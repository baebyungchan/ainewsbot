from newsbot.fetchers.hf import parse_daily_papers, parse_trending_models
from newsbot.rank import is_ai_related

PAPERS = [
    {"paper": {"id": "2609.01234", "title": "Big Model", "upvotes": 40, "summary": "We train a big model.",
               "authors": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}, "publishedAt": "2026-09-10T00:00:00Z"},
    {"paper": {"id": "2609.09999", "title": "Tiny note", "upvotes": 3, "authors": []}},
]
MODELS = [
    {"id": "deepseek-ai/DeepSeek-V4.1-Flash", "likes": 1047, "downloads": 6, "pipeline_tag": "text-generation"},
    {"id": "Qwen/Qwen3.8-27B", "likes": 14596, "downloads": 7322476},
]


def test_daily_papers_threshold_and_fields():
    items = parse_daily_papers(PAPERS, min_upvotes=15)
    assert [i.key for i in items] == ["hfpaper:2609.01234", "hfpaper:2609.09999"]
    top = items[0]
    assert top.priority > 1.0 and items[1].priority < 1.0
    assert top.url == "https://huggingface.co/papers/2609.01234"
    assert top.meta["discussion_url"].endswith("2609.01234")
    assert "A, B 외" in top.signal


def test_trending_models_rank_priority():
    items = parse_trending_models(MODELS, top_n=5)
    assert items[0].priority == 2.0 and items[1].priority == 1.6
    assert items[0].url == "https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash"
    assert "text-generation" in items[0].signal


def test_korean_keywords():
    assert is_ai_related("앤트로픽, 클로드 API 비용 절감 방법 공개")
    assert is_ai_related("생성형 AI 규제 논의")
    assert not is_ai_related("Windows XP는 초기 사용자 사진을 어떤 알고리듬으로 골랐을까?")
