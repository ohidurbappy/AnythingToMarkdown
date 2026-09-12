"""Generate the desktop app icons.

  * packaging/AppIcon.iconset/  — PNGs that `iconutil` turns into AppIcon.icns
  * packaging/AppIcon.ico       — multi-resolution Windows icon

Run via `make icon`. The artwork itself lives in packaging/brand.py so the
macOS/Windows icons, the MSIX tiles and the Store images can never drift
apart. Pillow ships with MarkItDown, so no extra dependency is needed.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from brand import app_icon  # noqa: E402  (needs the sys.path tweak above)


def make(size: int):
    """Backwards-compatible alias for the shared artwork routine."""
    return app_icon(size)


def main() -> None:
    # macOS .iconset PNGs (fed to `iconutil` to make AppIcon.icns).
    iconset = HERE / "AppIcon.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    specs = [(16, 1), (16, 2), (32, 1), (32, 2), (128, 1),
             (128, 2), (256, 1), (256, 2), (512, 1), (512, 2)]
    for base, scale in specs:
        name = f"icon_{base}x{base}{'@2x' if scale == 2 else ''}.png"
        app_icon(base * scale).save(iconset / name)
    print(f"Wrote {len(specs)} PNGs to {iconset}")

    # Windows .ico (multi-resolution, used by the Windows PyInstaller build).
    ico_path = HERE / "AppIcon.ico"
    sizes = [16, 24, 32, 48, 64, 128, 256]
    app_icon(256).save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"Wrote {ico_path}")


if __name__ == "__main__":
    main()
