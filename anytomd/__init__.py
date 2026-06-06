"""AnythingToMarkdown — convert PDFs, Office docs, and more to Markdown.

A lightweight cross-platform GUI + CLI tool powered by Microsoft's MarkItDown.
"""

__version__ = "1.0.0"
__app_name__ = "AnythingToMarkdown"

from .converter import (
    ConversionError,
    ConversionResult,
    Converter,
    SUPPORTED_EXTENSIONS,
)

__all__ = [
    "Converter",
    "ConversionResult",
    "ConversionError",
    "SUPPORTED_EXTENSIONS",
    "__version__",
    "__app_name__",
]
