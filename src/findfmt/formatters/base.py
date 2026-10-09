"""Base interfaces and protocols for output formatters."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo


class OutputFormat(str, enum.Enum):
    """Supported output serialization formats."""

    TEXT = "text"
    JSON = "json"
    JSONL = "jsonl"
    YAML = "yaml"
    IPYNB = "ipynb"
    CSV = "csv"
    TSV = "tsv"
    MARKDOWN = "markdown"
    MD = "md"
    RST = "rst"
    TABLE = "table"
    TREE = "tree"


TABLE_FIELD_NAMES: tuple[str, ...] = (
    "path",
    "relative_path",
    "tags",
    "mime_type",
    "shebang",
    "is_executable",
    "is_symlink",
    "size_bytes",
)


class UnsupportedFormatError(ValueError):
    """Raised when an unsupported output format is requested."""

    def __init__(self, format_type: str, valid_formats: str) -> None:
        """Initialize UnsupportedFormatError.

        Args:
            format_type: The invalid format requested.
            valid_formats: Comma-separated list of valid formats.
        """
        super().__init__(
            f"Unsupported output format: '{format_type}'. Expected one of: {valid_formats}",
        )


class Formatter(ABC):
    """Abstract base class for all findfmt output formatters."""

    def __init__(self, *, absolute: bool = False) -> None:
        """Initialize formatter.

        Args:
            absolute: Whether to format paths as absolute rather than relative.
        """
        self.absolute = absolute

    @abstractmethod
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format an iterable of FileInfo instances into a string.

        Args:
            files: Iterable of classified file objects.

        Returns:
            Formatted string representation.
        """

    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream formatted output directly to a text stream.

        Args:
            files: Iterable of classified file objects.
            stream: Target text output stream (e.g., sys.stdout).
        """
        stream.write(self.format(files))
        stream.flush()
