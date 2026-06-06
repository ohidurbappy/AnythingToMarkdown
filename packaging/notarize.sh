#!/usr/bin/env bash
# Sign, notarize, and staple the macOS app + .dmg for Gatekeeper-clean distribution.
#
# Requires an Apple Developer account ($99/yr) and a "Developer ID Application"
# certificate installed in your login keychain.
#
# ---- Configuration (environment variables) --------------------------------
#   SIGN_IDENTITY     Required. The codesign identity, e.g.
#                     "Developer ID Application: Your Name (TEAMID1234)".
#                     List yours with:  security find-identity -v -p codesigning
#
#   Notary credentials — provide ONE of:
#     NOTARY_PROFILE  Name of a stored notarytool keychain profile. Create once:
#                       xcrun notarytool store-credentials "MyProfile" \
#                         --apple-id you@example.com --team-id TEAMID1234 \
#                         --password <app-specific-password>
#   ...or all three of:
#     APPLE_ID        Your Apple ID email.
#     TEAM_ID         Your 10-character Team ID.
#     APPLE_PASSWORD  An app-specific password (appleid.apple.com → Security).
#
# Usage:
#   SIGN_IDENTITY="Developer ID Application: …" NOTARY_PROFILE=MyProfile \
#     packaging/notarize.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
VENV="$ROOT/.venv"
APP="$ROOT/dist/AnythingToMarkdown.app"
ENTITLEMENTS="$HERE/entitlements.plist"

die() { echo "Error: $*" >&2; exit 1; }

# ---- Validate configuration -----------------------------------------------
[ -n "${SIGN_IDENTITY:-}" ] || die "SIGN_IDENTITY is not set. See the header of this script."

NOTARY_AUTH=()
if [ -n "${NOTARY_PROFILE:-}" ]; then
    NOTARY_AUTH=(--keychain-profile "$NOTARY_PROFILE")
elif [ -n "${APPLE_ID:-}" ] && [ -n "${TEAM_ID:-}" ] && [ -n "${APPLE_PASSWORD:-}" ]; then
    NOTARY_AUTH=(--apple-id "$APPLE_ID" --team-id "$TEAM_ID" --password "$APPLE_PASSWORD")
else
    die "No notary credentials. Set NOTARY_PROFILE, or APPLE_ID + TEAM_ID + APPLE_PASSWORD."
fi

command -v xcrun >/dev/null || die "xcrun not found (install Xcode command line tools)."

# ---- 1. Build the app, signed with the hardened runtime -------------------
echo "==> Building and signing the app…"
MACOS_CODESIGN_IDENTITY="$SIGN_IDENTITY" \
MACOS_ENTITLEMENTS="$ENTITLEMENTS" \
    "$HERE/build_macos.sh"

[ -d "$APP" ] || die "App was not produced at $APP"

echo "==> Verifying signature…"
codesign --verify --deep --strict --verbose=2 "$APP"

# ---- 2. Package the (signed) app into a .dmg ------------------------------
echo "==> Building the .dmg…"
"$HERE/build_dmg.sh"

VERSION="$("$VENV/bin/python" -c "import sys; sys.path.insert(0,'$ROOT'); import anytomd; print(anytomd.__version__)" 2>/dev/null || echo "1.0.0")"
DMG="$ROOT/dist/AnythingToMarkdown-$VERSION.dmg"
[ -f "$DMG" ] || die "DMG not found at $DMG"

# Sign the disk image itself, too.
echo "==> Signing the .dmg…"
codesign --force --sign "$SIGN_IDENTITY" --timestamp "$DMG"

# ---- 3. Submit to Apple's notary service and wait -------------------------
echo "==> Submitting to Apple notary service (this can take a few minutes)…"
xcrun notarytool submit "$DMG" "${NOTARY_AUTH[@]}" --wait

# ---- 4. Staple the ticket to both the dmg and the app ---------------------
echo "==> Stapling notarization ticket…"
xcrun stapler staple "$DMG"
xcrun stapler staple "$APP"

# ---- 5. Final Gatekeeper assessment ---------------------------------------
echo "==> Gatekeeper assessment:"
spctl --assess --type open --context context:primary-signature --verbose=2 "$DMG" || true
xcrun stapler validate "$DMG"

echo
echo "Done. Notarized & stapled: $DMG"
echo "This can be distributed without Gatekeeper warnings."
