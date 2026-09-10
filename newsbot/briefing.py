"""Build the outgoing messages. `rules` = plain formatting (free, default).
`claude` = ask Claude for a one-line Korean take per item, then format the same way."""

from __future__ import annotations

import logging
import re
from datetime import datetime

from newsbot.config import Settings
from newsbot.deliver import render_messages
from newsbot.fetchers.util import clip
from newsbot.models import Item

logger = logging.getLogger(__name__)

SYSTEM = """당신은 개발자를 위한 AI 업계 뉴스 에디터입니다.
각 항목이 왜 중요한지 한국어로 1~2문장씩 씁니다. 과장 금지, 추측 금지, 링크와 HTML 금지.
고유명사(모델명, 회사명, 저장소명)는 원문 표기를 유지합니다.
출력 형식은 오직 다음과 같습니다. 다른 말은 쓰지 마세요.
1. <한 줄 설명>
2. <한 줄 설명>
"""

_LINE_RE = re.compile(r"^\s*(\d+)[.)]\s*(.+?)\s*$")


def _payload(items: list[Item]) -> str:
    lines = []
    for i, item in enumerate(items, start=1):
        bits = [f"{i}. title: {item.title}", f"   source: {item.source} | signal: {item.signal}", f"   url: {item.url}"]
        if item.summary:
            bits.append(f"   snippet: {clip(item.summary, 700)}")
        lines.append("\n".join(bits))
    return "\n\n".join(lines)


def _parse_takes(text: str, count: int) -> dict[int, str]:
    takes: dict[int, str] = {}
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        idx = int(m.group(1))
        if 1 <= idx <= count and idx not in takes:
            takes[idx] = m.group(2)
    return takes


def claude_takes(items: list[Item], settings: Settings) -> dict[int, str] | None:
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic SDK not installed; using rules briefing")
        return None
    try:
        client = anthropic.Anthropic()
        response = client.beta.messages.create(
            model=settings.claude_model,
            max_tokens=4000,
            system=SYSTEM,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": f"아래 {len(items)}개 항목:\n\n{_payload(items)}"}],
        )
    except anthropic.RateLimitError as exc:
        logger.warning("claude rate limited: %s", exc)
        return None
    except anthropic.APIStatusError as exc:
        logger.warning("claude api error %s: %s", exc.status_code, exc.message)
        return None
    except anthropic.APIConnectionError as exc:
        logger.warning("claude connection error: %s", exc)
        return None
    if response.stop_reason == "refusal":
        logger.warning("claude refused the briefing request")
        return None
    text = "".join(block.text for block in response.content if block.type == "text")
    takes = _parse_takes(text, len(items))
    if not takes:
        logger.warning("claude reply had no parseable lines: %r", text[:200])
        return None
    return takes


def build_messages(items: list[Item], settings: Settings, now_kst: datetime) -> list[str]:
    if settings.briefing_provider == "claude" and items:
        takes = claude_takes(items, settings)
        if takes:
            for i, item in enumerate(items, start=1):
                if i in takes:
                    item.summary = takes[i]
    return render_messages(items, now_kst)
