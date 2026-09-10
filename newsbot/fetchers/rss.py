"""Official blogs via RSS/Atom. Low volume: every recent post is a candidate."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import feedparser
import httpx

from newsbot.config import Settings
from newsbot.fetchers import BROWSER_UA
from newsbot.fetchers.util import age_hours, canonical_url, clip, iso_from_struct, squash, strip_html
from newsbot.models import Item
from newsbot.sources import RSS_FEEDS

logger = logging.getLogger(__name__)


def parse_feed(xml_text: str, name: str, *, lookback_hours: int, now: datetime | None = None, limit: int = 5) -> list[Item]:
    now = now or datetime.now(UTC)
    feed = feedparser.parse(xml_text)
    items: list[Item] = []
    for entry in feed.entries:
        link = entry.get("link") or ""
        title = squash(entry.get("title") or "")
        if not link or not title:
            continue
        published = iso_from_struct(entry.get("published_parsed") or entry.get("updated_parsed"))
        age = age_hours(published, now)
        if age is not None and age > lookback_hours:
            continue
        summary = strip_html(entry.get("summary") or entry.get("description") or "")
        items.append(
            Item(
                key=f"rss:{canonical_url(link)}",
                source="rss",
                title=title,
                url=link,
                summary=clip(summary, 500),
                score=1.0,
                threshold=1.0,
                signal=f"📰 {name}",
                published_at=published,
                meta={"feed": name},
            )
        )
        if len(items) >= limit:
            break
    return items


async def fetch_all(client: httpx.AsyncClient, settings: Settings, report: dict) -> list[Item]:
    async def one(name: str, url: str) -> list[Item]:
        try:
            resp = await client.get(url, headers={"User-Agent": BROWSER_UA})
            resp.raise_for_status()
            return parse_feed(resp.text, name, lookback_hours=settings.rss_lookback_hours)
        except Exception as exc:  # noqa: BLE001
            logger.warning("rss %s failed: %s", name, exc)
            report.setdefault("rss_errors", []).append(f"{name}: {exc}")
            return []

    results = await asyncio.gather(*(one(n, u) for n, u in RSS_FEEDS))
    items = [it for group in results for it in group]
    logger.info("rss: %s recent posts across %s feeds", len(items), len(RSS_FEEDS))
    return items
