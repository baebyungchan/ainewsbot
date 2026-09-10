"""Telegram rendering + sending."""

from __future__ import annotations

import html
import logging
import time
from datetime import datetime

import httpx

from newsbot.fetchers.util import clip
from newsbot.models import Item

logger = logging.getLogger(__name__)

TELEGRAM_LIMIT = 3800  # hard API limit is 4096 chars of rendered text
SOURCE_ICON = {
    "github_trending": "🐙",
    "github_new": "🐙",
    "reddit": "👽",
    "hn": "🟠",
    "rss": "📰",
    "x": "𝕏",
    "hf_paper": "📄",
    "hf_model": "🤗",
}


def esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def render_item(index: int, item: Item, *, summary_chars: int = 240) -> str:
    icon = SOURCE_ICON.get(item.source, "•")
    signal = item.signal
    if item.source == "rss" and signal[:1] and not signal[:1].isalnum():
        # feed entries carry their own icon at the start of the signal; hoist it next to the title
        parts = signal.split(" ", 1)
        icon, signal = parts[0], (parts[1] if len(parts) > 1 else "")
    lines = [f"{index}. {icon} <a href=\"{esc(item.url)}\">{esc(item.title)}</a>"]
    signal = esc(signal)
    disc = item.meta.get("discussion_url")
    if disc and disc != item.url:
        signal = f"{signal} · <a href=\"{esc(disc)}\">토론</a>" if signal else f"<a href=\"{esc(disc)}\">토론</a>"
    if signal:
        lines.append(signal)
    if item.summary:
        lines.append(esc(clip(item.summary, summary_chars)))
    return "\n".join(lines)


def header(now_kst: datetime, count: int, *, label: str = "AI 뉴스") -> str:
    return f"🤖 <b>{esc(label)}</b> · {now_kst.strftime('%m/%d %H:%M')} KST · {count}건"


def render_messages(items: list[Item], now_kst: datetime, *, label: str = "AI 뉴스") -> list[str]:
    """Render to one or more Telegram-sized HTML messages."""
    head = header(now_kst, len(items), label=label)
    chunks: list[str] = []
    current: list[str] = [head]
    size = len(head)
    for idx, item in enumerate(items, start=1):
        block = render_item(idx, item)
        if size + len(block) + 2 > TELEGRAM_LIMIT and len(current) > 1:
            chunks.append("\n\n".join(current))
            current = [f"{head} (계속)"]
            size = len(current[0])
        current.append(block)
        size += len(block) + 2
    chunks.append("\n\n".join(current))
    return chunks


def send_telegram(token: str, chat_id: str, text: str, *, retries: int = 2) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True},
    }
    for attempt in range(retries + 1):
        try:
            resp = httpx.post(url, json=payload, timeout=30.0)
        except httpx.HTTPError as exc:
            logger.warning("telegram network error (attempt %s): %s", attempt + 1, exc)
            time.sleep(2)
            continue
        if resp.status_code == 200:
            return True
        if resp.status_code == 429:
            wait = int((resp.json().get("parameters") or {}).get("retry_after", 3)) if resp.headers.get("content-type", "").startswith("application/json") else 3
            logger.warning("telegram rate limited; waiting %ss", wait)
            time.sleep(min(wait, 30))
            continue
        logger.error("telegram send failed %s: %s", resp.status_code, resp.text[:300])
        return False
    return False
