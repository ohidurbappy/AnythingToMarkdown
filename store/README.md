# Microsoft Store listing

Everything Partner Center asks for, prepared and checked in.

```
store/
├── SUBMISSION.md              step-by-step submission checklist  ← start here
├── PRIVACY.md                 privacy policy (needs a public URL)
├── listing/en-us/             every text field, one file per field
├── assets/                    Store logos and promotional art
│   └── screenshots/           real captures of the app running
├── make_store_assets.py       regenerates the branding images
├── make_screenshots.py        re-captures the screenshots from the live app
└── validate_listing.py        checks everything against Partner Center's limits
```

## Before submitting

```bash
python store/validate_listing.py
```

Confirms no text field is over its character limit, every image is exactly the
size Partner Center expects, and every screenshot has a caption.

## Regenerating

```bash
python store/make_store_assets.py    # logos and promotional art
python store/make_screenshots.py     # screenshots, by driving the real app
```

`make_screenshots.py` is not a mock-up: it creates genuine sample documents
(PDF, XLSX, PPTX, HTML, CSV), opens the real PySide6 window, runs a real
MarkItDown conversion and captures each stage at 1366x768. Re-run it after any
UI change — and preferably on Windows, for the most faithful shots.

The branding images share `packaging/brand.py` with the desktop icons and the
MSIX tiles, so the mark is identical everywhere.
