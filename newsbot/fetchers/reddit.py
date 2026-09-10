"""Reddit: official OAuth API when credentials exist, otherwise the public RSS (no scores)."""

from __future__ import annotations

import asyncio
import logging

import feedparser
import httpx
from bs4 import BeautifulSoup

from newsbot.config import Settings
from newsbot.fetchers import BROWSER_UA
from newsbot.fetchers.util import clip, iso_from_epoch, iso_from_struct, squash
from newsbot.models import Item
from newsbot.sources import SUBREDDITS

logger = logging.getLogger(__name__)

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OAUTH_BASE = "https://oauth.reddit.com"
# One request for all subreddits at once: anonymous Reddit rate-limits per-request very fast.
MULTI_RSS_URL = "https://www.reddit.com/r/{subs}/top.rss?t=day&limit=25"

# RSS fallback has no upvotes; rank-of-day across the combined feed is the only signal we have.
_RANK_FACTOR = {1: 2.0, 2: 1.6, 3: 1.3, 4: 1.1, 5: 1.0}


async def _oauth_token(client: httpx.AsyncClient, settings: Settings) -> str:
    resp = await client.post(
        TOKEN_URL,
        auth=(settings.reddit_client_id, settings.reddit_client_secret),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": settings.reddit_user_agent},
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("reddit token response had no access_token")
    return token


def _post_to_item(post: dict, sub: str, min_score: int) -> Item | None:
    pid = post.get("id")
    title = squash(post.get("title") or "")
    if not pid or not title:
        return None
    permalink = f"https://www.reddit.com{post.get('permalink', '')}"
    external = post.get("url_overridden_by_dest") or post.get("url") or ""
    is_self = bool(post.get("is_self")) or not external or external.startswith("/r/")
    url = permalink if is_self else external
    score = int(post.get("score") or post.get("ups") or 0)
    comments = int(post.get("num_comments") or 0)
    meta = {"subreddit": sub, "comments": comments, "permalink": permalink}
    if not is_self:
        meta["discussion_url"] = permalink
    return Item(
        key=f"reddit:{pid}",
        source="reddit",
        title=title,
        url=url,
        summary=clip(post.get("selftext") or "", 600),
        score=float(score),
        threshold=float(min_score),
        signal=f"▲ {score:,} · r/{sub} · 💬 {comments:,}",
        published_at=iso_from_epoch(post.get("created_utc")),
        meta=meta,
    )


async def _fetch_sub_oauth(client: httpx.AsyncClient, token: str, settings: Settings, sub: str, min_score: int) -> list[Item]:
    resp = await client.get(
        f"{OAUTH_BASE}/r/{sub}/top",
        params={"t": "day", "limit": 25, "raw_json": 1},
        headers={"Authorization": f"bearer {token}", "User-Agent": settings.reddit_user_agent},
    )
    resp.raise_for_status()
    children = ((resp.json().get("data") or {}).get("children")) or []
    items = []
    for child in children:
        item = _post_to_item(child.get("data") or {}, sub, min_score)
        if item and item.score >= min_score:
            items.append(item)
    return items


def parse_reddit_rss(
    xml_text: str,
    *,
    subreddit_scores: dict[str, int],
    default_min: int,
    top_n: int,
) -> list[Item]:
    """Combined top-of-day feed → top N posts. Subreddit comes from the entry's <category> tag."""
    feed = feedparser.parse(xml_text)
    items: list[Item] = []
    for rank, entry in enumerate(feed.entries[:top_n], start=1):
        link = entry.get("link") or ""
        pid = (entry.get("id") or link).rsplit("_", 1)[-1] or link
        title = squash(entry.get("title") or "")
        if not title or not link:
            continue
        tags = [t.get("term") for t in (entry.get("tags") or []) if t.get("term")]
        sub = tags[0] if tags else "reddit"
        min_score = subreddit_scores.get(sub) or default_min
        html = entry.get("summary") or ""
        soup = BeautifulSoup(html, "html.parser")
        external = ""
        for a in soup.find_all("a"):
            if squash(a.get_text()) == "[link]":
                external = a.get("href") or ""
                break
        text = squash(soup.get_text(" "))
        text = text.split("submitted by")[0].strip()
        is_self = not external or "reddit.com" in external
        url = link if is_self else external
        meta = {"subreddit": sub, "permalink": link, "rank": rank, "rss": True}
        if not is_self:
            meta["discussion_url"] = link
        factor = _RANK_FACTOR.get(rank, 0.0)
        items.append(
            Item(
                key=f"reddit:{pid}",
                source="reddit",
                title=title,
                url=url,
                summary=clip(text, 600) if is_self else "",
                score=float(min_score) * factor,
                threshold=float(min_score),
                signal=f"🏆 r/{sub} 오늘 #{rank}",
                published_at=iso_from_struct(entry.get("published_parsed")),
                meta=meta,
            )
        )
    return items


async def _fetch_multi_rss(client: httpx.AsyncClient, settings: Settings) -> list[Item]:
    url = MULTI_RSS_URL.format(subs="+".join(SUBREDDITS))
    headers = {"User-Agent": BROWSER_UA, "Accept": "application/rss+xml, application/atom+xml, application/xml"}
    for attempt in range(3):
        resp = await client.get(url, headers=headers)
        if resp.status_code == 429 and attempt < 2:
            wait = 10 * (attempt + 1)
            logger.warning("reddit rss 429; retrying in %ss", wait)
            await asyncio.sleep(wait)
            continue
        resp.raise_for_status()
        return parse_reddit_rss(
            resp.text,
            subreddit_scores=SUBREDDITS,
            default_min=settings.reddit_default_min_score,
            top_n=settings.reddit_rss_top_n,
        )
    return []


async def fetch_all(client: httpx.AsyncClient, settings: Settings, report: dict) -> list[Item]:
    items: list[Item] = []
    errors: list[str] = []
    mode = "oauth" if settings.reddit_oauth_ready else "rss"
    token = None
    if mode == "oauth":
        try:
            token = await _oauth_token(client, settings)
        except Exception as exc:  # noqa: BLE001
            logger.warning("reddit oauth failed (%s); falling back to rss", exc)
            errors.append(f"oauth: {str(exc).splitlines()[0]}")
            mode = "rss"

    if mode == "oauth" and token:
        for sub, min_score in SUBREDDITS.items():
            min_score = min_score or settings.reddit_default_min_score
            try:
                items.extend(await _fetch_sub_oauth(client, token, settings, sub, min_score))
            except Exception as exc:  # noqa: BLE001
                logger.warning("reddit r/%s failed: %s", sub, exc)
                errors.append(f"r/{sub}: {str(exc).splitlines()[0]}")
    else:
        try:
            items.extend(await _fetch_multi_rss(client, settings))
        except Exception as exc:  # noqa: BLE001
            logger.warning("reddit rss failed: %s", exc)
            errors.append(f"rss: {str(exc).splitlines()[0]}")

    report["reddit_mode"] = mode
    if errors:
        report["reddit_errors"] = errors
    logger.info("reddit (%s): %s candidates", mode, len(items))
    return items
