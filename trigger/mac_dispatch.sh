#!/bin/zsh
# Laptop-side stopgap trigger: asks GitHub to run the bot workflow (skips if one is already running).
# Installed as a launchd agent (see README) — only works while this Mac is awake.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
REPO="baebyungchan/ainewsbot"
busy=$(gh run list -R "$REPO" --workflow newsbot.yml --limit 3 --json status --jq '[.[]|select(.status!="completed")]|length' 2>/dev/null || echo 0)
if [ "${busy:-0}" -eq 0 ]; then
  if gh workflow run newsbot.yml -R "$REPO" >/dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M') dispatched"
  else
    echo "$(date '+%Y-%m-%d %H:%M') dispatch FAILED (gh auth?)"
  fi
else
  echo "$(date '+%Y-%m-%d %H:%M') skipped: run in progress"
fi
