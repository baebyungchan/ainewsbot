"""Hugging Face: curated daily papers (community upvotes) and trending models."""

from __future__ import annotations

import logging

import httpx

from newsbot.config import Settings
from newsbot.fetchers import BOT_UA
from newsbot.fetchers.util import clip, squash
from newsbot.models import Item

logger = logging.getLogger(__name__)

PAPERS_API = "https://huggingface.co/api/daily_papers"
MODELS_API = "https://huggingface.co/api/models"
_RANK_FACTOR = {1: 2.0, 2: 1.6, 3: 1.3, 4: 1.1, 5: 1.0}


def parse_daily_papers(data: list[dict], min_upvotes: int) -> list[Item]:
    items: list[Item] = []
    for row in data:
        paper = row.get("paper") or {}
        pid = paper.get("id")
        title = squash(paper.get("title") or row.get("title") or "")
        if not pid or not title:
            continue
        upvotes = int(paper.get("upvotes") or 0)
        authors = [a.get("name") for a in (paper.get("authors") or []) if a.get("name")]
        who = ", ".join(authors[:2]) + (" 외" if len(authors) > 2 else "")
        items.append(
            Item(
                key=f"hfpaper:{pid}",
                source="hf_paper",
                title=title,
                url=f"https://huggingface.co/papers/{pid}",
                summary=clip(paper.get("summary") or paper.get("ai_summary") or "", 600),
                score=float(upvotes),
                threshold=float(min_upvotes),
                signal=f"📄 논문 ▲ {upvotes} · {who}" if who else f"📄 논문 ▲ {upvotes}",
                published_at=row.get("publishedAt") or paper.get("publishedAt"),
                meta={"arxiv_id": pid, "upvotes": upvotes, "discussion_url": f"https://arxiv.org/abs/{pid}"},
            )
        )
    return items


def parse_trending_models(data: list[dict], top_n: int) -> list[Item]:
    items: list[Item] = []
    for rank, model in enumerate(data[:top_n], start=1):
        mid = model.get("id") or model.get("modelId")
        if not mid:
            continue
        likes = int(model.get("likes") or 0)
        downloads = int(model.get("downloads") or 0)
        pipeline = model.get("pipeline_tag") or ""
        bits = [f"🤗 트렌딩 #{rank}", f"❤ {likes:,}", f"⬇ {downloads:,}"]
        if pipeline:
            bits.append(pipeline)
        items.append(
            Item(
                key=f"hfmodel:{mid.lower()}",
                source="hf_model",
                title=mid,
                url=f"https://huggingface.co/{mid}",
                summary="",
                score=float(_RANK_FACTOR.get(rank, 0.0)),
                threshold=1.0,
                signal=" · ".join(bits),
                published_at=model.get("createdAt"),
                meta={"rank": rank, "likes": likes, "downloads": downloads, "pipeline": pipeline},
            )
        )
    return items


async def fetch_daily_papers(client: httpx.AsyncClient, settings: Settings) -> list[Item]:
    resp = await client.get(PAPERS_API, params={"limit": 50}, headers={"User-Agent": BOT_UA})
    resp.raise_for_status()
    items = [it for it in parse_daily_papers(resp.json(), settings.hf_paper_min_upvotes) if it.priority >= 1.0]
    logger.info("hf papers: %s above %s upvotes", len(items), settings.hf_paper_min_upvotes)
    return items


async def fetch_trending_models(client: httpx.AsyncClient, settings: Settings) -> list[Item]:
    resp = await client.get(
        MODELS_API,
        params={"sort": "trendingScore", "direction": -1, "limit": settings.hf_model_top_n},
        headers={"User-Agent": BOT_UA},
    )
    resp.raise_for_status()
    items = parse_trending_models(resp.json(), settings.hf_model_top_n)
    logger.info("hf models: top %s", len(items))
    return items
