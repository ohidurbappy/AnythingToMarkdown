# AnythingToMarkdown

A lightweight, cross-platform tool to convert **PDFs, Word/Excel/PowerPoint, HTML, images, audio, and more** into clean Markdown. It has both a friendly **drag-and-drop GUI** and a scriptable **CLI**, and uses Microsoft's [MarkItDown](https://github.com/microsoft/markitdown) engine under the hood.

- 🖱️ **GUI** — drag & drop files/folders, batch convert, pick an output folder.
- ⌨️ **CLI** — convert single files, globs, or whole directories; pipe to stdout.
- 🪶 **Lightweight** — one language (Python + PySide6), no heavyweight framework.
- 💻 **Cross-platform** — Windows, macOS, and Linux.
- 📦 **Installable** — macOS `.dmg`, a standalone Windows `.exe`, and an `.msix` for the Microsoft Store.

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

## Windows — Microsoft Store package (.msix)

The same app also builds as an **MSIX**, which is what the Microsoft Store distributes. Compared with the standalone `.exe` it adds a Start menu entry, File Explorer integration, a `PATH`-free command line, and a one-click uninstall — and it starts faster, because an MSIX is already unpacked on disk.

```bat
make msix              :: unsigned .msix, ready to upload to Partner Center
make msix-sideload     :: self-signed .msix you can install locally to test
make msix-install      :: install it (elevated prompt, to trust the test cert)
make msix-uninstall    :: remove it again
```

Building the package needs the **Windows 10/11 SDK** (for `makeappx`, `makepri` and `signtool`). CI builds it for you on every tag.

### What installing it gives you

| | |
| --- | --- |
| **Start menu entry** | *AnythingToMarkdown* appears in Start → All apps, and can be pinned to Start or the taskbar. |
| **Open with** | Right-click a PDF, Word, Excel, PowerPoint, EPUB, `.msg`, CSV, HTML, JSON or XML file → **Open with** → *AnythingToMarkdown*. The file arrives queued in the GUI, so you still choose where the Markdown goes. |
| **`anytomd` command** | Works immediately in PowerShell, Command Prompt and Windows Terminal — no `PATH` editing. |
| **Clean uninstall** | Start menu right-click → **Uninstall**, or Settings → Apps → Installed apps. Removes the app, its bundled runtime, the Start menu entry, the file associations and the command alias. Nothing is written to `Program Files` or the registry, and your converted `.md` files are never touched. |

> MSIX intentionally cannot create desktop shortcuts — Windows reserves the desktop for the user, who can drag the app there from the Start menu.

Full details: [packaging/msix/README.md](packaging/msix/README.md).

---

## Publishing to the Microsoft Store

Everything Partner Center asks for is prepared in [store/](store/) — listing text, logos, promotional art and real screenshots of the app running, all validated against Partner Center's limits.

**Start here: [store/SUBMISSION.md](store/SUBMISSION.md)** — a step-by-step checklist covering name reservation, product identity, categories, age rating and which file goes in which field.

```bash
make store         # regenerate every Store asset, then validate it
make store-check   # just validate
```

The Partner Center product identity is already configured in [packaging/msix/identity.json](packaging/msix/identity.json), so pushing a tag produces a **submittable** `.msix` — no repository variables or secrets needed. The one remaining manual step is hosting [store/PRIVACY.md](store/PRIVACY.md) at a public URL, which Partner Center requires.

> Publishing a fork under a different Partner Center account? Override with the `MSIX_IDENTITY_NAME`, `MSIX_PUBLISHER` and `MSIX_PUBLISHER_DISPLAY_NAME` environment/repository variables instead of editing the file.

---

## Versioning

`anytomd/__init__.py` holds the one canonical version; everything else is derived from it:

```
anytomd.__version__  "1.2.3"
  ├── pyproject.toml                  1.2.3
  ├── macOS Info.plist                1.2.3
  ├── release filenames               AnythingToMarkdown-1.2.3-…
  └── MSIX Identity/Version           1.2.3.0   (MSIX needs four parts;
                                                 the Store reserves the last)
```

Bump it in one step, so the numbers can't drift apart:

