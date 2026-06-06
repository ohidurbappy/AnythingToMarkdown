# AnythingToMarkdown

A lightweight, cross-platform tool to convert **PDFs, Word/Excel/PowerPoint, HTML, images, audio, and more** into clean Markdown. It has both a friendly **drag-and-drop GUI** and a scriptable **CLI**, and uses Microsoft's [MarkItDown](https://github.com/microsoft/markitdown) engine under the hood.

- 🖱️ **GUI** — drag & drop files/folders, batch convert, pick an output folder.
- ⌨️ **CLI** — convert single files, globs, or whole directories; pipe to stdout.
- 🪶 **Lightweight** — one language (Python + PySide6), no heavyweight framework.
- 💻 **Cross-platform** — Windows, macOS, and Linux.

---

## Quick start

The launcher scripts create the virtual environment and install dependencies automatically on first run.

### macOS / Linux
```bash
./run.sh              # open the GUI
./run.sh report.pdf   # convert a file from the CLI
./run.sh --help       # see all CLI options
```

### Windows
```bat
run.bat               :: open the GUI
run.bat report.pdf    :: convert a file from the CLI
run.bat --help        :: see all CLI options
```

---

## macOS — clickable app

A standalone, double-clickable `AnythingToMarkdown.app` can be built (no Python or terminal required to run it):

```bash
./run.sh                              # one-time: creates the venv
packaging/build_macos.sh              # builds dist/AnythingToMarkdown.app
open dist/AnythingToMarkdown.app      # or just double-click it in Finder
```

The app is self-contained (bundles Python, Qt, and MarkItDown). To install it, drag `AnythingToMarkdown.app` into your `/Applications` folder. You can also drop documents onto its icon to convert them.

### Distributable .dmg

To produce a single shareable installer with a drag-to-Applications layout:

```bash
make dmg                              # builds dist/AnythingToMarkdown-<version>.dmg
```

(or run `packaging/build_dmg.sh` directly — it builds the app first if needed). Hand the `.dmg` to anyone: they double-click it and drag the app onto the **Applications** shortcut. No Python required.

> First launch: because the app isn't notarized, macOS Gatekeeper may block it. Right-click the app → **Open** → **Open**, or run `xattr -dr com.apple.quarantine dist/AnythingToMarkdown.app`.

### Notarized distribution (optional)

To distribute without any Gatekeeper warning, sign and notarize with an Apple Developer ID ($99/yr). Once you have a *Developer ID Application* certificate installed:

```bash
# one-time: store notary credentials in the keychain
xcrun notarytool store-credentials "MyProfile" \
    --apple-id you@example.com --team-id TEAMID1234 --password <app-specific-password>

# sign → build dmg → notarize → staple
SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID1234)" \
NOTARY_PROFILE="MyProfile" \
    make notarize
```

This rebuilds the app with the hardened runtime ([packaging/entitlements.plist](packaging/entitlements.plist)), packages and signs the `.dmg`, submits it to Apple, and staples the ticket — producing a `.dmg` that installs cleanly on any Mac. Without these env vars, normal `make app` / `make dmg` builds stay unsigned (fine for personal use). See [packaging/notarize.sh](packaging/notarize.sh) for the full list of options.

---

## Windows — clickable app

A standalone, **single-file** `.exe` can be built (no Python required to run it):

```bat
make app                 :: builds dist\AnythingToMarkdown.exe (one file)
make open-app            :: reveals it in Explorer
```

(or run `packaging\build_windows.bat` directly). The result is a single self-contained executable — just hand someone **`AnythingToMarkdown.exe`** and they double-click it to launch the GUI. Run it from a terminal with arguments (e.g. `AnythingToMarkdown.exe report.pdf -o out`) to use the CLI.

> A single-file `.exe` unpacks to a temp folder on launch, so the **first** start is a few seconds slower than the macOS app — that's normal for onefile builds.

