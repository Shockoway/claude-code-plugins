#!/bin/bash
# Auto-rebuild kb/index.jsonl after any write/edit to a file inside kb/.
# Runs silently if kb/ does not exist in the project (safe for all projects).
set -euo pipefail

input=$(cat)

file_path=$(python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    print('')
" <<< "$input")

# Skip if no path or path is not under kb/
case "$file_path" in
  */kb/*|kb/*)
    ;;
  *)
    exit 0
    ;;
esac

# Skip if this project has no kb/ directory
if [ ! -d "${CLAUDE_PROJECT_DIR}/kb" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR}"

old_hash=$(cksum kb/index.jsonl 2>/dev/null || echo "")
python3 "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb_index.py" kb
new_hash=$(cksum kb/index.jsonl 2>/dev/null || echo "")

if [ "$old_hash" != "$new_hash" ]; then
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb_graph.py" kb build
fi
