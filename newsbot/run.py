"""One run = fetch → filter → queue → send → save. Designed to finish in under a minute."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import UTC, datetime, timedelta, timezone

import httpx

from newsbot import briefing, deliver, notion, rank
from newsbot.config import Settings, load_dotenv
from newsbot.fetchers import BOT_UA, github, hf, hn, reddit, rss, x
from newsbot.models import Item
from newsbot.state import State

logger = logging.getLogger("newsbot")
KST = timezone(timedelta(hours=9))


async def collect(settings: Settings, report: dict) -> list[Item]:
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers={"User-Agent": BOT_UA}) as client:
        jobs = {
            "github_trending": github.fetch_trending(client, settings),
            "github_new": github.fetch_new_repos(client, settings),
            "reddit": reddit.fetch_all(client, settings, report),
            "hn": hn.fetch(client, settings),
            "rss": rss.fetch_all(client, settings, report),
            "x": x.fetch_rss(client, settings, report),
            "hf_paper": hf.fetch_daily_papers(client, settings),
            "hf_model": hf.fetch_trending_models(client, settings),
        }
        results = await asyncio.gather(*jobs.values(), return_exceptions=True)
        items: list[Item] = []
        for name, res in zip(jobs, results):
            if isinstance(res, BaseException):
                logger.warning("%s failed: %s", name, res)
                report[name] = f"error: {res}"
                continue
            items.extend(res)
            report[name] = len(res)
        report["x_enriched"] = await x.enrich(client, items)
    return items


def in_quiet_hours(now_kst: datetime, start: int, end: int) -> bool:
    if start == end:
        return False
    h = now_kst.hour
    if start < end:
        return start <= h < end
    return h >= start or h < end  # wraps midnight, e.g. 23-7


def write_step_summary(summary: dict, messages: list[str]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = ["## AI News Bot run", "", "```json", json.dumps(summary, ensure_ascii=False, indent=2), "```"]
    if messages:
        lines += ["", "### Sent / would send", ""]
        for m in messages:
            lines += ["```html", m, "```", ""]
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="newsbot", description="AI news → Telegram, one run.")
    parser.add_argument("--dry-run", action="store_true", help="print messages, send nothing, do not touch state")
    parser.add_argument("--state", help="state file path (default state/state.json or STATE_PATH)")
    parser.add_argument("--bootstrap-limit", type=int, help="items to send on the very first run")
    parser.add_argument("--ignore-quiet-hours", action="store_true")
    parser.add_argument(
        "--absorb",
        action="store_true",
        help="mark everything currently above the bar as seen without sending (use after adding sources)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    load_dotenv()
    settings = Settings.from_env()
    if args.dry_run:
        settings.dry_run = True
    if args.state:
        from pathlib import Path

        settings.state_path = Path(args.state)
    if args.bootstrap_limit is not None:
        settings.bootstrap_limit = args.bootstrap_limit

    now = datetime.now(UTC)
    now_kst = now.astimezone(KST)
    state = State.load(settings.state_path)
    first_run = state.is_first_run
    report: dict = {}

    items = asyncio.run(collect(settings, report))
    candidates = rank.select(items)
    fresh = [it for it in candidates if state.is_new(it, now)]

    if args.absorb:
        for it in fresh:
            state.mark_seen(it, now=now)
        logger.info("absorbed %s items as seen (nothing sent)", len(fresh))
        fresh = []
    elif first_run:
        # Don't flood the chat with everything that is trending right now:
        # send the top few, remember the rest as already seen.
        fresh.sort(key=lambda i: i.priority, reverse=True)
        keep, skip = fresh[: settings.bootstrap_limit], fresh[settings.bootstrap_limit :]
        for it in skip:
            state.mark_seen(it, now=now)
        fresh = keep
    state.enqueue(fresh, now=now)
    state.touch(now)

    quiet = in_quiet_hours(now_kst, settings.quiet_start_kst, settings.quiet_end_kst) and not args.ignore_quiet_hours
    batch = [] if quiet else state.take(settings.max_items_per_run)
    messages: list[str] = []
    sent_ok = True
    if batch:
        messages = briefing.build_messages(batch, settings, now_kst)
        if settings.dry_run or not settings.telegram_ready:
            if not settings.telegram_ready and not settings.dry_run:
                logger.error("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing; nothing sent")
                sent_ok = False
            for m in messages:
                print("----- telegram message (not sent) -----")
                print(m)
        else:
            for m in messages:
                if not deliver.send_telegram(settings.telegram_bot_token, settings.telegram_chat_id, m):
                    sent_ok = False
                    break
        if sent_ok and not settings.dry_run:
            state.mark_sent(batch, now=now)
            try:
                report["notion_archived"] = notion.archive_sent(
                    batch, now, token=settings.notion_token, database_id=settings.notion_database_id
                )
            except Exception as exc:  # noqa: BLE001 — archive must never break delivery
                logger.warning("notion archive failed: %s", exc)
                report["notion_archived"] = f"error: {exc}"
        elif not settings.dry_run:
            state.requeue(batch, now=now)

    state.prune(seen_ttl_days=settings.seen_ttl_days, pending_ttl_hours=settings.pending_ttl_hours, now=now)
    if not settings.dry_run:
        state.save()

    summary = {
        "time_kst": now_kst.strftime("%Y-%m-%d %H:%M"),
        "first_run": first_run,
        "fetched": len(items),
        "above_bar": len(candidates),
        "new": len(fresh),
        "absorbed": bool(args.absorb),
        "sent": len(batch) if sent_ok and not settings.dry_run else 0,
        "would_send": len(batch) if settings.dry_run else 0,
        "still_pending": len(state.data["pending"]),
        "quiet_hours": quiet,
        "dry_run": settings.dry_run,
        "briefing": settings.briefing_provider,
        "sources": report,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    write_step_summary(summary, messages)
    return 0 if sent_ok else 1
