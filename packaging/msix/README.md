# MSIX packaging

Everything needed to turn the app into an `.msix` for the Microsoft Store or for
sideloading.

| File | Purpose |
| --- | --- |
| `AppxManifest.xml` | Package manifest template (identity/version filled in at build time) |
| `identity.json` | The Partner Center product identity this app publishes under |
| `build_msix.ps1` | Stages the payload, builds `resources.pri`, packs and optionally signs |
| `make_msix_assets.py` | Generates every tile/logo PNG into `Assets/` |
| `Assets/` | The generated images (committed, so a build needs no Pillow) |
| `Install-Sideload.ps1` | Trust the test certificate and install locally |
| `Uninstall-AnythingToMarkdown.ps1` | Scripted removal |

## Building locally (Windows)

Needs the **Windows 10/11 SDK** — `build_msix.ps1` looks for `makeappx.exe`,
`makepri.exe` and `signtool.exe` under `C:\Program Files (x86)\Windows Kits\10\bin`
and picks the newest version it finds.

```bat
:: 1. build the one-folder payload (not the single .exe — see below)
make msix-payload

:: 2. pack it, signing with a throwaway certificate so it can be installed
make msix-sideload

:: 3. install it (elevated PowerShell, to trust the test certificate)
powershell -ExecutionPolicy Bypass -File packaging\msix\Install-Sideload.ps1
```

For a Store upload, build it **unsigned** — Partner Center re-signs the package
with the Store certificate:

```bat
make msix
```

### Why a one-folder payload

The downloadable `.exe` is a PyInstaller one-file build, which unpacks itself to
a temp folder on every launch. Inside an MSIX that is pure overhead — the package
is already an extracted folder on disk — so the MSIX is built from
`BUILD_ONEDIR=1`, which starts faster and avoids Store certification warnings
about self-extracting executables.

## Product identity

`identity.json` holds the three values Partner Center requires the package to
match exactly:

```
Package/Identity/Name                     ORBApps.AnythingToMarkdown
Package/Identity/Publisher                CN=B120898B-B56C-415B-ACE0-6AD3877F041E
Package/Properties/PublisherDisplayName   ORB Apps
```

They are not secret — they ship inside every package — so they are committed
rather than injected from CI secrets. `build_msix.ps1` prefers an explicit
parameter, then `MSIX_IDENTITY_NAME` / `MSIX_PUBLISHER` /
`MSIX_PUBLISHER_DISPLAY_NAME`, then this file, so a fork can publish under its
own account without editing anything.

`check_manifest.py` validates the file (and runs in CI), because a wrong
identity is otherwise only discovered when Partner Center rejects the upload.

## Versioning

`anytomd/__init__.py` holds the one canonical version. Everything else derives
from it via `packaging/version_tool.py`:

```
anytomd.__version__  "1.2.3"
  ├── pyproject.toml                  1.2.3
  ├── macOS Info.plist                1.2.3
  ├── release filenames               AnythingToMarkdown-1.2.3-…
  └── MSIX Identity/Version           1.2.3.0
```

MSIX needs a four-part version and the Store reserves the fourth part, so Store
builds always use `.0`. CI puts its run number there for non-tagged test builds,
which is fine for sideloading and never submitted.

Tagging `v1.2.3` when `__version__` says something else fails the build on
purpose — CI runs `version_tool.py check --tag` before building anything.

```bash
python packaging/version_tool.py set 1.2.3   # bump everything at once
```

## What the package installs

**Start menu entry.** `AppListEntry="default"` in `uap:VisualElements` puts
*AnythingToMarkdown* in Start → All apps, where it can be pinned to Start or the
taskbar. `uap:DefaultTile` supplies the small/medium/wide/large tiles, drawn on
the brand colour declared as `BackgroundColor`.

**File Explorer integration.** `windows.fileTypeAssociation` registers the app
for the 14 document types it converts (`.pdf`, `.docx`, `.xlsx`, `.pptx`,
`.epub`, `.msg`, `.csv`, `.html`, `.json`, `.xml`, …), so they can be opened with
it from the right-click menu. Windows passes the path as `argv[1]`;
`packaging/app_entry.py` opens the GUI with the file queued rather than
converting silently, so the user still chooses where the Markdown goes.

**Command line.** `uap5:AppExecutionAlias` registers `anytomd.exe`, so
`anytomd report.pdf -o out\` works in PowerShell, Command Prompt and Windows
Terminal without anyone editing `PATH`.

> **Desktop shortcuts:** MSIX deliberately cannot drop an icon on the desktop —
> Windows reserves that for the user, who can drag the app there from the Start
> menu. The Start menu entry, taskbar pinning and "Open with" above are the
> supported equivalents.

## Uninstalling

An MSIX uninstalls cleanly with no extra machinery, which is the main practical
advantage over an `.exe` installer. Any of these work:

- **Start menu** → right-click *AnythingToMarkdown* → **Uninstall**
- **Settings** → **Apps** → **Installed apps** → **AnythingToMarkdown** → **Uninstall**
- **Microsoft Store** → **Library** → **AnythingToMarkdown** → **Uninstall**
- ```powershell
  powershell -File packaging\msix\Uninstall-AnythingToMarkdown.ps1
  ```

All of them remove the whole package: the executable, the bundled Python/Qt
runtime, the Start menu entry, the file type associations, the `anytomd` alias
and the app's private data folder. MSIX installs never write to `Program Files`
or the registry, so nothing is left behind. Markdown files the app produced are
your documents and are never touched.

Add `-RemoveTestCertificate` to the script to also drop the self-signed
certificate a sideloaded test install had to trust.

## Regenerating the assets

```bash
python packaging/msix/make_msix_assets.py
```

Writes the full scale/target-size matrix Windows expects (45 PNGs) from the
shared artwork in `packaging/brand.py`, the same routine behind the macOS and
Windows desktop icons.
