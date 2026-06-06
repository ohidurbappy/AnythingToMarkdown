#!/usr/bin/env bash
# Build a distributable .dmg for macOS with a drag-to-Applications layout.
# Uses only macOS built-ins (hdiutil) — no extra dependencies.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
APP="$ROOT/dist/AnythingToMarkdown.app"
VENV="$ROOT/.venv"
VOLNAME="AnythingToMarkdown"

# Use the venv's Python locally, or whatever Python is on PATH in CI.
PY="$VENV/bin/python"
[ -x "$PY" ] || PY="$(command -v python3 || command -v python)"

# Build the .app first if it isn't there yet.
if [ ! -d "$APP" ]; then
    echo "App not found — building it first…"
    "$HERE/build_macos.sh"
fi

# Resolve the version for the output filename (falls back gracefully).
VERSION="$("$PY" -c "import sys; sys.path.insert(0,'$ROOT'); import anytomd; print(anytomd.__version__)" 2>/dev/null || echo "1.0.0")"
DMG="$ROOT/dist/AnythingToMarkdown-$VERSION.dmg"

echo "Packaging $APP -> $DMG"

# Stage the contents: the app + a symlink to /Applications for drag-install.
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

# Create a compressed, read-only DMG.
rm -f "$DMG"
hdiutil create \
    -volname "$VOLNAME" \
    -srcfolder "$STAGING" \
    -fs HFS+ \
    -format UDZO \
    -imagekey zlib-level=9 \
    -ov \
    "$DMG" >/dev/null

SIZE="$(du -h "$DMG" | awk '{print $1}')"
echo
echo "Built: $DMG  ($SIZE)"
echo "Distribute this single file. Users open it and drag the app to Applications."
