from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Item:
    """One candidate news unit from any source.

    `score` is the raw importance signal of the source (stars today, upvotes, points ...).
    `threshold` is the bar for that source; `priority = score / threshold` makes
    sources comparable (1.0 = just made the cut).
    """

    key: str  # stable dedupe key, e.g. "gh:owner/repo", "reddit:abc123", "hn:4211"
    source: str  # github_trending | github_new | reddit | hn | rss | x
    title: str
    url: str
    summary: str = ""
    score: float = 0.0
    threshold: float = 1.0
    signal: str = ""  # short human label shown under the title
    published_at: str | None = None  # ISO 8601, UTC
    meta: dict = field(default_factory=dict)

    @property
    def priority(self) -> float:
        if self.threshold <= 0:
            return self.score
        return self.score / self.threshold

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Item:
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**known)
