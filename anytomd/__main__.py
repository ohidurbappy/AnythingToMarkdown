"""Entry point so `python -m anytomd` works for both CLI and GUI.

With arguments it behaves as a CLI; with none (from a terminal) it opens the GUI.
"""

from .cli import main

if __name__ == "__main__":
    main()
