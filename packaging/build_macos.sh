#!/usr/bin/env bash
# Build the clickable AnythingToMarkdown.app for macOS.
# Run from anywhere; uses the project's .venv.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
VENV="$ROOT/.venv"

if [ ! -x "$VENV/bin/python" ]; then
    echo "Error: virtual environment not found at $VENV" >&2
    echo "Run ./run.sh once first to create it." >&2
    exit 1
fi

# Ensure PyInstaller is available.
"$VENV/bin/python" -m pip install --quiet pyinstaller

cd "$HERE"
"$VENV/bin/pyinstaller" AnythingToMarkdown.spec \
    --noconfirm --clean \
    --distpath "$ROOT/dist" \
    --workpath "$ROOT/build"

echo
echo "Built: $ROOT/dist/AnythingToMarkdown.app"
echo "Double-click it in Finder, or run: open '$ROOT/dist/AnythingToMarkdown.app'"
