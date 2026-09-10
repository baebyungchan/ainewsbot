from newsbot.models import Item
from newsbot.rank import is_ai_related, select


def test_keyword_word_boundaries():
    assert is_ai_related("An AI toolkit")
    assert is_ai_related("Run LLMs locally")
    assert not is_ai_related("chain of custody detail")  # 'ai' inside words must not match
    assert not is_ai_related("A fast JSON parser in Rust")


def test_select_filters_below_bar_and_sorts():
    items = [
        Item(key="a", source="hn", title="a", url="https://a.com", score=50, threshold=100),
        Item(key="b", source="hn", title="b", url="https://b.com", score=300, threshold=100),
        Item(key="c", source="reddit", title="c", url="https://c.com", score=200, threshold=150),
    ]
    out = select(items)
    assert [i.key for i in out] == ["b", "c"]


def test_select_merges_same_url_and_keeps_discussion_link():
    gh = Item(key="gh:foo/bar", source="github_trending", title="foo/bar", url="https://github.com/foo/bar",
              score=1000, threshold=300, signal="★ +1,000 today")
    hn = Item(key="hn:1", source="hn", title="Foo Bar", url="https://github.com/Foo/Bar", score=150, threshold=100,
              signal="🟠 HN 150 pts", meta={"discussion_url": "https://news.ycombinator.com/item?id=1"})
    out = select([hn, gh])
    assert len(out) == 1
    assert out[0].key == "gh:foo/bar"
    assert out[0].meta["discussion_url"] == "https://news.ycombinator.com/item?id=1"
    assert "HN" in out[0].signal
