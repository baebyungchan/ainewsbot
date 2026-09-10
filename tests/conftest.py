import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def settings(monkeypatch):
    for k in list(os.environ):
        if k.startswith(("TELEGRAM_", "REDDIT_", "GITHUB_", "GH_", "X_", "HN_", "BRIEFING", "DRY_RUN", "QUIET", "MAX_ITEMS", "BOOTSTRAP")):
            monkeypatch.delenv(k, raising=False)
    from newsbot.config import Settings

    return Settings.from_env()
