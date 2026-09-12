"""Single source of truth for the application version.

`anytomd/__init__.py` holds the canonical `__version__`; everything else
(pyproject, the macOS Info.plist, the MSIX manifest, release filenames) is
derived from it by this script so the numbers can never drift apart.

Usage
-----
    python packaging/version_tool.py get
        -> 1.0.0

    python packaging/version_tool.py msix --revision 0
        -> 1.0.0.0            (MSIX/Appx needs a four-part version)

    python packaging/version_tool.py check --tag v1.0.0
        -> exits non-zero if the git tag disagrees with __version__

    python packaging/version_tool.py set 1.1.0
        -> rewrites anytomd/__init__.py and pyproject.toml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT_PY = ROOT / "anytomd" / "__init__.py"
PYPROJECT = ROOT / "pyproject.toml"

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def read_version() -> str:
    """Read __version__ out of anytomd/__init__.py without importing it.

    Importing would pull in MarkItDown/Qt, which we cannot assume are
    installed on a machine that only wants to know the version number.
    """
    text = INIT_PY.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.M)
    if not match:
        raise SystemExit(f"Could not find __version__ in {INIT_PY}")
    return match.group(1)


def read_app_name() -> str:
    """Read __app_name__ out of anytomd/__init__.py, without importing it.

    The display name shown in the GUI, the Start menu, the MSIX tile and the
    Store art all come from here, so they cannot drift apart.
    """
    text = INIT_PY.read_text(encoding="utf-8")
    match = re.search(r'^__app_name__\s*=\s*["\']([^"\']+)["\']', text, re.M)
    if not match:
        raise SystemExit(f"Could not find __app_name__ in {INIT_PY}")
    return match.group(1)


def msix_version(version: str, revision: int = 0) -> str:
    """Turn a semver string into the four-part version MSIX requires.

    The Microsoft Store reserves the fourth part (revision) for itself: a
    package submitted with a non-zero revision is rejected, so Store builds
    must always use `.0`. Non-zero revisions are fine for sideloaded test
    builds, which is why CI passes the run number there.
    """
    match = SEMVER_RE.match(version)
    if not match:
        raise SystemExit(
            f"Version {version!r} is not MAJOR.MINOR.PATCH — MSIX needs a "
            "numeric three-part version to extend to four parts."
        )
    if not 0 <= revision <= 65535:
        raise SystemExit(f"Revision {revision} is outside the allowed 0-65535 range.")
    return f"{match.group(1)}.{match.group(2)}.{match.group(3)}.{revision}"


def check_tag(tag: str) -> None:
    """Fail loudly when a release tag does not match the source version."""
    wanted = tag[1:] if tag.startswith("v") else tag
    actual = read_version()
    if wanted != actual:
        raise SystemExit(
            f"Version mismatch: git tag is {tag!r} (=> {wanted}) but "
            f"anytomd.__version__ is {actual!r}.\n"
            f"Run `python packaging/version_tool.py set {wanted}` and commit "
            "before tagging."
        )
    print(f"OK: tag {tag} matches __version__ {actual}")


def set_version(version: str) -> None:
    if not SEMVER_RE.match(version):
        raise SystemExit(f"{version!r} is not a MAJOR.MINOR.PATCH version.")

    init_text = INIT_PY.read_text(encoding="utf-8")
    init_new = re.sub(
        r'^(__version__\s*=\s*)["\'][^"\']+["\']',
        lambda m: f'{m.group(1)}"{version}"',
        init_text,
        count=1,
        flags=re.M,
    )
    INIT_PY.write_text(init_new, encoding="utf-8")

    proj_text = PYPROJECT.read_text(encoding="utf-8")
    proj_new = re.sub(
        r'^(version\s*=\s*)["\'][^"\']+["\']',
        lambda m: f'{m.group(1)}"{version}"',
        proj_text,
        count=1,
        flags=re.M,
    )
    PYPROJECT.write_text(proj_new, encoding="utf-8")

    print(f"Set version to {version} in {INIT_PY.name} and {PYPROJECT.name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("get", help="Print the current version (1.2.3)")
    sub.add_parser("app-name", help="Print the display name (__app_name__)")

    p_msix = sub.add_parser("msix", help="Print the four-part MSIX version")
    p_msix.add_argument(
        "--revision", type=int, default=0,
        help="Fourth version part. Must be 0 for Microsoft Store submissions.",
    )

    p_check = sub.add_parser("check", help="Verify a git tag matches the source")
    p_check.add_argument("--tag", required=True, help="e.g. v1.0.0")

    p_set = sub.add_parser("set", help="Write a new version into the source files")
    p_set.add_argument("version", help="e.g. 1.1.0")

    args = parser.parse_args(argv)

    if args.command == "get":
        print(read_version())
    elif args.command == "app-name":
        print(read_app_name())
    elif args.command == "msix":
        print(msix_version(read_version(), args.revision))
    elif args.command == "check":
        check_tag(args.tag)
    elif args.command == "set":
        set_version(args.version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
