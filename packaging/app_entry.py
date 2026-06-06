"""Entry point for the bundled desktop app.

- Double-clicked with no files  -> opens the GUI.
- Files dropped onto the icon    -> converts them (argv_emulation passes paths).
"""

import sys

from anytomd.cli import main

if __name__ == "__main__":
    main()