```bash
make set-version VERSION=1.2.3     # or: python packaging/version_tool.py set 1.2.3
```

Tagging `v1.2.3` while `__version__` says something else **fails CI on purpose**, before anything is built.

---

## Automated builds & releases (GitHub Actions)

The repo ships a CI workflow ([.github/workflows/build.yml](.github/workflows/build.yml)) that builds every platform and publishes them to a GitHub Release:

- **macOS** → `AnythingToMarkdown-<version>.dmg`
- **Windows** → `AnythingToMarkdown-<version>-windows-x64.exe` (single file)
- **Windows / Microsoft Store** → `AnythingToMarkdown-<version>.0-x64.msix`

A `version` job runs first: it checks the tag against `anytomd.__version__`, validates the Store listing, and hands one agreed set of version numbers to every build job — so the `.dmg`, the `.exe` and the `.msix` can never disagree about what they are.

**To cut a release**, push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds on `macos-latest` and `windows-latest`, then attaches both files to a release named after the tag (with auto-generated notes). You can also trigger it manually from the **Actions** tab (without releasing) to test a build.

> The CI-built `.dmg` and `.exe` are **unsigned**. For signed/notarized macOS builds, run `make notarize` locally with your Developer ID (see above), or add your signing secrets to the workflow. The `.msix` is unsigned *by design* — Partner Center signs Store packages itself.

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
make store                           # regenerate + validate every Store asset
make set-version VERSION=1.2.3       # bump the version everywhere
make clean                           # remove build/dist artifacts
make clean-all                       # also remove the virtual environment
```

```bat
:: Windows
make                                 :: show all targets
make run                             :: set up the venv (if needed) and launch the GUI
make cli report.pdf -o out           :: run the CLI (args passed directly)
make app                             :: build the single-file Windows app (dist\AnythingToMarkdown.exe)
make open-app                        :: reveal the built executable in Explorer
make msix                            :: build the unsigned .msix for the Store
make msix-sideload                   :: build a self-signed .msix to test locally
make msix-install                    :: install it (elevated prompt)
make msix-uninstall                  :: remove it again
make store-check                     :: validate the Store listing
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

PDF · Word (`.docx`/`.doc`) · PowerPoint (`.pptx`/`.ppt`) · Excel (`.xlsx`/`.xls`) · HTML · CSV · JSON · XML · EPub · Outlook `.msg` · images (`.jpg`, `.png`, …, embedded metadata) · audio (`.mp3`, `.wav`, …, transcription) · ZIP archives · plain text.

> **Note:** Two formats need an external tool on your `PATH`: audio transcription requires [`ffmpeg`](https://ffmpeg.org/), and image metadata requires [`exiftool`](https://exiftool.org/). Images produce their embedded metadata rather than OCR'd text. Everything else works out of the box.

---

## Project layout

```
AnythingToMarkdown/
├── anytomd/
│   ├── __init__.py      # package metadata + public API (canonical version)
│   ├── __main__.py      # `python -m anytomd` entry point
│   ├── converter.py     # core MarkItDown wrapper (GUI/CLI agnostic)
│   ├── cli.py           # argparse command-line interface
│   └── gui.py           # PySide6 graphical interface
├── packaging/
│   ├── brand.py         # the app mark — shared by every icon, tile and logo
│   ├── version_tool.py  # derives every version string from __version__
│   ├── make_icon.py     # macOS .icns + Windows .ico
│   ├── app_entry.py     # bundled-app entry point (file associations → GUI)
│   ├── AnythingToMarkdown.spec   # PyInstaller: .app / one-file / one-folder
│   └── msix/            # MSIX manifest, tile assets, build & uninstall scripts
├── store/               # Microsoft Store listing text, art and screenshots
├── pyproject.toml       # packaging + console/gui entry points
├── requirements.txt
├── run.sh               # macOS/Linux launcher (auto-sets up venv)
└── run.bat              # Windows launcher (auto-sets up venv)
```

---

## License

MIT. Powered by [MarkItDown](https://github.com/microsoft/markitdown) and [PySide6](https://doc.qt.io/qtforpython/).
