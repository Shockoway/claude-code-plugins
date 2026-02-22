#!/bin/bash
# Inject KB skill into subagent context
set -euo pipefail

# Read the KB skill content
plugin_root="${CLAUDE_PLUGIN_ROOT:-.}"
skill_path="${plugin_root}/skills/kb/SKILL.md"

if [ ! -f "$skill_path" ]; then
  exit 0
fi

# Read skill content and escape for JSON
skill_content=$(cat "$skill_path")

# Format as JSON hook output with additionalContext
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStart",
    "additionalContext": $(printf '%s' "$skill_content" | jq -Rs .)
  }
}
EOF
