"""Markup documentation table serializers (Markdown, reStructuredText)."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TextIO

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

from findfmt.formatters.base import TABLE_FIELD_NAMES, Formatter
from findfmt.formatters.delimited import file_to_record

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from findfmt.models import FileInfo

__all__ = [
    "MarkdownFormatter",
    "RstFormatter",
    "UnsupportedTableStyleError",
    "escape_markdown_cell",
    "escape_rst_cell",
]

_MARKDOWN_ALIGNMENTS: tuple[str, ...] = (
    "left",  # path
    "left",  # relative_path
    "left",  # tags
    "left",  # mime_type
    "left",  # shebang
    "center",  # is_executable
    "center",  # is_symlink
    "right",  # size_bytes
)


def escape_markdown_cell(cell: str) -> str:
    """Escape special characters in a Markdown table cell."""
    return (
        cell.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\t", " ")
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def escape_rst_cell(cell: str) -> str:
    """Escape special characters in a reStructuredText table cell."""
    return (
        cell.replace("|", "\\|")
        .replace("\t", " ")
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def _pad_cell(cell: str, width: int, alignment: str) -> str:
    """Pad a cell string according to its alignment specification."""
    if alignment == "center":
        return cell.center(width)

    if alignment == "right":
        return cell.rjust(width)

    return cell.ljust(width)


def _make_markdown_separator(width: int, alignment: str) -> str:
    """Construct a GFM column alignment indicator."""
    if alignment == "center":
        return f":{'-' * max(3, width - 2)}:"

    if alignment == "right":
        return f"{'-' * max(3, width - 1)}:"

    return f":{'-' * max(3, width - 1)}"


def _compute_markdown_col_widths(rows: Sequence[Sequence[str]]) -> list[int]:
    """Calculate column widths for a GFM table."""
    min_widths = [5 if align == "center" else 4 for align in _MARKDOWN_ALIGNMENTS]
    widths: list[int] = []
    for idx, header in enumerate(TABLE_FIELD_NAMES):
        max_data = max((len(r[idx]) for r in rows), default=0)
        widths.append(max(len(header), min_widths[idx], max_data))

    return widths


def _render_markdown_row(cells: Sequence[str], col_widths: Sequence[int]) -> str:
    """Format a single row of cells into a Markdown table line."""
    padded = [
        _pad_cell(cell, col_widths[i], _MARKDOWN_ALIGNMENTS[i]) for i, cell in enumerate(cells)
    ]
    return f"| {' | '.join(padded)} |"


class MarkdownFormatter(Formatter):
    """GitHub Flavored Markdown (GFM) column-aligned table serializer."""

    def __init__(self, *, absolute: bool = False, no_indent: bool = False) -> None:
        """Initialize MarkdownFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            no_indent: Whether to strip column whitespace padding.
        """
        super().__init__(absolute=absolute)
        self.no_indent = no_indent

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format FileInfo objects into a GFM table string."""
        rows = [
            [escape_markdown_cell(c) for c in file_to_record(f, absolute=self.absolute)]
            for f in files
        ]
        if self.no_indent:
            header_line = f"|{'|'.join(TABLE_FIELD_NAMES)}|"
            seps = [
                ":---:" if a == "center" else ("---:" if a == "right" else ":---")
                for a in _MARKDOWN_ALIGNMENTS
            ]
            sep_line = f"|{'|'.join(seps)}|"
            body_lines = [f"|{'|'.join(row)}|" for row in rows]
            return "\n".join([header_line, sep_line, *body_lines]) + "\n"

        col_widths = _compute_markdown_col_widths(rows)
        header_line = _render_markdown_row(TABLE_FIELD_NAMES, col_widths)
        separators = [
            _make_markdown_separator(col_widths[i], _MARKDOWN_ALIGNMENTS[i])
            for i in range(len(TABLE_FIELD_NAMES))
        ]
        sep_line = f"| {' | '.join(separators)} |"
        body_lines = [_render_markdown_row(row, col_widths) for row in rows]
        return "\n".join([header_line, sep_line, *body_lines]) + "\n"

    @override
    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream formatted Markdown table to a text stream."""
        stream.write(self.format(files))
        stream.flush()


def _format_rst_grid(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    col_widths: Sequence[int],
) -> str:
    """Render a reStructuredText grid table."""
    row_border = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    head_border = "+" + "+".join("=" * (w + 2) for w in col_widths) + "+"

    header_line = (
        "| " + " | ".join(h.ljust(w) for h, w in zip(headers, col_widths, strict=True)) + " |"
    )

    lines = [row_border, header_line, head_border]
    for row in rows:
        row_line = (
            "| " + " | ".join(cell.ljust(w) for cell, w in zip(row, col_widths, strict=True)) + " |"
        )
        lines.append(row_line)
        lines.append(row_border)

    if not rows:
        lines.append(row_border)

    return "\n".join(lines) + "\n"


def _format_rst_simple(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    col_widths: Sequence[int],
) -> str:
    """Render a reStructuredText simple table."""
    border = " ".join("=" * w for w in col_widths)
    header_line = " ".join(h.ljust(w) for h, w in zip(headers, col_widths, strict=True))

    lines = [border, header_line, border]
    for row in rows:
        row_line = " ".join(cell.ljust(w) for cell, w in zip(row, col_widths, strict=True))
        lines.append(row_line)

    lines.append(border)

    return "\n".join(lines) + "\n"


class UnsupportedTableStyleError(ValueError):
    """Raised when an unsupported table style is requested."""

    def __init__(self, table_style: str) -> None:
        """Initialize UnsupportedTableStyleError.

        Args:
            table_style: The invalid table style requested.
        """
        super().__init__(
            f"Unsupported RST table style: '{table_style}'. Expected 'grid' or 'simple'.",
        )


class RstFormatter(Formatter):
    """reStructuredText grid or simple table serializer for Sphinx docs."""

    def __init__(
        self,
        *,
        absolute: bool = False,
        table_style: str = "grid",
    ) -> None:
        """Initialize RstFormatter."""
        super().__init__(absolute=absolute)
        norm = table_style.lower().strip()
        if norm not in {"grid", "simple"}:
            raise UnsupportedTableStyleError(table_style)

        self.table_style = norm

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format FileInfo objects into a reStructuredText table string."""
        rows: list[list[str]] = [
            [escape_rst_cell(c) for c in file_to_record(f, absolute=self.absolute)] for f in files
        ]

        col_widths = [
            max(len(header), max((len(r[idx]) for r in rows), default=0), 1)
            for idx, header in enumerate(TABLE_FIELD_NAMES)
        ]

        if self.table_style == "simple":
            return _format_rst_simple(TABLE_FIELD_NAMES, rows, col_widths)

        return _format_rst_grid(TABLE_FIELD_NAMES, rows, col_widths)

    @override
    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream formatted reStructuredText table to a text stream."""
        stream.write(self.format(files))
        stream.flush()
