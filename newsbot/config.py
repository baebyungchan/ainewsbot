"""Settings. Everything comes from environment variables.

Locally: put them in `.env` (never committed).
GitHub Actions: Secrets (tokens) and Variables (tuning knobs), see README.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool(name: str, default: bool = False) -> bool:
    raw = _env(name).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def load_dotenv(path: str | Path = ".env") -> None:
    """Tiny .env loader (no dependency). Existing env vars win."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass
class Settings:
    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str
    dry_run: bool

    # Source credentials (all optional)
    github_token: str
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    x_rss_base: str
    x_accounts: list[str]

    # Briefing
    briefing_provider: str  # rules | claude
    claude_model: str

    # Behaviour
    state_path: Path
    max_items_per_run: int
    bootstrap_limit: int
    quiet_start_kst: int
    quiet_end_kst: int
    pending_ttl_hours: int
    seen_ttl_days: int

    # Importance thresholds
    github_trending_min_stars_today: int
    github_trending_any_topic_min: int
    github_new_min_stars: int
    github_new_max_age_days: int
    hn_min_points: int
    hn_lookback_hours: int
    reddit_default_min_score: int
    reddit_rss_top_n: int
    rss_lookback_hours: int
    hf_paper_min_upvotes: int
    hf_model_top_n: int

    @classmethod
    def from_env(cls) -> Settings:
        quiet = _env("QUIET_HOURS_KST", "0-8")
        try:
            q_start, q_end = (int(x) for x in quiet.split("-", 1))
        except ValueError:
            q_start, q_end = 0, 8
        accounts = [a.strip().lstrip("@") for a in _env("X_ACCOUNTS").split(",") if a.strip()]
        return cls(
            telegram_bot_token=_env("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=_env("TELEGRAM_CHAT_ID") or _env("TELEGRAM_DEV_CHAT_ID"),
            dry_run=_bool("DRY_RUN", False),
            github_token=_env("GH_TOKEN") or _env("GITHUB_TOKEN"),
            reddit_client_id=_env("REDDIT_CLIENT_ID"),
            reddit_client_secret=_env("REDDIT_CLIENT_SECRET"),
            reddit_user_agent=_env("REDDIT_USER_AGENT", "github-actions:ainewsbot:1.0 (personal news bot)"),
            x_rss_base=_env("X_RSS_BASE").rstrip("/"),
            x_accounts=accounts,
            briefing_provider=(_env("BRIEFING_PROVIDER", "rules") or "rules").lower(),
            claude_model=_env("CLAUDE_MODEL", "claude-opus-5"),
            state_path=Path(_env("STATE_PATH", "state/state.json")),
            max_items_per_run=_int("MAX_ITEMS_PER_RUN", 12),
            bootstrap_limit=_int("BOOTSTRAP_LIMIT", 5),
            quiet_start_kst=q_start,
            quiet_end_kst=q_end,
            pending_ttl_hours=_int("PENDING_TTL_HOURS", 36),
            seen_ttl_days=_int("SEEN_TTL_DAYS", 45),
            github_trending_min_stars_today=_int("GITHUB_TRENDING_MIN_STARS_TODAY", 500),
            github_trending_any_topic_min=_int("GITHUB_TRENDING_ANY_TOPIC_MIN", 2000),
            github_new_min_stars=_int("GITHUB_NEW_MIN_STARS", 500),
            github_new_max_age_days=_int("GITHUB_NEW_MAX_AGE_DAYS", 14),
            hn_min_points=_int("HN_MIN_POINTS", 100),
            hn_lookback_hours=_int("HN_LOOKBACK_HOURS", 36),
            reddit_default_min_score=_int("REDDIT_MIN_SCORE", 150),
            reddit_rss_top_n=_int("REDDIT_RSS_TOP_N", 5),
            rss_lookback_hours=_int("RSS_LOOKBACK_HOURS", 48),
            hf_paper_min_upvotes=_int("HF_PAPER_MIN_UPVOTES", 15),
            hf_model_top_n=_int("HF_MODEL_TOP_N", 5),
        )

    @property
    def telegram_ready(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def reddit_oauth_ready(self) -> bool:
        return bool(self.reddit_client_id and self.reddit_client_secret)
