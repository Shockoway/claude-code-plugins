#!/usr/bin/env bash
# lang-daily.sh — called by the Claude Code cron trigger.
# Generates today's session and sends a macOS notification.
# Requires LANG_DB to point to the correct lang.db, or run from the language directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LANG_PY="${SCRIPT_DIR}/../skills/lang/scripts/lang.py"

# Ensure DB exists
python3 "$LANG_PY" db init

# Get due queue
QUEUE=$(python3 "$LANG_PY" queue --n=4)
QUEUE_SIZE=$(echo "$QUEUE" | python3 -c "import sys, json; q=json.load(sys.stdin)['queue']; print(len(q))")

if [ "$QUEUE_SIZE" -eq 0 ]; then
  python3 "$LANG_PY" notify "Nothing due today — great job staying on top of it!"
  exit 0
fi

# Send notification — user opens Claude Code and runs /lang-test
python3 "$LANG_PY" notify "Time to study! Run /lang to start today's session ($QUEUE_SIZE topics due)"
