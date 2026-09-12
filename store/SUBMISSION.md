# Submitting AnythingToMarkdown to the Microsoft Store

Everything the submission needs is generated from this repository. Work through
the checklist once; after that, releasing a new version is just pushing a tag.

---

## 1. Reserve the name (one time)

1. Sign in to [Partner Center](https://partner.microsoft.com/dashboard) with a
   registered developer account.
2. **Apps and games → New product → MSIX or PWA app**.
3. Reserve the name **AnythingToMarkdown**.

## 2. Product identity — already configured ✅

Partner Center shows three values under **Product management → Product identity**
that the package must match *exactly*, or the upload is rejected. They are
committed in [`packaging/msix/identity.json`](../packaging/msix/identity.json):

| Partner Center field | Value |
| --- | --- |
| Package/Identity/Name | `ORBApps.AnythingToMarkdown` |
| Package/Identity/Publisher | `CN=B120898B-B56C-415B-ACE0-6AD3877F041E` |
| Package/Properties/PublisherDisplayName | `ORB Apps` |

Nothing to set up — every build already produces a submittable package. These
values are not secret; they ship inside the package itself.

If they ever change in Partner Center, edit `identity.json` and re-run:

```bash
python packaging/msix/check_manifest.py
```

A fork publishing under a different Partner Center account can override them
without touching the file, via `MSIX_IDENTITY_NAME`, `MSIX_PUBLISHER` and
`MSIX_PUBLISHER_DISPLAY_NAME` (environment variables, or GitHub repository
variables under **Settings → Secrets and variables → Actions → Variables**).

## 3. Host the privacy policy (one time)

Partner Center requires a public privacy policy URL. [`store/PRIVACY.md`](PRIVACY.md)
is ready to publish — enable GitHub Pages, or use the raw file URL:

```
https://github.com/ohidurbappy/AnythingToMarkdown/blob/main/store/PRIVACY.md
```

## 4. Build the package

Push a version tag. CI builds and attaches the `.msix` to the GitHub release:

```bash
python packaging/version_tool.py set 1.0.0   # keeps every version string in sync
git commit -am "Release 1.0.0"
git tag v1.0.0
git push origin main --tags
```

Download `AnythingToMarkdown-<version>-x64.msix` from the release. It is
deliberately **unsigned** — Partner Center signs Store packages itself.

## 5. Fill in the submission

### Pricing and availability
| Field | Value |
| --- | --- |
| Markets | All markets |
| Price | Free |
| Visibility | Public |
| Free trial | No free trial |

### Properties
| Field | Value |
| --- | --- |
| Category | Productivity *(alternative: Developer tools)* |
| Privacy policy URL | the URL from step 3 |
| Website | `https://github.com/ohidurbappy/AnythingToMarkdown` |
| Support contact info | `anythingtomd@ohidur.com` |
| Publisher display name | `ORB Apps` (set on the account, shown on the listing) |
| System requirements | see [`listing/en-us/system-requirements.txt`](listing/en-us/system-requirements.txt) |

**Product declarations** — the honest answers for this app:

- Does not contain ads
- Does not access, collect or transmit personal information
- Customers can install to any location, including removable storage: **yes**
- Not a system utility or driver, no restricted capabilities
- Works offline: **yes**

### Age ratings
Complete the IARC questionnaire. A document converter with no user-generated
content, no ads, no in-app purchases, no data collection and no communication
features rates **3+ / Everyone** in every region.

### Packages
Upload the `.msix` from step 4. Architecture is x64, minimum Windows 10 1809
(build 17763) — this comes from the manifest, nothing to type.

### Store listing (en-us)
Every field is prepared in [`listing/en-us/`](listing/en-us/):

| Partner Center field | File |
| --- | --- |
| Description | `description.txt` |
| Short description | `short-description.txt` |
| Product features | `product-features.txt` (one per line) |
| Search terms | `search-terms.txt` (one per line) |
| What's new in this version | `release-notes.txt` |
| Copyright and trademark info | `copyright-and-trademark.txt` |
| Additional licence terms | `additional-license-terms.txt` |

**Screenshots** — upload from [`assets/screenshots/`](assets/screenshots/) and
paste the captions from `screenshot-captions.txt`. These are real captures of
the app converting real documents, produced by `store/make_screenshots.py`.

**Store logos** — upload from [`assets/`](assets/):

| Partner Center slot | File |
| --- | --- |
| 2:3 Poster art | `PosterArt-720x1080.png` |
| 1:1 Box art | `BoxArt-1080x1080.png` |
| 16:9 Super hero art | `SuperHeroArt-2400x1200.png` |
| 16:9 Hero art | `HeroArt-1920x1080.png` |
| Promotional 414x180 | `Promotional-414x180.png` |
| 300x300 logo | `StoreLogo-300x300.png` |

Before pasting anything, confirm nothing exceeds a Partner Center limit:

```bash
python store/validate_listing.py
```

### Notes for certification
Worth pasting into **Notes for certification** so the reviewer isn't guessing:

> AnythingToMarkdown is an offline document converter. No sign-in or account is
> required and the app has no network functionality — testing needs no
> credentials. To exercise it: launch the app, drag any PDF, .docx, .xlsx,
> .pptx, .html or .csv file onto the window, and press "Convert to Markdown". A
> .md file is written next to the source file. The bundled `anytomd` command is
> also available from Windows Terminal.
>
> Audio transcription and image metadata require FFmpeg and ExifTool
> respectively, which users install separately; all other formats work with no
> additional software.

## 6. Submit

Review and publish. First submissions typically clear certification within a few
business days.

---

## Releasing an update

1. `python packaging/version_tool.py set 1.1.0`
2. Update `store/listing/en-us/release-notes.txt`
3. Commit, tag `v1.1.0`, push
4. In Partner Center: **Update** → upload the new `.msix` → paste the new
   release notes → submit

The Store compares four-part versions, so the new package must have a higher
version than the published one. `version_tool.py` handles that as long as you
bump the semver.
