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

import rich.markup
from rich.table import Table

from findfmt.formatters.base import TABLE_FIELD_NAMES, Formatter, write_stream_safe
from findfmt.formatters.visual import RICH_BOX_STYLES, UnsupportedBoxStyleError
from findfmt.terminal import get_console

_QuotingType = Literal[0, 1, 2, 3]

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo

__all__ = [
    "FORMULA_TRIGGER_CHARS",
    "CsvFormatter",
    "CsvTableFormatter",
    "TsvFormatter",
    "escape_tsv_cell",
    "file_to_record",
    "sanitize_csv_cell",
]

FORMULA_TRIGGER_CHARS: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(cell: str) -> str:
    """Neutralize spreadsheet formula injection by prefixing trigger characters with a single quote.

    Spreadsheet applications (e.g. Excel, LibreOffice Calc, Google Sheets) interpret
    cells beginning with '=', '+', '-', '@', TAB, or CR as executable formulas or commands.
    Prefixing such cells with a single quote (') forces spreadsheet engines to treat the
    content strictly as text.

    Args:
        cell: Raw cell string value.

    Returns:
        Sanitized cell string prefixed with "'" if beginning with a formula trigger, else unchanged.
    """
    if cell.startswith(FORMULA_TRIGGER_CHARS):
        return f"'{cell}"

    return cell


def file_to_record(
    file_info: FileInfo,
    *,
    absolute: bool,
    csv_safe: bool = False,
) -> tuple[str, str, str, str, str, str, str, str]:
    """Convert a FileInfo instance into a sequence of cell string values.

    Args:
        file_info: Classified file information.
        absolute: Whether to emit absolute path.
        csv_safe: Whether to prefix formula trigger characters with a single quote.

    Returns:
        Tuple of 8 string values matching TABLE_FIELD_NAMES.
    """
    raw_record = (
        str(file_info.path if absolute else file_info.relative_path),
        str(file_info.relative_path),
        ", ".join(sorted(file_info.tags)),
        file_info.mime_type or "",
        file_info.shebang or "",
        "true" if file_info.is_executable else "false",
        "true" if file_info.is_symlink else "false",
        str(file_info.size_bytes),
    )
    if csv_safe:
        return (
            sanitize_csv_cell(raw_record[0]),
            sanitize_csv_cell(raw_record[1]),
            sanitize_csv_cell(raw_record[2]),
            sanitize_csv_cell(raw_record[3]),
            sanitize_csv_cell(raw_record[4]),
            sanitize_csv_cell(raw_record[5]),
            sanitize_csv_cell(raw_record[6]),
            sanitize_csv_cell(raw_record[7]),
        )

    return raw_record


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
        csv_safe: bool = False,
    ) -> None:
        """Initialize CsvFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            delimiter: Column delimiter character (defaults to comma).
            quoting: Quoting mode from standard library csv module.
            lineterminator: Record terminator string (defaults to newline).
            csv_safe: Whether to neutralize formula injection triggers with a single quote.
        """
        super().__init__(absolute=absolute)
        self.delimiter = delimiter
        self.quoting = quoting
        self.lineterminator = lineterminator
        self.csv_safe = csv_safe

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
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="surrogateescape")

        writer = csv.writer(
            stream,
            delimiter=self.delimiter,
            quoting=cast("_QuotingType", self.quoting),
            lineterminator=self.lineterminator,
        )
        writer.writerow(TABLE_FIELD_NAMES)
        for file_info in files:
            writer.writerow(
                file_to_record(file_info, absolute=self.absolute, csv_safe=self.csv_safe),
            )

        stream.flush()


class TsvFormatter(Formatter):
    """Tab-separated values (TSV) serializer for Unix pipelines."""

    def __init__(
        self,
        *,
        absolute: bool = False,
        lineterminator: str = "\n",
        csv_safe: bool = False,
    ) -> None:
        """Initialize TsvFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            lineterminator: Record terminator string (defaults to newline).
            csv_safe: Whether to neutralize formula injection triggers with a single quote.
        """
        super().__init__(absolute=absolute)
        self.lineterminator = lineterminator
        self.csv_safe = csv_safe

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
        write_stream_safe(stream, "\t".join(TABLE_FIELD_NAMES) + self.lineterminator)
        for file_info in files:
            record = file_to_record(file_info, absolute=self.absolute, csv_safe=self.csv_safe)
            escaped_cells = [escape_tsv_cell(c) for c in record]
            write_stream_safe(stream, "\t".join(escaped_cells) + self.lineterminator)

        stream.flush()


class CsvTableFormatter(Formatter):
    """Aligned ASCII/Unicode table constructed directly from CSV schema."""

    def __init__(
        self,
        *,
        absolute: bool = False,
        table_style: str = "rounded",
        console_width: int | None = None,
        force_color: bool | None = None,
        csv_safe: bool = False,
    ) -> None:
        """Initialize CsvTableFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            table_style: Border style name mapping to rich.box styles.
            console_width: Optional terminal output column width override.
            force_color: Explicit color enable override flag.
            csv_safe: Whether to neutralize formula injection triggers with a single quote.

        Raises:
            UnsupportedBoxStyleError: If table_style is not recognized.
        """
        super().__init__(absolute=absolute)
        normalized = table_style.lower().strip()
        if normalized not in RICH_BOX_STYLES:
            valid_styles = ", ".join(sorted(RICH_BOX_STYLES.keys()))
            raise UnsupportedBoxStyleError(table_style, valid_styles)

        self.table_style = normalized
        self.box_style = RICH_BOX_STYLES[normalized]
        self.console_width = console_width
        self.force_color = force_color
        self.csv_safe = csv_safe

    def _build_table(self, files: Iterable[FileInfo]) -> Table:
        """Construct a Rich Table populated with CSV record rows."""
        table = Table(
            box=self.box_style,
            show_header=True,
            header_style="bold cyan",
            title="findfmt CSV Table",
        )
        for field_name in TABLE_FIELD_NAMES:
            table.add_column(field_name, no_wrap=field_name in {"path", "relative_path"})

        for file_info in files:
            rec = file_to_record(file_info, absolute=self.absolute, csv_safe=self.csv_safe)
            escaped_rec = [rich.markup.escape(c) for c in rec]
            table.add_row(*escaped_rec)

        return table

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Render CSV records into an aligned table string."""
        table = self._build_table(files)
        buf = io.StringIO()
        width = self.console_width if self.console_width is not None else 120
        get_console(buf, width=width, force_color=self.force_color).print(table)
        return buf.getvalue()

    @override
    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream aligned CSV table directly to a text stream."""
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="surrogateescape")

        table = self._build_table(files)
        get_console(stream, width=self.console_width, force_color=self.force_color).print(table)
