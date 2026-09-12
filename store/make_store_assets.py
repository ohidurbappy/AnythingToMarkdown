"""Generate the branding images the Microsoft Store listing asks for.

Partner Center's "Store logos" section takes a few fixed aspect ratios that
it crops into the various Store surfaces. These are brand images, not
screenshots — screenshots come from store/make_screenshots.py, which captures
the real app.

    python store/make_store_assets.py [--out DIR]

Artwork comes from packaging/brand.py so the Store images, the MSIX tiles and
the desktop icons are all the same mark.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packaging"))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from brand import mark  # noqa: E402
from version_tool import read_app_name  # noqa: E402

DEFAULT_OUT = ROOT / "store" / "assets"

APP_NAME = read_app_name()   # single source: anytomd.__app_name__
TAGLINE = "Convert documents to clean Markdown"

# Vertical gradient: brand blue into a deeper blue, so the white mark and
# type stay readable wherever the Store crops the image.
GRADIENT_TOP = (37, 99, 235)
GRADIENT_BOTTOM = (23, 55, 148)

# Font candidates per platform, most preferred first.
BOLD_FONTS = (
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)
REGULAR_FONTS = (
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)


def _font(candidates: Tuple[str, ...], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    print(
        "Warning: no system TrueType font found — falling back to Pillow's "
        "bitmap font, which will look poor at these sizes.",
        file=sys.stderr,
    )
    return ImageFont.load_default()


def _fit_font(
    candidates: Tuple[str, ...], size: int, text: str, max_width: int
) -> ImageFont.ImageFont:
    """Pick the largest size at or below ``size`` whose text fits ``max_width``.

    "AnythingToMarkdown" is a long word: on the 2:3 poster a size chosen from
    the canvas height alone runs into the margins.
    """
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    while size > 8:
        font = _font(candidates, size)
        box = measure.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
        size = int(size * 0.94)
    return _font(candidates, size)


def _gradient(width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height))
    d = ImageDraw.Draw(img)
    for y in range(height):
        t = y / max(1, height - 1)
        d.line(
            [(0, y), (width, y)],
            fill=tuple(
                round(a + (b - a) * t)
                for a, b in zip(GRADIENT_TOP, GRADIENT_BOTTOM)
            ),
        )
    return img.convert("RGBA")


def _centred_text(
    d: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    centre_x: int,
    top_y: int,
    fill,
) -> int:
    """Draw text horizontally centred on ``centre_x``; return its height."""
    left, top, right, bottom = d.textbbox((0, 0), text, font=font)
    d.text((centre_x - (right - left) / 2 - left, top_y - top), text, font=font, fill=fill)
    return bottom - top


def stacked(width: int, height: int, *, show_tagline: bool = True) -> Image.Image:
    """Mark above the product name — used for the square and portrait art."""
    img = _gradient(width, height)
    d = ImageDraw.Draw(img)

    unit = min(width, height)
    glyph = mark(round(unit * 0.30))
    safe_width = round(width * 0.84)   # keep clear of the Store's own cropping
    title_font = _fit_font(BOLD_FONTS, max(10, round(unit * 0.082)), APP_NAME, safe_width)
    tag_font = _fit_font(REGULAR_FONTS, max(8, round(unit * 0.040)), TAGLINE, safe_width)

    gap = round(unit * 0.07)
    title_h = d.textbbox((0, 0), APP_NAME, font=title_font)[3]
    tag_h = d.textbbox((0, 0), TAGLINE, font=tag_font)[3] if show_tagline else 0
    total = glyph.height + gap + title_h + (round(unit * 0.035) + tag_h if show_tagline else 0)

    y = (height - total) // 2
    img.alpha_composite(glyph, ((width - glyph.width) // 2, y))
    y += glyph.height + gap
    y += _centred_text(d, APP_NAME, title_font, width // 2, y, (255, 255, 255, 255))
    if show_tagline:
        y += round(unit * 0.035)
        _centred_text(d, TAGLINE, tag_font, width // 2, y, (219, 234, 254, 255))
    return img


def banner(width: int, height: int) -> Image.Image:
    """Mark beside the product name — used for the wide promotional art."""
    img = _gradient(width, height)
    d = ImageDraw.Draw(img)

    glyph = mark(round(height * 0.46))
    safe_width = round(width * 0.62)   # the mark takes the rest of the row
    title_font = _fit_font(BOLD_FONTS, max(10, round(height * 0.155)), APP_NAME, safe_width)
    tag_font = _fit_font(REGULAR_FONTS, max(8, round(height * 0.075)), TAGLINE, safe_width)

    title_box = d.textbbox((0, 0), APP_NAME, font=title_font)
    tag_box = d.textbbox((0, 0), TAGLINE, font=tag_font)
    text_w = max(title_box[2] - title_box[0], tag_box[2] - tag_box[0])
    gap = round(height * 0.10)

    block_w = glyph.width + gap + text_w
    x = (width - block_w) // 2
    img.alpha_composite(glyph, (x, (height - glyph.height) // 2))

    text_x = x + glyph.width + gap
    line_gap = round(height * 0.05)
    text_h = (title_box[3] - title_box[1]) + line_gap + (tag_box[3] - tag_box[1])
    y = (height - text_h) // 2
    d.text((text_x - title_box[0], y - title_box[1]), APP_NAME,
           font=title_font, fill=(255, 255, 255, 255))
    y += (title_box[3] - title_box[1]) + line_gap
    d.text((text_x - tag_box[0], y - tag_box[1]), TAGLINE,
           font=tag_font, fill=(219, 234, 254, 255))
    return img


def generate(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def save(img: Image.Image, name: str) -> None:
        path = out_dir / name
        img.convert("RGB").save(path, format="PNG")
        written.append(path)
        print(f"  {name}  ({img.width}x{img.height})")

    print("Store branding images:")
    # 300x300 Store logo: mark only. It renders small in the Store, so text
    # would be unreadable.
    logo = _gradient(300, 300)
    glyph = mark(round(300 * 0.52))
    logo.alpha_composite(glyph, ((300 - glyph.width) // 2, (300 - glyph.height) // 2))
    save(logo, "StoreLogo-300x300.png")

    save(stacked(1080, 1080), "BoxArt-1080x1080.png")          # 1:1
    save(stacked(720, 1080), "PosterArt-720x1080.png")         # 2:3
    save(banner(2400, 1200), "SuperHeroArt-2400x1200.png")     # 16:9-ish
    save(banner(1920, 1080), "HeroArt-1920x1080.png")          # 16:9
    save(banner(414, 180), "Promotional-414x180.png")          # 2.3:1
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    written = generate(args.out)
    print(f"\nWrote {len(written)} images to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
