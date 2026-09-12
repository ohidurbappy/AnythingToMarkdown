"""Entry point for the bundled desktop app (PyInstaller / MSIX / .app).

The bundled binary is windowed — there is no console attached — so the plain
CLI behaviour of "convert and print progress to stderr" would be invisible
when Windows or Finder launches us with a file path. The rule here:

  * no arguments                     -> open the GUI (double-click)
  * only file/folder paths           -> open the GUI with those queued
                                        (Explorer "Open with", MSIX file type
                                        association, drop onto the app icon)
  * any option flag (-o, -r, --gui…) -> hand over to the normal CLI, which is
                                        what someone typing `anytomd ...` in a
                                        terminal intends

The pip-installed `anytomd` command is unaffected: it keeps using
anytomd.cli:main directly.
"""

import sys
from pathlib import Path

from anytomd.cli import main as cli_main


def _looks_like_option(arg: str) -> bool:
    """True for '-o' / '--gui' style flags, but not for a path like '-file'."""
    return arg.startswith("-") and arg != "-"


def main() -> None:
    args = sys.argv[1:]

    # Explicit CLI usage (or --gui): let argparse handle everything.
    if any(_looks_like_option(a) for a in args):
        cli_main()
        return

    from anytomd.gui import launch_gui

    paths = [Path(a) for a in args]
    existing = [p for p in paths if p.exists()]
    sys.exit(launch_gui(initial_files=existing or None))


if __name__ == "__main__":
    main()
