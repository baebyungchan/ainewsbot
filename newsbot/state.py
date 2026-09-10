"""Persistent state: what was seen/sent, what is still queued. Stored as one JSON file
that the GitHub Actions job commits back to the repo after every run."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from newsbot.models import Item

VERSION = 1
MILESTONE_FACTOR = 3.0  # re-notify a GitHub repo when its total stars tripled
MILESTONE_MIN_HOURS = 48


def _now() -> datetime:
    return datetime.now(UTC)


def _parse(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class State:
    def __init__(self, path: Path, data: dict | None = None):
        self.path = path
        self.data = data or {"version": VERSION, "created_at": None, "seen": {}, "pending": [], "sends": []}
        self.data.setdefault("seen", {})
        self.data.setdefault("pending", [])
        self.data.setdefault("sends", [])

    # ---- io -------------------------------------------------------------
    @classmethod
    def load(cls, path: Path) -> State:
        if path.exists():
            try:
                return cls(path, json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass
        return cls(path)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    # ---- queries ----------------------------------------------------------
    @property
    def is_first_run(self) -> bool:
        return not self.data.get("created_at")

    @property
    def pending(self) -> list[Item]:
        return [Item.from_dict(d) for d in self.data["pending"]]

    def is_new(self, item: Item, now: datetime | None = None) -> bool:
        now = now or _now()
        rec = self.data["seen"].get(item.key)
        if rec is None:
            return True
        # Milestone re-notify for GitHub repos that keep growing.
        if item.source.startswith("github") and rec.get("sent"):
            old = rec.get("stars_total") or 0
            new = item.meta.get("stars_total") or 0
            sent_at = _parse(rec.get("sent"))
            if old and new >= old * MILESTONE_FACTOR and sent_at and now - sent_at >= timedelta(hours=MILESTONE_MIN_HOURS):
                item.signal = f"🚀 {old:,} → {new:,} stars · {item.signal}"
                item.meta["milestone"] = True
                return True
        return False

    # ---- mutations --------------------------------------------------------
    def touch(self, now: datetime | None = None) -> None:
        now = now or _now()
        if self.is_first_run:
            self.data["created_at"] = now.isoformat()
        self.data["last_run"] = now.isoformat()

    def mark_seen(self, item: Item, *, now: datetime | None = None) -> None:
        now = now or _now()
        rec = self.data["seen"].setdefault(item.key, {"first": now.isoformat(), "sent": None})
        rec["last"] = now.isoformat()
        rec["score"] = item.score
        if item.meta.get("stars_total") is not None:
            rec["stars_total"] = item.meta["stars_total"]

    def enqueue(self, items: list[Item], *, now: datetime | None = None) -> None:
        now = now or _now()
        queued = {d["key"] for d in self.data["pending"]}
        for item in items:
            self.mark_seen(item, now=now)
            if item.key in queued:
                continue
            d = item.to_dict()
            d["queued_at"] = now.isoformat()
            self.data["pending"].append(d)
            queued.add(item.key)

    def take(self, limit: int) -> list[Item]:
        """Pop up to `limit` highest-priority pending items."""
        rows = sorted(self.data["pending"], key=lambda d: (d.get("score", 0) / (d.get("threshold") or 1.0)), reverse=True)
        chosen, rest = rows[:limit], rows[limit:]
        self.data["pending"] = rest
        return [Item.from_dict(d) for d in chosen]

    def requeue(self, items: list[Item], *, now: datetime | None = None) -> None:
        now = now or _now()
        rows = [dict(i.to_dict(), queued_at=now.isoformat()) for i in items]
        self.data["pending"] = rows + self.data["pending"]

    def mark_sent(self, items: list[Item], *, now: datetime | None = None) -> None:
        now = now or _now()
        for item in items:
            rec = self.data["seen"].setdefault(item.key, {"first": now.isoformat()})
            rec["sent"] = now.isoformat()
            rec["last"] = now.isoformat()
            if item.meta.get("stars_total") is not None:
                rec["stars_total"] = item.meta["stars_total"]
        self.data["sends"].append({"at": now.isoformat(), "count": len(items)})

    def prune(self, *, seen_ttl_days: int, pending_ttl_hours: int, now: datetime | None = None) -> None:
        now = now or _now()
        seen_cut = now - timedelta(days=seen_ttl_days)
        self.data["seen"] = {
            k: v for k, v in self.data["seen"].items() if (_parse(v.get("last") or v.get("first")) or now) >= seen_cut
        }
        pend_cut = now - timedelta(hours=pending_ttl_hours)
        self.data["pending"] = [d for d in self.data["pending"] if (_parse(d.get("queued_at")) or now) >= pend_cut]
        self.data["sends"] = self.data["sends"][-200:]
