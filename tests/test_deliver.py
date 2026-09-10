from datetime import datetime, timedelta, timezone

from newsbot.deliver import render_item, render_messages
from newsbot.models import Item
from newsbot.run import in_quiet_hours

KST = timezone(timedelta(hours=9))


def test_render_item_escapes_html():
    it = Item(key="hn:1", source="hn", title="<script>&", url="https://a.com/?x=1&y=2", signal="🟠 HN 100 pts",
              summary="a < b", meta={"discussion_url": "https://news.ycombinator.com/item?id=1"})
    out = render_item(1, it)
    assert "&lt;script&gt;&amp;" in out
    assert 'href="https://a.com/?x=1&amp;y=2"' in out
    assert "토론" in out


def test_render_messages_splits_long_batches():
    items = [Item(key=f"k{i}", source="reddit", title="t" * 200, url="https://r.com", summary="s" * 300) for i in range(30)]
    msgs = render_messages(items, datetime.now(KST))
    assert len(msgs) > 1
    assert all(len(m) <= 4096 for m in msgs)
    assert msgs[1].startswith("🤖")


def test_quiet_hours():
    t = lambda h: datetime(2026, 9, 10, h, 0, tzinfo=KST)
    assert in_quiet_hours(t(3), 0, 8)
    assert not in_quiet_hours(t(9), 0, 8)
    assert in_quiet_hours(t(23), 23, 7)
    assert in_quiet_hours(t(2), 23, 7)
    assert not in_quiet_hours(t(12), 23, 7)
    assert not in_quiet_hours(t(3), 0, 0)
