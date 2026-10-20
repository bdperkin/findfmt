"""Base interfaces and protocols for output formatters."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TextIO

from findfmt.exceptions import UnsupportedFormatError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo

__all__ = [
    "TABLE_FIELD_NAMES",
    "Formatter",
    "OutputFormat",
    "UnsupportedFormatError",
    "write_stream_safe",
]


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
    CSV_TABLE = "csv-table"
    NDJSON = "ndjson"
    XML = "xml"
    HTML = "html"


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


def write_stream_safe(stream: TextIO, content: str) -> None:
    """Write text content to a text stream, handling surrogate escapes safely.

    If the target stream or its wrapper raises UnicodeEncodeError, this attempts
    to encode with errors='surrogateescape' and write directly to the stream's
    underlying binary buffer.

    Args:
        stream: Target text stream.
        content: String content potentially containing surrogate code points.
    """
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(errors="surrogateescape")

    try:
        stream.write(content)
    except UnicodeEncodeError:
        buffer = getattr(stream, "buffer", None)
        if buffer is not None:
            encoding = getattr(stream, "encoding", None) or "utf-8"
            buffer.write(content.encode(encoding, errors="surrogateescape"))
        else:
            raise


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
        write_stream_safe(stream, self.format(files))
        stream.flush()
