"""GitHub: trending page (unofficial HTML) + search API for brand-new repos."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta

import httpx
from bs4 import BeautifulSoup

from newsbot.config import Settings
from newsbot.fetchers import BOT_UA, BROWSER_UA
from newsbot.fetchers.util import parse_int, squash
from newsbot.models import Item
from newsbot.rank import is_ai_related
from newsbot.sources import GITHUB_NEW_QUERY

logger = logging.getLogger(__name__)

TRENDING_URL = "https://github.com/trending?since=daily"
SEARCH_URL = "https://api.github.com/search/repositories"
_STARS_TODAY = re.compile(r"([\d,]+)\s+stars?\s+today")


def parse_trending_html(html: str) -> list[dict]:
    """Return raw rows: full_name, description, language, stars_total, stars_today."""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for art in soup.select("article.Box-row"):
        link = art.select_one("h2 a[href]")
        if not link:
            continue
        full_name = link["href"].strip().strip("/")
        if full_name.count("/") != 1:
            continue
        desc_node = art.select_one("p")
        lang_node = art.select_one("[itemprop=programmingLanguage]")
        star_node = art.select_one('a[href$="/stargazers"]')
        today_match = _STARS_TODAY.search(art.get_text(" "))
        rows.append(
            {
                "full_name": full_name,
                "description": squash(desc_node.get_text(" ")) if desc_node else "",
                "language": squash(lang_node.get_text()) if lang_node else "",
                "stars_total": parse_int(star_node.get_text()) if star_node else None,
                "stars_today": parse_int(today_match.group(1)) if today_match else 0,
            }
        )
    return rows


def _trending_item(row: dict, settings: Settings) -> Item | None:
    today = row["stars_today"] or 0
    ai = is_ai_related(row["full_name"], row["description"])
    if today < settings.github_trending_min_stars_today:
        return None
    if not ai and today < settings.github_trending_any_topic_min:
        return None
    total = row["stars_total"]
    bits = [f"★ +{today:,} today"]
    if total is not None:
        bits.append(f"{total:,} total")
    if row["language"]:
        bits.append(row["language"])
    return Item(
        key=f"gh:{row['full_name'].lower()}",
        source="github_trending",
        title=row["full_name"],
        url=f"https://github.com/{row['full_name']}",
        summary=row["description"],
        score=float(today),
        threshold=float(settings.github_trending_min_stars_today),
        signal=" · ".join(bits),
        meta={"stars_total": total, "stars_today": today, "language": row["language"], "ai": ai},
    )


async def fetch_trending(client: httpx.AsyncClient, settings: Settings) -> list[Item]:
    resp = await client.get(TRENDING_URL, headers={"User-Agent": BROWSER_UA, "Accept": "text/html"})
    resp.raise_for_status()
    rows = parse_trending_html(resp.text)
    if not rows:
        raise RuntimeError("trending page parsed to 0 rows (layout changed?)")
    items = [it for it in (_trending_item(r, settings) for r in rows) if it]
    logger.info("github trending: %s rows, %s above bar", len(rows), len(items))
    return items


async def fetch_new_repos(client: httpx.AsyncClient, settings: Settings) -> list[Item]:
    since = (datetime.now(UTC) - timedelta(days=settings.github_new_max_age_days)).date()
    query = f"{GITHUB_NEW_QUERY} created:>={since.isoformat()} stars:>={settings.github_new_min_stars}"
    headers = {"User-Agent": BOT_UA, "Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    resp = await client.get(
        SEARCH_URL,
        params={"q": query, "sort": "stars", "order": "desc", "per_page": 30},
        headers=headers,
    )
    resp.raise_for_status()
    data = resp.json()
    items: list[Item] = []
    now = datetime.now(UTC)
    for repo in data.get("items") or []:
        full_name = repo.get("full_name")
        stars = repo.get("stargazers_count") or 0
        if not full_name or stars < settings.github_new_min_stars:
            continue
        created = repo.get("created_at") or ""
        try:
            created_dt = datetime.fromisoformat(created)
            age_days = max((now - created_dt).total_seconds() / 86400.0, 0.5)
        except ValueError:
            age_days = float(settings.github_new_max_age_days)
        bits = [f"🆕 {stars:,} stars in {age_days:.0f}d"]
        if repo.get("language"):
            bits.append(repo["language"])
        items.append(
            Item(
                key=f"gh:{full_name.lower()}",
                source="github_new",
                title=full_name,
                url=repo.get("html_url") or f"https://github.com/{full_name}",
                summary=squash(repo.get("description") or ""),
                score=float(stars),
                threshold=float(settings.github_new_min_stars),
                signal=" · ".join(bits),
                published_at=created or None,
                meta={
                    "stars_total": stars,
                    "language": repo.get("language"),
                    "topics": repo.get("topics") or [],
                    "age_days": round(age_days, 1),
                },
            )
        )
    logger.info("github new repos: %s candidates", len(items))
    return items
