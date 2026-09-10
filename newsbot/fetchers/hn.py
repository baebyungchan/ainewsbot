"""Hacker News via the Algolia API: top stories of the last N hours, AI-filtered locally."""

from __future__ import annotations

import logging
import time

import httpx

from newsbot.config import Settings
from newsbot.fetchers import BOT_UA
from newsbot.fetchers.util import clip, iso_from_epoch, squash, strip_html
from newsbot.models import Item
from newsbot.rank import is_ai_related

logger = logging.getLogger(__name__)

API = "https://hn.algolia.com/api/v1/search_by_date"


async def fetch(client: httpx.AsyncClient, settings: Settings) -> list[Item]:
    since = int(time.time()) - settings.hn_lookback_hours * 3600
    params = {
        "tags": "story",
        "numericFilters": f"points>{settings.hn_min_points},created_at_i>{since}",
        "hitsPerPage": 100,
    }
    resp = await client.get(API, params=params, headers={"User-Agent": BOT_UA})
    resp.raise_for_status()
    hits = resp.json().get("hits") or []
    items: list[Item] = []
    for hit in hits:
        title = squash(hit.get("title") or "")
        text = strip_html(hit.get("story_text") or "")
        if not title or not is_ai_related(title, text, hit.get("url") or ""):
            continue
        oid = hit.get("objectID")
        hn_url = f"https://news.ycombinator.com/item?id={oid}"
        url = hit.get("url") or hn_url
        points = int(hit.get("points") or 0)
        comments = int(hit.get("num_comments") or 0)
        meta = {"hn_id": oid, "comments": comments}
        if url != hn_url:
            meta["discussion_url"] = hn_url
        items.append(
            Item(
                key=f"hn:{oid}",
                source="hn",
                title=title,
                url=url,
                summary=clip(text, 600),
                score=float(points),
                threshold=float(settings.hn_min_points),
                signal=f"🟠 HN {points:,} pts · 💬 {comments:,}",
                published_at=iso_from_epoch(hit.get("created_at_i")),
                meta=meta,
            )
        )
    logger.info("hn: %s hits, %s AI-related", len(hits), len(items))
    return items
