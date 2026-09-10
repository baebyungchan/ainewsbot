"""X (Twitter).

X has no free read API and public Nitter mirrors are gone, so:
1. `enrich`: any x.com/status link that surfaced via HN/Reddit gets its tweet text
   attached through the fxtwitter API (free, no key).
2. `fetch_rss`: optional. If you self-host a Nitter-compatible instance, set
   X_RSS_BASE=https://your-instance and X_ACCOUNTS=OpenAI,AnthropicAI,... .
"""

from __future__ import annotations

import asyncio
import logging

import feedparser
import httpx

from newsbot.config import Settings
from newsbot.fetchers import BOT_UA, BROWSER_UA
from newsbot.fetchers.util import clip, iso_from_struct, squash, strip_html, x_status
from newsbot.models import Item

logger = logging.getLogger(__name__)

FX_API = "https://api.fxtwitter.com/{user}/status/{sid}"
MAX_ENRICH = 12


async def _fx_lookup(client: httpx.AsyncClient, user: str, sid: str) -> dict | None:
    try:
        resp = await client.get(FX_API.format(user=user, sid=sid), headers={"User-Agent": BOT_UA}, timeout=15.0)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("tweet") or None
    except Exception as exc:  # noqa: BLE001
        logger.debug("fxtwitter failed for %s: %s", sid, exc)
        return None


async def enrich(client: httpx.AsyncClient, items: list[Item]) -> int:
    """Attach tweet text/author to items whose URL is an X status. Returns count enriched."""
    targets = [(it, x_status(it.url)) for it in items]
    targets = [(it, ref) for it, ref in targets if ref][:MAX_ENRICH]
    if not targets:
        return 0
    tweets = await asyncio.gather(*(_fx_lookup(client, user, sid) for _, (user, sid) in targets))
    done = 0
    for (item, (user, sid)), tweet in zip(targets, tweets):
        if not tweet:
            continue
        author = (tweet.get("author") or {}).get("screen_name") or user
        text = squash(tweet.get("text") or "")
        likes = int(tweet.get("likes") or 0)
        if text:
            item.summary = clip(text, 500)
        extra = f"𝕏 @{author}"
        if likes:
            extra += f" · ❤ {likes:,}"
        item.signal = f"{item.signal} · {extra}" if item.signal else extra
        item.meta["x_status_id"] = sid
        item.meta["x_author"] = author
        done += 1
    logger.info("x enrich: %s/%s tweets resolved", done, len(targets))
    return done


def parse_x_rss(xml_text: str, account: str, limit: int = 5) -> list[Item]:
    feed = feedparser.parse(xml_text)
    items: list[Item] = []
    for entry in feed.entries[:limit]:
        link = entry.get("link") or ""
        ref = x_status(link)
        text = strip_html(entry.get("summary") or entry.get("title") or "")
        if not ref or not text:
            continue
        _, sid = ref
        items.append(
            Item(
                key=f"x:{sid}",
                source="x",
                title=clip(text, 120),
                url=f"https://x.com/{account}/status/{sid}",
                summary=clip(text, 500),
                score=1.0,
                threshold=1.0,
                signal=f"𝕏 @{account}",
                published_at=iso_from_struct(entry.get("published_parsed")),
                meta={"x_status_id": sid, "x_author": account},
            )
        )
    return items


async def fetch_rss(client: httpx.AsyncClient, settings: Settings, report: dict) -> list[Item]:
    if not settings.x_rss_base or not settings.x_accounts:
        return []

    async def one(account: str) -> list[Item]:
        url = f"{settings.x_rss_base}/{account}/rss"
        try:
            resp = await client.get(url, headers={"User-Agent": BROWSER_UA, "Accept": "application/rss+xml"})
            resp.raise_for_status()
            return parse_x_rss(resp.text, account)
        except Exception as exc:  # noqa: BLE001
            logger.warning("x rss @%s failed: %s", account, exc)
            report.setdefault("x_errors", []).append(f"@{account}: {exc}")
            return []

    results = await asyncio.gather(*(one(a) for a in settings.x_accounts))
    return [it for group in results for it in group]
