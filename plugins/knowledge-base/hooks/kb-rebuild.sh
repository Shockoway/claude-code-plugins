#!/bin/bash
# Rebuild kb/index.jsonl and kb/graph.json if kb/ exists in the project.
set -euo pipefail

if [ ! -d "${CLAUDE_PROJECT_DIR}/kb" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR}"

python3 "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb_index.py" kb
python3 "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb_graph.py" kb build
