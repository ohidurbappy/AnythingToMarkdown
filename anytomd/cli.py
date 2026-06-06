"""Command-line interface for AnythingToMarkdown."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __app_name__, __version__
from .converter import Converter, expand_inputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anytomd",
        description=(
            "Convert PDFs, Office documents, HTML, images and more to Markdown "
            "using Microsoft's MarkItDown engine."
        ),
        epilog=(
            "Examples:\n"
            "  anytomd report.pdf                 # writes report.md next to it\n"
            "  anytomd *.docx -o out/             # convert many into out/\n"
            "  anytomd notes.pdf --stdout         # print markdown to stdout\n"
            "  anytomd ./docs -r -o markdown/     # recurse a folder\n"
            "  anytomd --gui                      # launch the GUI\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Files and/or directories to convert.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        metavar="DIR",
        help="Directory to write .md files into (default: alongside each input).",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recurse into subdirectories when an input is a folder.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print Markdown to stdout instead of writing files "
             "(only valid with a single input file).",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Do not overwrite existing .md files; write a numbered copy instead.",
    )
    parser.add_argument(
        "--plugins",
        action="store_true",
        help="Enable third-party MarkItDown plugins.",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress per-file progress output.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the graphical interface instead of running on the CLI.",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"{__app_name__} {__version__}",
    )
    return parser


def _eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def run_cli(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Launch the GUI either explicitly (--gui) or when invoked with no inputs
    # (double-clicking the app / bare `anytomd`). Use --help for CLI usage.
    if args.gui or not args.inputs:
        from .gui import launch_gui
        return launch_gui()

    files = expand_inputs(args.inputs, recursive=args.recursive)
    if not files:
        _eprint("No convertible files found in the given inputs.")
        return 1

    if args.stdout and len(files) != 1:
        _eprint("--stdout requires exactly one input file "
                f"(got {len(files)}).")
        return 2

    try:
        converter = Converter(enable_plugins=args.plugins)
    except Exception as exc:
        _eprint(f"Failed to start converter: {exc}")
        return 3

    # --stdout: single file, print and exit.
    if args.stdout:
        res = converter.convert_file(files[0])
        if not res.success:
            _eprint(f"Error converting {files[0]}: {res.error}")
            return 1
        sys.stdout.write(res.markdown)
        if res.markdown and not res.markdown.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    # Otherwise: write files (alongside input, or into --output-dir).
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else None

    def report(i: int, total: int, res) -> None:
        if args.quiet:
            return
        if res.success:
            _eprint(f"[{i}/{total}] OK   {res.source.name} -> {res.output_path}")
        else:
            _eprint(f"[{i}/{total}] FAIL {res.source.name}: {res.error}")

    # When no output dir is set, default to writing alongside each input.
    if output_dir is None:
        summary_results = []
        total = len(files)
        for i, f in enumerate(files, start=1):
            res = converter.convert_file(
                f,
                output_path=f.with_suffix(".md"),
                overwrite=not args.no_overwrite,
            )
            summary_results.append(res)
            report(i, total, res)
        failed = [r for r in summary_results if not r.success]
        succeeded = [r for r in summary_results if r.success]
    else:
        summary = converter.convert_many(
            files,
            output_dir=output_dir,
            overwrite=not args.no_overwrite,
            progress=report,
        )
        failed = summary.failed
        succeeded = summary.succeeded

    if not args.quiet:
        _eprint(f"\nDone: {len(succeeded)} succeeded, {len(failed)} failed.")

    return 0 if not failed else 1


def main() -> None:
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