> Windows SmartScreen may warn about an unrecognized app on first launch (it isn't code-signed). Click **More info → Run anyway**.

---

## Automated builds & releases (GitHub Actions)

The repo ships a CI workflow ([.github/workflows/build.yml](.github/workflows/build.yml)) that builds both platforms and publishes them to a GitHub Release:

- **macOS** → `AnythingToMarkdown-<version>.dmg`
- **Windows** → `AnythingToMarkdown-<version>-windows-x64.exe` (single file)

**To cut a release**, push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds on `macos-latest` and `windows-latest`, then attaches both files to a release named after the tag (with auto-generated notes). You can also trigger it manually from the **Actions** tab (without releasing) to test a build.

> The CI-built artifacts are **unsigned**. For signed/notarized macOS builds, run `make notarize` locally with your Developer ID (see below), or add your signing secrets to the workflow.

---

## Make targets

Common tasks are wrapped up for you. On **macOS/Linux** use `make` (run `make help` to list targets); on **Windows** use the bundled `make.bat` (no GNU Make needed) — the targets are identical.

```bash
# macOS / Linux
make                                 # show all targets
make run                             # set up the venv (if needed) and launch the GUI
make cli ARGS="report.pdf -o out/"   # run the CLI
make app                             # build the clickable macOS .app
make open-app                        # open the built app
make clean                           # remove build/dist artifacts
make clean-all                       # also remove the virtual environment
```

```bat
:: Windows
make                                 :: show all targets
make run                             :: set up the venv (if needed) and launch the GUI
make cli report.pdf -o out           :: run the CLI (args passed directly)
make app                             :: build the clickable Windows app (dist\AnythingToMarkdown)
make open-app                        :: open the built app folder
make clean                           :: remove build/dist artifacts
make clean-all                       :: also remove the virtual environment
```

---

## Manual setup (any platform)

```bash
# 1. Create & activate a virtual environment (Python 3.10+)
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install
pip install -r requirements.txt
pip install -e .                 # optional: enables the `anytomd` command

# 3. Run
anytomd                          # GUI  (or: python -m anytomd)
anytomd file.pdf                 # CLI
```

---

## CLI usage

```
anytomd [inputs...] [options]
```

| Option | Description |
| --- | --- |
| `inputs` | One or more files and/or folders to convert. |
| `-o, --output-dir DIR` | Write `.md` files into `DIR` (default: alongside each input). |
| `-r, --recursive` | Recurse into subfolders when an input is a directory. |
| `--stdout` | Print Markdown to stdout instead of writing a file (single input only). |
| `--no-overwrite` | Don't overwrite existing `.md`; write a numbered copy instead. |
| `--plugins` | Enable third-party MarkItDown plugins. |
| `-q, --quiet` | Suppress per-file progress output. |
| `--gui` | Launch the GUI. |
| `-V, --version` | Print version. |

### Examples
```bash
anytomd report.pdf                 # writes report.md next to it
anytomd *.docx -o out/             # batch convert into ./out
anytomd notes.pdf --stdout         # print Markdown to the terminal
anytomd ./docs -r -o markdown/     # recurse a folder into ./markdown
anytomd a.pdf b.pptx c.xlsx        # multiple files at once
```

Running with no arguments (from a terminal or by double-clicking) opens the GUI.

---

## Supported formats

PDF · Word (`.docx`/`.doc`) · PowerPoint (`.pptx`/`.ppt`) · Excel (`.xlsx`/`.xls`) · HTML · CSV · JSON · XML · EPub · Outlook `.msg` · images (`.jpg`, `.png`, …, with OCR/metadata) · audio (`.mp3`, `.wav`, …, with transcription) · ZIP archives · plain text.

> **Note:** Audio transcription requires `ffmpeg` to be installed and on your `PATH`. Everything else works out of the box.

---

## Project layout

```
AnythingToMarkdown/
├── anytomd/
│   ├── __init__.py      # package metadata + public API
│   ├── __main__.py      # `python -m anytomd` entry point
│   ├── converter.py     # core MarkItDown wrapper (GUI/CLI agnostic)
│   ├── cli.py           # argparse command-line interface
│   └── gui.py           # PySide6 graphical interface
├── pyproject.toml       # packaging + console/gui entry points
├── requirements.txt
├── run.sh               # macOS/Linux launcher (auto-sets up venv)
└── run.bat              # Windows launcher (auto-sets up venv)
```

---

## License

MIT. Powered by [MarkItDown](https://github.com/microsoft/markitdown) and [PySide6](https://doc.qt.io/qtforpython/).
