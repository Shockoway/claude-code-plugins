#!/bin/bash
# Inject KB context when entering plan mode.
set -euo pipefail

kb_dir="${CLAUDE_PROJECT_DIR}/kb"

if [ ! -d "$kb_dir" ]; then
  exit 0
fi

plugin_root="${CLAUDE_PLUGIN_ROOT:-.}"
skill_path="${plugin_root}/skills/kb/SKILL.md"

index_file="$kb_dir/index.jsonl"
summary=""

if [ -f "$index_file" ]; then
  planned=$(grep -c '"status":"planned"' "$index_file" 2>/dev/null || echo 0)
  in_progress=$(grep -c '"status":"in-progress"' "$index_file" 2>/dev/null || echo 0)
  summary="KB tasks — planned: ${planned}, in-progress: ${in_progress}."
fi

skill_content=""
if [ -f "$skill_path" ]; then
  skill_content=$(cat "$skill_path")
fi

context="This project has a knowledge base in kb/. ${summary}
Use Skill(shockoway-knowledge-base:kb) to read charter, tasks, and ADRs before planning.

---

${skill_content}"

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": $(printf '%s' "$context" | jq -Rs .)
  }
}
EOF
