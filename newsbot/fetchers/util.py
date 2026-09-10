from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src", "s", "t",
}

_WS = re.compile(r"\s+")
_TAG = re.compile(r"<[^>]+>")


def strip_html(text: str | None) -> str:
    return _WS.sub(" ", _TAG.sub(" ", text or "")).strip()


def squash(text: str | None) -> str:
    return _WS.sub(" ", text or "").strip()


def clip(text: str, limit: int) -> str:
    text = squash(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def canonical_url(url: str) -> str:
    """Normalise a URL so the same page from two sources dedupes."""
    parsed = urlparse((url or "").strip())
    scheme = (parsed.scheme or "https").lower()
    host = parsed.netloc.lower()
    host = host.removeprefix("www.")
    if host in {"twitter.com", "mobile.twitter.com", "x.com"}:
        host = "x.com"
    path = parsed.path.rstrip("/") or "/"
    if host == "github.com":
        path = path.lower()
    pairs = parse_qs(parsed.query, keep_blank_values=False)
    kept = {k: v for k, v in pairs.items() if k.lower() not in TRACKING_PARAMS}
    query = urlencode(sorted((k, vv) for k, vals in kept.items() for vv in vals), doseq=True)
    return urlunparse((scheme, host, path, "", query, ""))


def parse_int(text: str | None) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def iso_from_epoch(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    try:
        return datetime.fromtimestamp(float(epoch), tz=UTC).isoformat()
    except (ValueError, OverflowError, TypeError):
        return None


def iso_from_struct(struct) -> str | None:
    """feedparser gives time.struct_time (already UTC)."""
    if not struct:
        return None
    try:
        return datetime(*struct[:6], tzinfo=UTC).isoformat()
    except (ValueError, TypeError):
        return None


def age_hours(iso: str | None, now: datetime) -> float | None:
    if not iso:
        return None
    try:
        then = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=UTC)
    return (now - then).total_seconds() / 3600.0


X_STATUS_RE = re.compile(r"^https?://(?:www\.|mobile\.)?(?:twitter|x)\.com/([A-Za-z0-9_]+)/status/(\d+)")


def x_status(url: str) -> tuple[str, str] | None:
    m = X_STATUS_RE.match(url or "")
    if not m:
        return None
    return m.group(1), m.group(2)
