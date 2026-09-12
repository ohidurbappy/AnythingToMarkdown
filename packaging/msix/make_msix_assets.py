"""Generate every image the MSIX package needs.

Windows resolves tile/logo images by filename qualifier, so each logo has to
exist at several scales (and the 44x44 app-list icon additionally at several
"target sizes", both plated and unplated). Missing files don't fail the build
— they fail Store certification, or quietly show a blank tile — so this
script writes the complete set.

    python packaging/msix/make_msix_assets.py [--out DIR]

Artwork comes from packaging/brand.py, the same routine that draws the macOS
.icns and the Windows .ico.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from brand import app_icon, tile  # noqa: E402  (needs the sys.path tweak above)

DEFAULT_OUT = HERE / "Assets"

# Windows ships tiles at these DPI scales. The pixel sizes below are exactly
# the ones in Microsoft's asset-size tables (they round .5 up, not to even).
SCALES = (100, 125, 150, 200, 400)

# The app-list / taskbar icon is also requested at fixed "target sizes" that
# ignore scale. Unplated variants are used where Windows doesn't draw a
# coloured plate behind the icon (taskbar, Alt+Tab, Task Manager).
TARGET_SIZES = (16, 24, 32, 48, 256)


def scaled(value: int, scale: int) -> int:
    """Scale a base dimension the way Microsoft's asset tables do."""
    return int(math.floor(value * scale / 100 + 0.5))


def save(img, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")


def generate(out_dir: Path) -> int:
    written = 0

    # --- Square44x44Logo: app list, taskbar, title bar, file associations ---
    # Self-contained artwork (rounded brand tile) so it reads on any surface.
    for scale in SCALES:
        size = scaled(44, scale)
        save(app_icon(size), out_dir / f"Square44x44Logo.scale-{scale}.png")
        written += 1
    for target in TARGET_SIZES:
        icon = app_icon(target)
        for suffix in ("", "_altform-unplated", "_altform-lightunplated"):
            save(icon, out_dir / f"Square44x44Logo.targetsize-{target}{suffix}.png")
            written += 1

    # --- StoreLogo: shown in the Store listing and in Apps & features -------
    for scale in SCALES:
        save(app_icon(scaled(50, scale)), out_dir / f"StoreLogo.scale-{scale}.png")
        written += 1

    # --- Start menu tiles --------------------------------------------------
    # Transparent background: Windows paints the manifest's BackgroundColor
    # behind these, so the mark sits on the brand colour on every tile size.
    square_tiles = (
        (71, 0.52),    # small tile
        (150, 0.44),   # medium tile (also the default Start tile)
        (310, 0.36),   # large tile
    )
    for base, fraction in square_tiles:
        for scale in SCALES:
            size = scaled(base, scale)
            save(
                tile(size, size, mark_fraction=fraction),
                out_dir / f"Square{base}x{base}Logo.scale-{scale}.png",
            )
            written += 1

    # Wide tile (310x150).
    for scale in SCALES:
        w, h = scaled(310, scale), scaled(150, scale)
        save(
            tile(w, h, mark_fraction=0.52),
            out_dir / f"Wide310x150Logo.scale-{scale}.png",
        )
        written += 1

    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT,
        help=f"Directory to write the assets into (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args(argv)

    count = generate(args.out)
    print(f"Wrote {count} MSIX assets to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
