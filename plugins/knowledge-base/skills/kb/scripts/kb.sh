#!/bin/bash
# KB skill entry point — delegates all commands to kb.py
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/kb.py" "$@"
