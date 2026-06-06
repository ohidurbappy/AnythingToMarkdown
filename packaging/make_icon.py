"""Generate the macOS app icon set (packaging/AppIcon.iconset).

Run via `make icon`, which then calls `iconutil` to produce AppIcon.icns.
Pillow ships with MarkItDown, so no extra dependency is needed.
"""

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent


def make(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    # Rounded blue background tile (macOS-style).
    pad = int(s * 0.08)
    r = int(s * 0.22)
    d.rounded_rectangle([pad, pad, s - pad, s - pad], radius=r, fill=(37, 99, 235, 255))
    # White document page.
    dx0, dy0, dx1, dy1 = int(s * 0.30), int(s * 0.24), int(s * 0.70), int(s * 0.76)
    d.rounded_rectangle([dx0, dy0, dx1, dy1], radius=int(s * 0.04), fill=(255, 255, 255, 255))
    # Down arrow suggesting conversion.
    cx = s // 2
    ax0, ax1 = int(s * 0.42), int(s * 0.58)
    ay0, ay1 = int(s * 0.34), int(s * 0.56)
    d.rectangle([cx - int(s * 0.025), ay0, cx + int(s * 0.025), ay1], fill=(37, 99, 235, 255))
    d.polygon(
        [(ax0, ay1 - int(s * 0.02)), (ax1, ay1 - int(s * 0.02)), (cx, int(s * 0.66))],
        fill=(37, 99, 235, 255),
    )
    return img


def main() -> None:
    # macOS .iconset PNGs (fed to `iconutil` to make AppIcon.icns).
    iconset = HERE / "AppIcon.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    specs = [(16, 1), (16, 2), (32, 1), (32, 2), (128, 1),
             (128, 2), (256, 1), (256, 2), (512, 1), (512, 2)]
    for base, scale in specs:
        name = f"icon_{base}x{base}{'@2x' if scale == 2 else ''}.png"
        make(base * scale).save(iconset / name)
    print(f"Wrote {len(specs)} PNGs to {iconset}")

    # Windows .ico (multi-resolution, used by the Windows PyInstaller build).
    ico_path = HERE / "AppIcon.ico"
    sizes = [16, 24, 32, 48, 64, 128, 256]
    make(256).save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"Wrote {ico_path}")


if __name__ == "__main__":
    main()
