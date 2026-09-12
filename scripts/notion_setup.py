"""One-time setup: create the "AI News Archive" database in Notion with the bot's integration.

Usage:
  NOTION_TOKEN=secret_xxx python scripts/notion_setup.py <parent page URL or ID>

The integration must already be connected to that parent page (page ... menu → Connections).
Prints the new database id; put it in the repo variable NOTION_DATABASE_ID.
"""

from __future__ import annotations

import os
import re
import sys

import httpx

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _sel(*names_colors: tuple[str, str]) -> dict:
    return {"options": [{"name": n, "color": c} for n, c in names_colors]}


SCHEMA = {
    "Title": {"title": {}},
    "URL": {"url": {}},
    "Kind": {"select": _sel(("논문", "purple"), ("저장소", "green"), ("모델", "orange"), ("커뮤니티", "blue"), ("블로그", "gray"), ("X", "default"))},
    "Source": {"select": {"options": []}},
    "Status": {"select": _sel(("안 읽음", "gray"), ("읽는 중", "yellow"), ("정리 완료", "green"), ("보관", "blue"))},
    "Tags": {"multi_select": _sel(("LLM", "green"), ("Agent", "red"), ("VLA", "purple"), ("Robotics", "purple"), ("CV", "blue"), ("Tooling", "yellow"), ("중요", "red"))},
    "Score": {"number": {"format": "number"}},
    "Signal": {"rich_text": {}},
    "Summary": {"rich_text": {}},
    "Discussion": {"url": {}},
    "Sent": {"date": {}},
    "Key": {"rich_text": {}},
    "Memo": {"rich_text": {}},
}


def page_id_from(arg: str) -> str:
    m = re.search(r"([0-9a-f]{32})", arg.replace("-", ""))
    if not m:
        raise SystemExit(f"could not find a page id in: {arg}")
    return m.group(1)


def main() -> int:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token or len(sys.argv) < 2:
        print(__doc__)
        return 2
    parent = page_id_from(sys.argv[1])
    resp = httpx.post(
        f"{API}/databases",
        headers={"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION},
        json={
            "parent": {"type": "page_id", "page_id": parent},
            "icon": {"type": "emoji", "emoji": "🤖"},
            "title": [{"type": "text", "text": {"content": "AI News Archive"}}],
            "properties": SCHEMA,
        },
        timeout=30.0,
    )
    if resp.status_code >= 400:
        print("Notion error", resp.status_code, resp.text[:500])
        return 1
    data = resp.json()
    print("created:", data.get("url"))
    print("NOTION_DATABASE_ID =", data["id"].replace("-", ""))
    print("next: gh variable set NOTION_DATABASE_ID --body", data["id"].replace("-", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
