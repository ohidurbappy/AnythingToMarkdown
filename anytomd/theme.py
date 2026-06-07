"""Visual theme for the GUI — a clean, modern light/dark palette + stylesheet.

Kept separate from ``gui.py`` so the look can be tweaked in one place. The
palette is chosen at runtime based on the OS colour scheme.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    window: str        # app background
    surface: str       # cards / panels
    surface_alt: str   # subtle alternate (list rows, console)
    border: str        # hairline borders
    text: str          # primary text
    muted: str         # secondary text
    accent: str        # primary action
    accent_hover: str
    accent_press: str
    on_accent: str     # text on accent
    success: str
    danger: str
    drop_bg: str       # drop-zone fill when active


LIGHT = Palette(
    name="light",
    window="#f4f5f7",
    surface="#ffffff",
    surface_alt="#f7f8fa",
    border="#e3e6ea",
    text="#1b2330",
    muted="#6b7280",
    accent="#2563eb",
    accent_hover="#1d4ed8",
    accent_press="#1e40af",
    on_accent="#ffffff",
    success="#16a34a",
    danger="#dc2626",
    drop_bg="#eef4ff",
)

DARK = Palette(
    name="dark",
    window="#1c1d21",
    surface="#26282d",
    surface_alt="#2d2f35",
    border="#3a3d44",
    text="#e7e9ee",
    muted="#9aa1ac",
    accent="#3b82f6",
    accent_hover="#60a5fa",
    accent_press="#2563eb",
    on_accent="#ffffff",
    success="#22c55e",
    danger="#f87171",
    drop_bg="#23314d",
)


def stylesheet(p: Palette, check_url: str = "") -> str:
    """Return a Qt stylesheet (QSS) string for the given palette.

    ``check_url`` is an optional path/URL to a checkmark image used for the
    checked state of checkboxes (generated at runtime by the GUI).
    """
    check_rule = f"image: url({check_url});" if check_url else "image: none;"
    return f"""
    QWidget {{
        color: {p.text};
        font-size: 13px;
    }}
    QMainWindow, #Root {{
        background: {p.window};
    }}

    /* Header */
    #AppTitle {{
        font-size: 20px;
        font-weight: 700;
        color: {p.text};
    }}
    #AppSubtitle {{
        font-size: 12px;
        color: {p.muted};
    }}

    /* Cards */
    #Card {{
        background: {p.surface};
        border: 1px solid {p.border};
        border-radius: 12px;
    }}
    #SectionLabel {{
        font-size: 11px;
        font-weight: 600;
        color: {p.muted};
        letter-spacing: 0.6px;
    }}

    /* Drop zone / file table */
    #FileTable {{
        background: {p.surface};
        border: 2px dashed {p.border};
        border-radius: 12px;
        padding: 4px;
        outline: 0;
        gridline-color: transparent;
        alternate-background-color: {p.surface_alt};
        selection-background-color: {p.accent};
        selection-color: {p.on_accent};
    }}
    #FileTable[dragActive="true"] {{
        border: 2px dashed {p.accent};
        background: {p.drop_bg};
    }}
    #FileTable::item {{
        padding: 6px 10px;
        border: none;
        color: {p.text};
    }}
    #FileTable::item:selected {{
        background: {p.accent};
        color: {p.on_accent};
    }}
    QHeaderView::section {{
        background: {p.surface_alt};
        color: {p.muted};
        border: none;
        border-bottom: 1px solid {p.border};
        padding: 8px 10px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.4px;
    }}
    QTableCornerButton::section {{
        background: {p.surface_alt};
        border: none;
    }}
    #DropHint {{
        color: {p.muted};
        font-size: 13px;
    }}
    #DropHintBig {{
        color: {p.text};
        font-size: 15px;
        font-weight: 600;
    }}

    /* Buttons — secondary (outline) by default */
    QPushButton {{
        background: {p.surface};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 7px 14px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background: {p.surface_alt};
        border-color: {p.accent};
    }}
    QPushButton:pressed {{
        background: {p.border};
    }}
    QPushButton:disabled {{
        color: {p.muted};
        background: {p.surface};
        border-color: {p.border};
    }}

    /* Primary action */
    QPushButton#Primary {{
        background: {p.accent};
        color: {p.on_accent};
        border: 1px solid {p.accent};
        padding: 9px 20px;
        font-weight: 600;
    }}
    QPushButton#Primary:hover {{
        background: {p.accent_hover};
        border-color: {p.accent_hover};
    }}
    QPushButton#Primary:pressed {{
        background: {p.accent_press};
        border-color: {p.accent_press};
    }}
    QPushButton#Primary:disabled {{
        background: {p.border};
        color: {p.muted};
        border-color: {p.border};
    }}

    /* Danger / cancel */
    QPushButton#Danger {{
        background: transparent;
        color: {p.danger};
        border: 1px solid {p.danger};
        padding: 9px 18px;
        font-weight: 600;
    }}
    QPushButton#Danger:hover {{
        background: {p.danger};
        color: {p.on_accent};
    }}

    /* Checkboxes */
    QCheckBox {{
        spacing: 8px;
        color: {p.text};
    }}
    QCheckBox::indicator {{
        width: 18px; height: 18px;
        border: 1px solid {p.border};
        border-radius: 5px;
        background: {p.surface};
    }}
    QCheckBox::indicator:hover {{
        border-color: {p.accent};
    }}
    QCheckBox::indicator:checked {{
        background: {p.accent};
        border-color: {p.accent};
        {check_rule}
    }}

    /* Output path field */
    #OutPath {{
        color: {p.text};
        background: {p.surface_alt};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 7px 11px;
    }}

    /* Progress bar */
    QProgressBar {{
        background: {p.surface_alt};
        border: 1px solid {p.border};
        border-radius: 8px;
        height: 18px;
        text-align: center;
        color: {p.muted};
        font-size: 11px;
    }}
    QProgressBar::chunk {{
        background: {p.accent};
        border-radius: 7px;
        margin: 1px;
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border};
        border-radius: 5px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p.muted};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* Menu + status bar */
    QMenuBar, QStatusBar {{
        background: {p.window};
        color: {p.muted};
    }}
    QMenuBar::item:selected {{
        background: {p.surface_alt};
        color: {p.text};
    }}
    QMenu {{
        background: {p.surface};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 22px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background: {p.accent};
        color: {p.on_accent};
    }}
    QToolTip {{
        background: {p.text};
        color: {p.window};
        border: none;
        padding: 5px 8px;
        border-radius: 6px;
    }}
    """
