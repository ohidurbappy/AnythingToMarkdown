"""Core conversion logic — a thin, friendly wrapper around MarkItDown.

This module is GUI/CLI agnostic so it can be reused by both front-ends and
tested in isolation. It deliberately avoids importing any Qt code.
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence

# File extensions MarkItDown can handle (with the [all] extra installed).
# Used for file-dialog filters and quick validation — not an exhaustive gate,
# MarkItDown sniffs content too, so unknown extensions are still attempted.
SUPPORTED_EXTENSIONS: tuple[str, ...] = (
    # Documents
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
    # Web / markup / data
    ".html", ".htm", ".csv", ".json", ".xml", ".epub",
    # Plain text
    ".txt", ".md", ".rst",
    # Email
    ".msg",
    # Images (OCR / metadata)
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
    # Audio (transcription / metadata)
    ".mp3", ".wav", ".m4a", ".flac",
    # Archives
    ".zip",
)


class ConversionError(Exception):
    """Raised when a single file fails to convert."""

    def __init__(self, source: Path, message: str):
        self.source = source
        self.message = message
        super().__init__(f"{source}: {message}")


@dataclass
class ConversionResult:
    """Outcome of converting one input file."""

    source: Path
    success: bool
    output_path: Optional[Path] = None
    markdown: str = ""
    error: str = ""
    title: Optional[str] = None


@dataclass
class BatchSummary:
    """Aggregate outcome of a batch conversion."""

    results: List[ConversionResult] = field(default_factory=list)

    @property
    def succeeded(self) -> List[ConversionResult]:
        return [r for r in self.results if r.success]

    @property
    def failed(self) -> List[ConversionResult]:
        return [r for r in self.results if not r.success]

    @property
    def total(self) -> int:
        return len(self.results)


# Progress callback signature: (index, total, current_result_or_None)
ProgressCallback = Callable[[int, int, Optional[ConversionResult]], None]


class Converter:
    """Wraps a MarkItDown instance and adds batch + file-output helpers."""

    def __init__(self, enable_plugins: bool = False):
        # Imported lazily so importing this module (e.g. for --help) doesn't
        # pull in MarkItDown's heavy dependency tree until it's actually needed.
        try:
            # pydub (pulled in for audio) warns about missing ffmpeg on import.
            # That's irrelevant unless the user converts audio, so keep it quiet.
            warnings.filterwarnings(
                "ignore", message="Couldn't find ffmpeg", category=RuntimeWarning
            )
            from markitdown import MarkItDown
        except ImportError as exc:  # pragma: no cover - environment issue
            raise ConversionError(
                Path("<startup>"),
                "MarkItDown is not installed. Run: pip install 'markitdown[all]'",
            ) from exc

        self._md = MarkItDown(enable_plugins=enable_plugins)

    # ------------------------------------------------------------------ #
    # Single-file conversion
    # ------------------------------------------------------------------ #
    def convert_file(
        self,
        source: os.PathLike | str,
        output_path: Optional[os.PathLike | str] = None,
        output_dir: Optional[os.PathLike | str] = None,
        overwrite: bool = True,
    ) -> ConversionResult:
        """Convert a single file to Markdown.

        If ``output_path`` is given it is used verbatim. Otherwise, when
        ``output_dir`` is given the output is written there with a ``.md``
        extension. If neither is given, the markdown is returned in-memory
        only (no file written).
        """
        src = Path(source).expanduser()
        if not src.exists():
            return ConversionResult(src, False, error="File not found")
        if not src.is_file():
            return ConversionResult(src, False, error="Not a file")

        try:
            result = self._md.convert(str(src))
        except Exception as exc:  # MarkItDown raises many exception types
            return ConversionResult(src, False, error=str(exc) or type(exc).__name__)

        markdown = result.text_content or ""
        title = getattr(result, "title", None)

        target: Optional[Path] = None
        if output_path is not None:
            target = Path(output_path).expanduser()
        elif output_dir is not None:
            target = Path(output_dir).expanduser() / (src.stem + ".md")

        if target is not None:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and not overwrite:
                    target = _dedupe_path(target)
                target.write_text(markdown, encoding="utf-8")
            except OSError as exc:
                return ConversionResult(
                    src, False, markdown=markdown, title=title,
                    error=f"Could not write output: {exc}",
                )

        return ConversionResult(
            src, True, output_path=target, markdown=markdown, title=title,
        )

    # ------------------------------------------------------------------ #
    # Batch conversion
    # ------------------------------------------------------------------ #
    def convert_many(
        self,
        sources: Sequence[os.PathLike | str],
        output_dir: Optional[os.PathLike | str] = None,
        overwrite: bool = True,
        progress: Optional[ProgressCallback] = None,
    ) -> BatchSummary:
        """Convert several files, reporting progress as each completes."""
        summary = BatchSummary()
        total = len(sources)
        for i, src in enumerate(sources, start=1):
            res = self.convert_file(
                src, output_dir=output_dir, overwrite=overwrite,
            )
            summary.results.append(res)
            if progress is not None:
                progress(i, total, res)
        return summary


def _dedupe_path(path: Path) -> Path:
    """Return a non-existing path by appending ' (1)', ' (2)', ... if needed."""
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    n = 1
    while True:
        candidate = parent / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def expand_inputs(
    paths: Iterable[os.PathLike | str],
    recursive: bool = False,
) -> List[Path]:
    """Expand a mix of files and directories into a flat list of files.

    Directories contribute their convertible files (respecting ``recursive``).
    Order is stable and duplicates are removed.
    """
    out: List[Path] = []
    seen: set[Path] = set()

    def add(p: Path) -> None:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            out.append(p)

    for raw in paths:
        p = Path(raw).expanduser()
        if p.is_dir():
            globber = p.rglob("*") if recursive else p.glob("*")
            for child in sorted(globber):
                if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
                    add(child)
        elif p.is_file():
            add(p)
    return out
