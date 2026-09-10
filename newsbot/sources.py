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

# Official / high-signal blogs. Low volume, so every new post is sent.
RSS_FEEDS: list[tuple[str, str]] = [
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Anthropic", "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
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
]
