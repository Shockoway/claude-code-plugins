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

# Add skill invocation hint at the beginning
skill_with_hint="**⚠️ For agents: The KB skill is registered as \`kb\` (not by plugin name). Use \`Skill(kb)\` to invoke.**

---

$skill_content"

# Format as JSON hook output with additionalContext
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStart",
    "additionalContext": $(printf '%s' "$skill_with_hint" | jq -Rs .)
  }
}
EOF
