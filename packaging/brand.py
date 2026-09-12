"""Shared brand artwork for every icon/tile the project ships.

One drawing routine feeds the macOS .icns, the Windows .ico, the MSIX tiles
and the Microsoft Store listing images, so the mark stays identical across
all of them. Pillow ships as a MarkItDown dependency, so nothing extra is
needed to run this.

Two primitives:
  * ``app_icon(size)``  — the self-contained icon: rounded blue tile with the
    document mark inside. Used wherever the artwork sits on an unknown
    background (Windows taskbar, Dock, Start list, Store logo).
  * ``mark(height)``    — just the document + arrow on a transparent canvas.
    Used for MSIX tiles and the splash screen, which paint the manifest's
    ``BackgroundColor`` behind the image themselves.
"""

from __future__ import annotations

from typing import Optional, Tuple

from PIL import Image, ImageDraw

# Brand palette — matches anytomd/theme.py's light accent so the installed
# app and its icon read as the same product.
BRAND_BLUE: Tuple[int, int, int, int] = (37, 99, 235, 255)
BRAND_BLUE_HEX = "#2563eb"
PAPER_WHITE: Tuple[int, int, int, int] = (255, 255, 255, 255)

RGBA = Tuple[int, int, int, int]

# The document rectangle occupies this fraction of the icon's bounding box.
# ``mark()`` uses it to work backwards from a wanted height to the icon scale.
_DOC_X0, _DOC_X1 = 0.30, 0.70
_DOC_Y0, _DOC_Y1 = 0.24, 0.76


def _draw_mark(
    d: ImageDraw.ImageDraw,
    s: float,
    ox: float = 0.0,
    oy: float = 0.0,
    *,
    paper: RGBA = PAPER_WHITE,
    ink: RGBA = BRAND_BLUE,
) -> None:
    """Draw the document-with-down-arrow mark sized to an ``s``-unit square.

    ``ox``/``oy`` shift the drawing, which lets ``mark()`` crop the artwork to
    the document's own bounds without re-deriving every coordinate.
    """
    def x(f: float) -> int:
        return int(ox + s * f)

    def y(f: float) -> int:
        return int(oy + s * f)

    # White document page.
    d.rounded_rectangle(
        [x(_DOC_X0), y(_DOC_Y0), x(_DOC_X1), y(_DOC_Y1)],
        radius=int(s * 0.04),
        fill=paper,
    )
    # Down arrow suggesting conversion: a shaft plus a triangular head.
    cx = int(ox + s // 2) if ox == 0 else int(ox + s / 2)
    half_shaft = int(s * 0.025)
    ay0, ay1 = y(0.34), y(0.56)
    d.rectangle([cx - half_shaft, ay0, cx + half_shaft, ay1], fill=ink)
    d.polygon(
        [
            (x(0.42), ay1 - int(s * 0.02)),
            (x(0.58), ay1 - int(s * 0.02)),
            (cx, y(0.66)),
        ],
        fill=ink,
    )


def app_icon(size: int) -> Image.Image:
    """The full app icon: rounded brand-blue tile with the mark inside."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    pad = int(s * 0.08)
    d.rounded_rectangle(
        [pad, pad, s - pad, s - pad], radius=int(s * 0.22), fill=BRAND_BLUE
    )
    _draw_mark(d, s)
    return img


def mark(height: int, *, paper: RGBA = PAPER_WHITE, ink: RGBA = BRAND_BLUE) -> Image.Image:
    """The document mark alone, on transparency, exactly ``height`` px tall."""
    s = height / (_DOC_Y1 - _DOC_Y0)
    width = max(1, round((_DOC_X1 - _DOC_X0) * s))
    img = Image.new("RGBA", (width, max(1, height)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _draw_mark(d, s, ox=-_DOC_X0 * s, oy=-_DOC_Y0 * s, paper=paper, ink=ink)
    return img


def tile(
    width: int,
    height: int,
    *,
    background: Optional[RGBA] = None,
    mark_fraction: float = 0.50,
    ink: RGBA = BRAND_BLUE,
    paper: RGBA = PAPER_WHITE,
) -> Image.Image:
    """A ``width``x``height`` canvas with the mark centred on it.

    ``background=None`` leaves the canvas transparent, which is what MSIX
    tiles want — Windows paints the manifest's BackgroundColor behind them.
    """
    img = Image.new("RGBA", (width, height), background or (0, 0, 0, 0))
    glyph_h = max(1, round(min(width, height) * mark_fraction))
    glyph = mark(glyph_h, paper=paper, ink=ink)
    img.alpha_composite(
        glyph, ((width - glyph.width) // 2, (height - glyph.height) // 2)
    )
    return img
