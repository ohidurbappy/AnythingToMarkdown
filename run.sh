#!/usr/bin/env bash
# Launch AnythingToMarkdown on macOS / Linux.
# Sets up the virtual environment on first run, then forwards all arguments.
#   ./run.sh                 -> opens the GUI
#   ./run.sh file.pdf        -> CLI: convert file.pdf
#   ./run.sh --help          -> CLI help
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"

# Pick a Python >= 3.10 for first-time setup.
pick_python() {
    for c in python3.13 python3.12 python3.11 python3.10 python3 python; do
        if command -v "$c" >/dev/null 2>&1; then
            ver="$("$c" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo 0.0)"
            major="${ver%%.*}"; minor="${ver##*.}"
            if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; then echo "$c"; return 0; fi
        fi
    done
    return 1
}

if [ ! -d "$VENV" ]; then
    echo "Setting up virtual environment (first run)…"
    PY="$(pick_python)" || { echo "Error: Python 3.10+ is required." >&2; exit 1; }
    "$PY" -m venv "$VENV"
    "$VENV/bin/python" -m pip install --upgrade pip >/dev/null
    "$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt"
fi

exec "$VENV/bin/python" -m anytomd "$@"
