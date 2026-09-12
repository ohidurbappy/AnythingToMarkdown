"""Check the Store listing text and images against Partner Center's limits.

Partner Center rejects over-long fields and wrongly sized images at submission
time, which is a slow way to find out. This runs the same checks locally (and
in CI).

    python store/validate_listing.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTING = ROOT / "store" / "listing" / "en-us"
ASSETS = ROOT / "store" / "assets"

# field file -> (max characters, max lines or None for "treat as one field")
TEXT_LIMITS = {
    "description.txt": (10_000, None),
    "short-description.txt": (1_000, None),
    "release-notes.txt": (1_500, None),
    "copyright-and-trademark.txt": (200, None),
    "additional-license-terms.txt": (10_000, None),
}

# Files where each line is a separate field: (max lines, max chars per line)
PER_LINE_LIMITS = {
    "product-features.txt": (20, 200),
    "search-terms.txt": (7, 30),
    "screenshot-captions.txt": (10, 200),
}

# Exact pixel sizes Partner Center expects, by filename.
IMAGE_SIZES = {
    "StoreLogo-300x300.png": (300, 300),
    "BoxArt-1080x1080.png": (1080, 1080),
    "PosterArt-720x1080.png": (720, 1080),
    "SuperHeroArt-2400x1200.png": (2400, 1200),
    "HeroArt-1920x1080.png": (1920, 1080),
    "Promotional-414x180.png": (414, 180),
}

# Screenshots must be one of Partner Center's accepted desktop sizes.
SCREENSHOT_SIZES = {(1366, 768), (1920, 1080), (3840, 2160)}
MAX_IMAGE_BYTES = 50 * 1024 * 1024


def check() -> list[str]:
    problems: list[str] = []

    for name, (max_chars, _) in TEXT_LIMITS.items():
        path = LISTING / name
        if not path.exists():
            problems.append(f"{name}: missing")
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            problems.append(f"{name}: empty")
        elif len(text) > max_chars:
            problems.append(f"{name}: {len(text)} chars exceeds the {max_chars} limit")

    for name, (max_lines, max_chars) in PER_LINE_LIMITS.items():
        path = LISTING / name
        if not path.exists():
            problems.append(f"{name}: missing")
            continue
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if len(lines) > max_lines:
            problems.append(f"{name}: {len(lines)} entries exceeds the {max_lines} limit")
        for i, line in enumerate(lines, start=1):
            # Captions are stored as "filename | caption"; only the caption counts.
            value = line.split("|", 1)[1].strip() if name.endswith("captions.txt") and "|" in line else line
            if len(value) > max_chars:
                problems.append(f"{name} line {i}: {len(value)} chars exceeds the {max_chars} limit")

    # Search terms additionally have a combined word budget.
    terms_path = LISTING / "search-terms.txt"
    if terms_path.exists():
        words = terms_path.read_text(encoding="utf-8").split()
        if len(words) > 21:
            problems.append(f"search-terms.txt: {len(words)} words exceeds the 21-word total")

    try:
        from PIL import Image
    except ImportError:
        problems.append("Pillow not installed — skipped image checks")
        return problems

    for name, expected in IMAGE_SIZES.items():
        path = ASSETS / name
        if not path.exists():
            problems.append(f"assets/{name}: missing (run store/make_store_assets.py)")
            continue
        size = Image.open(path).size
        if size != expected:
            problems.append(f"assets/{name}: is {size[0]}x{size[1]}, expected {expected[0]}x{expected[1]}")
        if path.stat().st_size > MAX_IMAGE_BYTES:
            problems.append(f"assets/{name}: larger than 50 MB")

    shots = sorted((ASSETS / "screenshots").glob("*.png"))
    if not shots:
        problems.append("assets/screenshots: none found — the Store requires at least one (run store/make_screenshots.py)")
    for shot in shots:
        size = Image.open(shot).size
        if size not in SCREENSHOT_SIZES:
            allowed = ", ".join(f"{w}x{h}" for w, h in sorted(SCREENSHOT_SIZES))
            problems.append(f"screenshots/{shot.name}: is {size[0]}x{size[1]}; Partner Center accepts {allowed}")

    # Every screenshot should have a caption, and vice versa.
    captions_path = LISTING / "screenshot-captions.txt"
    if captions_path.exists() and shots:
        captioned = {
            ln.split("|", 1)[0].strip()
            for ln in captions_path.read_text(encoding="utf-8").splitlines()
            if "|" in ln
        }
        for shot in shots:
            if shot.name not in captioned:
                problems.append(f"screenshot-captions.txt: no caption for {shot.name}")
        for name in captioned - {s.name for s in shots}:
            problems.append(f"screenshot-captions.txt: caption for missing screenshot {name}")

    return problems


def main() -> int:
    problems = check()
    if problems:
        print("Store listing problems:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("Store listing OK: text within Partner Center limits, images correctly sized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
