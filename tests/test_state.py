from datetime import UTC, datetime, timedelta
from pathlib import Path

from newsbot.models import Item
from newsbot.state import State


def _item(key="gh:a/b", score=500.0, stars=1000):
    return Item(key=key, source="github_trending", title=key, url=f"https://github.com/{key[3:]}",
                score=score, threshold=300.0, meta={"stars_total": stars})


def test_first_run_and_roundtrip(tmp_path: Path):
    p = tmp_path / "s.json"
    st = State.load(p)
    assert st.is_first_run
    now = datetime.now(UTC)
    it = _item()
    assert st.is_new(it, now)
    st.enqueue([it], now=now)
    st.touch(now)
    st.save()

    st2 = State.load(p)
    assert not st2.is_first_run
    assert not st2.is_new(_item(), now)  # queued == seen
    batch = st2.take(8)
    assert [i.key for i in batch] == ["gh:a/b"]
    assert st2.data["pending"] == []


def test_take_is_priority_ordered_and_requeue(tmp_path: Path):
    st = State.load(tmp_path / "s.json")
    low = Item(key="hn:1", source="hn", title="low", url="https://l.com", score=110, threshold=100)
    high = Item(key="hn:2", source="hn", title="high", url="https://h.com", score=900, threshold=100)
    st.enqueue([low, high])
    batch = st.take(1)
    assert batch[0].key == "hn:2"
    st.requeue(batch)
    assert st.data["pending"][0]["key"] == "hn:2"
    assert len(st.data["pending"]) == 2


def test_milestone_renotify(tmp_path: Path):
    st = State.load(tmp_path / "s.json")
    t0 = datetime.now(UTC) - timedelta(days=3)
    first = _item(stars=1000)
    st.enqueue([first], now=t0)
    st.mark_sent([first], now=t0)
    now = datetime.now(UTC)
    assert not st.is_new(_item(stars=2000), now)
    grown = _item(stars=3500)
    assert st.is_new(grown, now)
    assert grown.meta.get("milestone") is True


def test_prune(tmp_path: Path):
    st = State.load(tmp_path / "s.json")
    old = datetime.now(UTC) - timedelta(days=60)
    st.enqueue([_item("gh:old/x")], now=old)
    st.enqueue([_item("gh:new/x")])
    st.prune(seen_ttl_days=45, pending_ttl_hours=36)
    assert "gh:old/x" not in st.data["seen"]
    assert [d["key"] for d in st.data["pending"]] == ["gh:new/x"]
