from datetime import UTC, datetime

from newsbot.fetchers.github import parse_trending_html
from newsbot.fetchers.reddit import parse_reddit_rss
from newsbot.fetchers.rss import parse_feed


def test_trending_parser(fixtures):
    rows = parse_trending_html((fixtures / "trending.html").read_text())
    assert len(rows) == 3
    first = rows[0]
    assert first["full_name"].count("/") == 1
    assert first["stars_today"] > 0
    assert first["stars_total"] and first["stars_total"] >= first["stars_today"]
    assert first["language"]


def test_reddit_rss_parser(fixtures):
    items = parse_reddit_rss(
        (fixtures / "reddit_top.rss").read_text(), subreddit_scores={"LocalLLaMA": 300}, default_min=150, top_n=3
    )
    assert len(items) == 3
    assert items[0].key.startswith("reddit:")
    assert items[0].signal == "🏆 r/LocalLLaMA 오늘 #1"
    assert items[0].threshold == 300.0
    assert items[0].priority == 2.0
    assert all(i.url.startswith("http") for i in items)


ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>New model</title><link href="https://example.com/a"/><updated>{recent}</updated><summary>&lt;p&gt;Hello &lt;b&gt;world&lt;/b&gt;&lt;/p&gt;</summary></entry>
<entry><title>Old post</title><link href="https://example.com/b"/><updated>2020-01-01T00:00:00Z</updated></entry>
</feed>"""


def test_rss_parser_filters_old_and_strips_html():
    now = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    xml = ATOM.format(recent="2026-09-10T08:00:00Z")
    items = parse_feed(xml, "Example", lookback_hours=48, now=now)
    assert [i.title for i in items] == ["New model"]
    assert items[0].summary == "Hello world"
    assert items[0].key == "rss:https://example.com/a"
