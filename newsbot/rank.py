"""Importance filter + cross-source dedupe."""

from __future__ import annotations

import re

from newsbot.fetchers.util import canonical_url
from newsbot.models import Item
from newsbot.sources import AI_KEYWORDS

_KEYWORD_RE = re.compile(
    r"(?<![a-z0-9])(?:" + "|".join(re.escape(k) for k in sorted(AI_KEYWORDS, key=len, reverse=True)) + r")(?![a-z0-9])",
    re.IGNORECASE,
)


def is_ai_related(*texts: str) -> bool:
    hay = " ".join(t for t in texts if t)
    return bool(_KEYWORD_RE.search(hay))


def select(items: list[Item]) -> list[Item]:
    """Keep items at/above their source bar, merge duplicates, sort by priority."""
    by_key: dict[str, Item] = {}
    for item in items:
        if item.priority < 1.0:
            continue
        prev = by_key.get(item.key)
        if prev is None or item.priority > prev.priority:
            by_key[item.key] = item

    by_url: dict[str, Item] = {}
    for item in by_key.values():
        cu = canonical_url(item.url)
        prev = by_url.get(cu)
        if prev is None:
            by_url[cu] = item
            continue
        winner, loser = (item, prev) if item.priority > prev.priority else (prev, item)
        # Keep the discussion link of whichever side has one (HN / Reddit thread).
        for side in (loser, winner):
            disc = side.meta.get("discussion_url") or (side.url if side.source in {"hn", "reddit"} and side.url != winner.url else None)
            if disc and not winner.meta.get("discussion_url"):
                winner.meta["discussion_url"] = disc
        winner.meta.setdefault("also", []).append(loser.source)
        if loser.signal and loser.signal not in winner.signal:
            winner.signal = f"{winner.signal} · {loser.signal}" if winner.signal else loser.signal
        by_url[cu] = winner

    return sorted(by_url.values(), key=lambda i: i.priority, reverse=True)
