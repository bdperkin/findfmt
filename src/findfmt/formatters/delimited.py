"""Delimited tabular output serializers (CSV, TSV)."""

from __future__ import annotations

import csv
import io
import sys
from typing import TYPE_CHECKING, Literal, TextIO, cast

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

from findfmt.formatters.base import TABLE_FIELD_NAMES, Formatter

_QuotingType = Literal[0, 1, 2, 3]

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo

__all__ = [
    "CsvFormatter",
    "TsvFormatter",
    "escape_tsv_cell",
    "file_to_record",
]


def file_to_record(
    file_info: FileInfo,
    *,
    absolute: bool,
) -> tuple[str, str, str, str, str, str, str, str]:
    """Convert a FileInfo instance into a sequence of cell string values.

    Args:
        file_info: Classified file information.
        absolute: Whether to emit absolute path.

    Returns:
        Tuple of 8 string values matching TABLE_FIELD_NAMES.
    """
    return (
        str(file_info.path if absolute else file_info.relative_path),
        str(file_info.relative_path),
        ", ".join(sorted(file_info.tags)),
        file_info.mime_type or "",
        file_info.shebang or "",
        "true" if file_info.is_executable else "false",
        "true" if file_info.is_symlink else "false",
        str(file_info.size_bytes),
    )


def escape_tsv_cell(cell: str) -> str:
    """Escape special characters in TSV cell to preserve single-line records.

    Args:
        cell: Raw cell string value.

    Returns:
        Escaped cell value with tabs, newlines, and backslashes escaped.
    """
    return cell.replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")


class CsvFormatter(Formatter):
    """RFC 4180 compliant comma-separated values serializer."""

    def __init__(
        self,
        *,
        absolute: bool = False,
        delimiter: str = ",",
        quoting: int = csv.QUOTE_MINIMAL,
        lineterminator: str = "\n",
    ) -> None:
        """Initialize CsvFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            delimiter: Column delimiter character (defaults to comma).
            quoting: Quoting mode from standard library csv module.
            lineterminator: Record terminator string (defaults to newline).
        """
        super().__init__(absolute=absolute)
        self.delimiter = delimiter
        self.quoting = quoting
        self.lineterminator = lineterminator

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format FileInfo objects into an RFC 4180 CSV string.

        Args:
            files: Iterable of classified file objects.

        Returns:
            Formatted CSV document with header row.
        """
        buffer = io.StringIO()
        self.stream(files, buffer)
        return buffer.getvalue()

    @override
    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream CSV records directly to a text stream.

        Args:
            files: Iterable of classified file objects.
            stream: Target text stream.
        """
        writer = csv.writer(
            stream,
            delimiter=self.delimiter,
            quoting=cast("_QuotingType", self.quoting),
            lineterminator=self.lineterminator,
        )
        writer.writerow(TABLE_FIELD_NAMES)
        for file_info in files:
            writer.writerow(file_to_record(file_info, absolute=self.absolute))

        stream.flush()


class TsvFormatter(Formatter):
    """Tab-separated values (TSV) serializer for Unix pipelines."""

    def __init__(
        self,
        *,
        absolute: bool = False,
        lineterminator: str = "\n",
    ) -> None:
        """Initialize TsvFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            lineterminator: Record terminator string (defaults to newline).
        """
        super().__init__(absolute=absolute)
        self.lineterminator = lineterminator

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format FileInfo objects into a TSV string.

        Args:
            files: Iterable of classified file objects.

        Returns:
            Formatted TSV document with header row.
        """
        buffer = io.StringIO()
        self.stream(files, buffer)
        return buffer.getvalue()

    @override
    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream TSV records directly to a text stream.

        Args:
            files: Iterable of classified file objects.
            stream: Target text stream.
        """
        stream.write("\t".join(TABLE_FIELD_NAMES) + self.lineterminator)
        for file_info in files:
            record = file_to_record(file_info, absolute=self.absolute)
            escaped_cells = [escape_tsv_cell(c) for c in record]
            stream.write("\t".join(escaped_cells) + self.lineterminator)

        stream.flush()
