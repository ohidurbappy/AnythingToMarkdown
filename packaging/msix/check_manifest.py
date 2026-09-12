"""Validate the MSIX manifest template without needing Windows.

The real package can only be built on a machine with the Windows SDK, so the
cheap mistakes — a malformed manifest, a logo that points at a file nobody
generated, a stray placeholder — would otherwise only surface in CI on
Windows, or worse, at Store certification. This reproduces the substitution
that build_msix.ps1 performs and checks the result.

    python packaging/msix/check_manifest.py
"""

from __future__ import annotations

import json
import re
import sys
import xml.dom.minidom as minidom
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "AppxManifest.xml"
IDENTITY = HERE / "identity.json"
ASSETS = HERE / "Assets"

# Partner Center's rules for the product identity fields. Getting these wrong
# is only discovered at upload time, which is a slow way to find out.
IDENTITY_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]{2,49}$")
PUBLISHER_RE = re.compile(r"^CN=.+")

# The same tokens build_msix.ps1 substitutes, with stand-in values.
SUBSTITUTIONS = {
    "VERSION": "1.0.0.0",
    "IDENTITY_NAME": "ExamplePublisher.AnythingToMarkdown",
    "PUBLISHER": "CN=EXAMPLE",
    "PUBLISHER_DISPLAY_NAME": "Example Publisher",
    "DISPLAY_NAME": "AnythingToMarkdown",
}

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")
ASSET_REF_RE = re.compile(r"Assets\\([A-Za-z0-9]+)\.png")


def check_identity() -> list[str]:
    """The three values that must match Partner Center exactly."""
    if not IDENTITY.exists():
        return [f"{IDENTITY} is missing"]
    try:
        data = json.loads(IDENTITY.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"identity.json is not valid JSON: {exc}"]

    problems: list[str] = []
    for field in ("identityName", "publisher", "publisherDisplayName", "displayName"):
        if not str(data.get(field, "")).strip():
            problems.append(f"identity.json: {field} is missing or empty")

    name = str(data.get("identityName", ""))
    if name and not IDENTITY_NAME_RE.fullmatch(name):
        problems.append(
            f"identity.json: identityName {name!r} is not a valid package name "
            "(3-50 chars, letters/digits/dots/hyphens, must start alphanumeric)"
        )

    publisher = str(data.get("publisher", ""))
    if publisher and not PUBLISHER_RE.match(publisher):
        problems.append(
            f"identity.json: publisher {publisher!r} must be a distinguished "
            "name starting with 'CN=' — copy it verbatim from Partner Center"
        )

    # The Store tile shows ShortName; over 40 characters it is truncated.
    display = str(data.get("displayName", ""))
    if len(display) > 40:
        problems.append(
            f"identity.json: displayName is {len(display)} chars; the tile "
            "ShortName is truncated past 40"
        )

    # The name Windows shows must match the name the app shows about itself,
    # or the Start menu entry and the window title disagree.
    init_py = HERE.parent.parent / "anytomd" / "__init__.py"
    match = re.search(
        r'^__app_name__\s*=\s*["\']([^"\']+)["\']',
        init_py.read_text(encoding="utf-8"),
        re.M,
    )
    if match and display and match.group(1) != display:
        problems.append(
            f"identity.json displayName {display!r} does not match "
            f"anytomd.__app_name__ {match.group(1)!r}"
        )
    return problems


def check() -> list[str]:
    problems: list[str] = check_identity()

    if not MANIFEST.exists():
        return problems + [f"{MANIFEST} is missing"]

    template = MANIFEST.read_text(encoding="utf-8")

    # Every token must be one build_msix.ps1 knows how to fill in.
    for token in set(PLACEHOLDER_RE.findall(template)):
        if token.strip("{}") not in SUBSTITUTIONS:
            problems.append(
                f"manifest uses {token}, which build_msix.ps1 does not substitute"
            )

    text = template
    for key, value in SUBSTITUTIONS.items():
        text = text.replace("{{%s}}" % key, value)

    # build_msix.ps1 refuses to pack if anything double-braced survives — that
    # includes prose in comments, which is how this check earns its keep.
    leftover = PLACEHOLDER_RE.findall(text)
    if leftover:
        problems.append(
            f"{sorted(set(leftover))} survives substitution, so build_msix.ps1 "
            "would abort (a comment must not contain double-brace tokens)"
        )

    try:
        doc = minidom.parseString(text)
    except Exception as exc:
        problems.append(f"substituted manifest is not well-formed XML: {exc}")
        return problems

    identity = doc.getElementsByTagName("Identity")
    if not identity:
        problems.append("no <Identity> element")
    elif not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", identity[0].getAttribute("Version")):
        problems.append("Identity/@Version is not a four-part version")

    apps = doc.getElementsByTagName("Application")
    if len(apps) != 1:
        problems.append(f"expected exactly one <Application>, found {len(apps)}")
    elif apps[0].getAttribute("EntryPoint") != "Windows.FullTrustApplication":
        problems.append("Application/@EntryPoint must be Windows.FullTrustApplication")

    # Each referenced logo resolves through resources.pri to a qualified file
    # such as Square44x44Logo.scale-200.png, so at least one must exist.
    for ref in sorted(set(ASSET_REF_RE.findall(text))):
        if not list(ASSETS.glob(f"{ref}.*.png")):
            problems.append(
                f"manifest references Assets\\{ref}.png but no {ref}.*.png exists "
                "— run packaging/msix/make_msix_assets.py"
            )

    return problems


def main() -> int:
    problems = check()
    if problems:
        print("MSIX manifest problems:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("MSIX manifest OK: identity valid, substitutes cleanly, valid XML, "
          "all logos present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
