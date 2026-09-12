from datetime import UTC, datetime

from newsbot.models import Item
from newsbot.notion import build_properties, source_label


def test_build_properties_paper():
    it = Item(key="hfpaper:2609.1", source="hf_paper", title="Big Model", url="https://huggingface.co/papers/2609.1",
              summary="s" * 3000, score=40, threshold=15, signal="📄 논문 ▲ 40",
              meta={"discussion_url": "https://arxiv.org/abs/2609.1"})
    props = build_properties(it, datetime(2026, 9, 12, 8, 0, tzinfo=UTC))
    assert props["Kind"]["select"]["name"] == "논문"
    assert props["Source"]["select"]["name"] == "HF Papers"
    assert props["Status"]["select"]["name"] == "안 읽음"
    assert props["Score"]["number"] == 2.67
    assert len(props["Summary"]["rich_text"][0]["text"]["content"]) <= 1900
    assert props["Discussion"]["url"].endswith("2609.1")
    assert props["Sent"]["date"]["start"].startswith("2026-09-12T08:00")


def test_source_labels():
    assert source_label(Item(key="a", source="rss", title="t", url="u", meta={"feed": "OpenAI"})) == "OpenAI"
    assert source_label(Item(key="a", source="reddit", title="t", url="u", meta={"subreddit": "LocalLLaMA"})) == "r/LocalLLaMA"
    assert source_label(Item(key="a", source="github_trending", title="t", url="u")) == "GitHub Trending"
    props = build_properties(Item(key="a", source="hn", title="t", url="u"), datetime.now(UTC))
    assert "Discussion" not in props and props["Kind"]["select"]["name"] == "커뮤니티"
