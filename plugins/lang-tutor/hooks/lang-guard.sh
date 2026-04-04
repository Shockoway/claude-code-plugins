#!/usr/bin/env bash
# lang-guard.sh — PreToolUse hook: block direct sqlite3 access to lang.db.
# Receives tool call JSON on stdin; exits 2 to block.

INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('command', ''))
" 2>/dev/null || echo "")

# Block sqlite3 CLI targeting lang.db
if printf '%s' "$COMMAND" | grep -qE 'sqlite3[^|]*lang\.db|lang\.db[^|]*sqlite3'; then
  echo "BLOCKED: Direct sqlite3 access to lang.db is not allowed."
  echo ""
  echo "Use lang.py instead:"
  echo "  python3 \"\${CLAUDE_PLUGIN_ROOT}/skills/lang/scripts/lang.py\" db init"
  echo "  python3 \"\${CLAUDE_PLUGIN_ROOT}/skills/lang/scripts/lang.py\" profile save '<json>'"
  echo "  python3 \"\${CLAUDE_PLUGIN_ROOT}/skills/lang/scripts/lang.py\" roadmap save '<json_array>'"
  echo "  python3 \"\${CLAUDE_PLUGIN_ROOT}/skills/lang/scripts/lang.py\" <command>"
  echo ""
  echo "Available commands: db, profile, roadmap, queue, session, attempt, mastery, analytics, dashboard, calendar, notify"
  exit 2
fi
