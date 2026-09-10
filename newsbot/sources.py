"""Editable source list. Change subreddits, feeds and keywords here."""

from __future__ import annotations

# Subreddit -> minimum upvotes (only used when Reddit OAuth credentials are set;
# the RSS fallback has no scores and just takes the top N posts of the day).
SUBREDDITS: dict[str, int] = {
    "LocalLLaMA": 300,
    "MachineLearning": 100,
    "artificial": 150,
    "singularity": 300,
    "ClaudeAI": 150,
    "OpenAI": 200,
}

# RSS / Atom feeds. `ai_only`: keep only AI-related entries (for feeds that cover all of tech).
# `limit`: max new entries per run from that feed.
RSS_FEEDS: list[dict] = [
    # official labs (low volume, every post is worth a look)
    {"name": "OpenAI", "url": "https://openai.com/news/rss.xml", "icon": "📰"},
    {"name": "Anthropic", "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml", "icon": "📰"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml", "icon": "📰"},
    {"name": "Google AI", "url": "https://blog.google/technology/ai/rss/", "icon": "📰"},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "icon": "📰"},
    {"name": "Qwen", "url": "https://qwenlm.github.io/blog/index.xml", "icon": "📰"},
    {"name": "Mistral", "url": "https://mistral.ai/rss.xml", "icon": "📰", "ai_only": True},
    # research labs (broad feeds → AI filter)
    {"name": "Google Research", "url": "https://research.google/blog/rss/", "icon": "🔬", "ai_only": True, "limit": 3},
    {"name": "Microsoft Research", "url": "https://www.microsoft.com/en-us/research/feed/", "icon": "🔬", "ai_only": True, "limit": 3},
    {"name": "Apple ML Research", "url": "https://machinelearning.apple.com/rss.xml", "icon": "🔬", "limit": 3},
    # daily / weekly digests
    {"name": "TLDR AI", "url": "https://tldr.tech/api/rss/ai", "icon": "🗞", "limit": 1},
    {"name": "Import AI", "url": "https://importai.substack.com/feed", "icon": "🗞", "limit": 1},
    # researchers' newsletters / blogs
    {"name": "Interconnects", "url": "https://www.interconnects.ai/feed", "icon": "✍️", "limit": 2},
    {"name": "Ahead of AI", "url": "https://magazine.sebastianraschka.com/feed", "icon": "✍️", "limit": 1},
    {"name": "Lil'Log", "url": "https://lilianweng.github.io/index.xml", "icon": "✍️", "limit": 1},
    {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/", "icon": "✍️", "limit": 4},
    # Korean
    {"name": "GeekNews", "url": "https://news.hada.io/rss/news", "icon": "🇰🇷", "ai_only": True},
    # video
    {"name": "AI Explained (YouTube)", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCNJ1Ymd5yFuUPtn21xtRbbw", "icon": "▶️"},
]

# GitHub search query for brand-new repos (qualifiers for date/stars are appended in code).
# GitHub allows at most five AND/OR/NOT operators per query.
GITHUB_NEW_QUERY = "llm OR agent OR ai OR gpt OR claude"

# Keywords that mark something as AI-related (GitHub trending and Hacker News are
# not AI-only, so they get filtered). Matched case-insensitively on word boundaries.
AI_KEYWORDS: list[str] = [
    "ai",
    "llm",
    "llms",
    "gpt",
    "chatgpt",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "deepseek",
    "qwen",
    "llama",
    "mistral",
    "grok",
    "copilot",
    "cursor",
    "agent",
    "agents",
    "agentic",
    "mcp",
    "rag",
    "transformer",
    "transformers",
    "diffusion",
    "stable diffusion",
    "text-to-image",
    "text-to-video",
    "speech-to-text",
    "text-to-speech",
    "tts",
    "asr",
    "embedding",
    "embeddings",
    "vector database",
    "fine-tune",
    "fine-tuning",
    "finetune",
    "finetuning",
    "inference",
    "vllm",
    "ollama",
    "huggingface",
    "hugging face",
    "pytorch",
    "cuda",
    "nvidia",
    "machine learning",
    "deep learning",
    "neural network",
    "neural networks",
    "reinforcement learning",
    "foundation model",
    "language model",
    "multimodal",
    "vision language",
    "vla",
    "robotics",
    "computer vision",
    "prompt",
    "prompts",
    "coding assistant",
    "code generation",
    "autonomous",
    "benchmark",
    # Korean
    "인공지능",
    "언어모델",
    "언어 모델",
    "거대언어모델",
    "딥러닝",
    "머신러닝",
    "생성형",
    "챗gpt",
    "클로드",
    "오픈ai",
    "앤트로픽",
    "제미나이",
    "딥시크",
    "에이전트",
    "파운데이션 모델",
    "미스트랄",
    "허깅페이스",
]
