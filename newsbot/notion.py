"""Mirror every item the bot sends into a Notion database (the user's archive).

Needs NOTION_TOKEN (internal integration secret, connected to the database) and
NOTION_DATABASE_ID. If either is missing the archive step is skipped silently.
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from newsbot.fetchers.util import clip
from newsbot.models import Item

logger = logging.getLogger(__name__)

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

KIND_BY_SOURCE = {
    "github_trending": "저장소",
    "github_new": "저장소",
    "hf_paper": "논문",
    "hf_model": "모델",
    "reddit": "커뮤니티",
    "hn": "커뮤니티",
    "rss": "블로그",
    "x": "X",
}
SOURCE_LABEL = {
    "github_trending": "GitHub Trending",
    "github_new": "GitHub New",
    "hf_paper": "HF Papers",
    "hf_model": "HF Models",
    "hn": "Hacker News",
    "x": "X",
}


def source_label(item: Item) -> str:
    if item.source == "rss":
        return item.meta.get("feed") or "RSS"
    if item.source == "reddit":
        sub = item.meta.get("subreddit")
        return f"r/{sub}" if sub else "Reddit"
    return SOURCE_LABEL.get(item.source, item.source)


def _rt(text: str, limit: int = 1900) -> dict:
    return {"rich_text": [{"text": {"content": clip(text, limit)}}]} if text else {"rich_text": []}


def build_properties(item: Item, sent_at: datetime) -> dict:
    props = {
        "Title": {"title": [{"text": {"content": clip(item.title, 200)}}]},
        "URL": {"url": item.url[:2000]},
        "Kind": {"select": {"name": KIND_BY_SOURCE.get(item.source, "블로그")}},
        "Source": {"select": {"name": source_label(item)[:100]}},
        "Status": {"select": {"name": "안 읽음"}},
        "Score": {"number": round(item.priority, 2)},
        "Signal": _rt(item.signal, 300),
        "Summary": _rt(item.summary),
        "Sent": {"date": {"start": sent_at.isoformat()}},
        "Key": _rt(item.key, 200),
    }
    disc = item.meta.get("discussion_url")
    if disc:
        props["Discussion"] = {"url": disc[:2000]}
    return props


class NotionArchive:
    def __init__(self, token: str, database_id: str):
        self.database_id = database_id
        self.client = httpx.Client(
            base_url=API,
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
        )

    def exists(self, key: str) -> bool:
        resp = self.client.post(
            f"/databases/{self.database_id}/query",
            json={"filter": {"property": "Key", "rich_text": {"equals": key}}, "page_size": 1},
        )
        resp.raise_for_status()
        return bool(resp.json().get("results"))

    def add(self, item: Item, sent_at: datetime) -> bool:
        resp = self.client.post(
            "/pages",
            json={"parent": {"database_id": self.database_id}, "properties": build_properties(item, sent_at)},
        )
        if resp.status_code >= 400:
            logger.warning("notion add failed %s for %s: %s", resp.status_code, item.key, resp.text[:300])
            return False
        return True

    def archive(self, items: list[Item], sent_at: datetime) -> int:
        added = 0
        for item in items:
            try:
                if self.exists(item.key):
                    continue
                if self.add(item, sent_at):
                    added += 1
            except httpx.HTTPError as exc:
                logger.warning("notion archive error for %s: %s", item.key, exc)
        logger.info("notion archive: %s/%s added", added, len(items))
        return added


def archive_sent(items: list[Item], sent_at: datetime, *, token: str, database_id: str) -> int:
    if not token or not database_id or not items:
        return 0
    return NotionArchive(token, database_id).archive(items, sent_at)
