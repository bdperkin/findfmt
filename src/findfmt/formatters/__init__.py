"""Output formatting engines for findfmt."""

from __future__ import annotations

import csv

from findfmt.formatters.base import (
    TABLE_FIELD_NAMES,
    Formatter,
    OutputFormat,
    UnsupportedFormatError,
)
from findfmt.formatters.delimited import CsvFormatter, TsvFormatter
from findfmt.formatters.markup import (
    MarkdownFormatter,
    RstFormatter,
    UnsupportedTableStyleError,
)
from findfmt.formatters.structured import (
    IpynbFormatter,
    JsonFormatter,
    JsonlFormatter,
    YamlFormatter,
)
from findfmt.formatters.text import TextFormatter

__all__ = [
    "TABLE_FIELD_NAMES",
    "CsvFormatter",
    "Formatter",
    "IpynbFormatter",
    "JsonFormatter",
    "JsonlFormatter",
    "MarkdownFormatter",
    "OutputFormat",
    "RstFormatter",
    "TextFormatter",
    "TsvFormatter",
    "UnsupportedFormatError",
    "UnsupportedTableStyleError",
    "YamlFormatter",
    "get_formatter",
]


def _normalize_format_name(format_type: OutputFormat | str) -> str:
    """Normalize format argument to lowercase string value.

    Args:
        format_type: Requested output format enum or string.

    Returns:
        Normalized lowercase format string.
    """
    if isinstance(format_type, OutputFormat):
        val = format_type.value
    else:
        val = str(format_type).lower().strip()

    if val == OutputFormat.MD.value:
        return OutputFormat.MARKDOWN.value

    return val


def _create_structured_formatter(
    fmt_str: str,
    *,
    absolute: bool,
    kwargs: dict[str, object],
) -> Formatter | None:
    """Instantiate structured formatter if matched.

    Args:
        fmt_str: Normalized format string.
        absolute: Whether to emit absolute paths.
        kwargs: Configuration keyword arguments.

    Returns:
        Structured formatter instance or None if not a structured format.
    """
    if fmt_str == OutputFormat.JSON.value:
        indent = kwargs.get("indent", 2)
        indent_val = indent if isinstance(indent, int) or indent is None else 2
        return JsonFormatter(absolute=absolute, indent=indent_val)

    if fmt_str == OutputFormat.JSONL.value:
        return JsonlFormatter(absolute=absolute)

    if fmt_str == OutputFormat.YAML.value:
        indent = kwargs.get("indent", 2)
        indent_int = indent if isinstance(indent, int) else 2
        return YamlFormatter(absolute=absolute, indent=indent_int)

    if fmt_str == OutputFormat.IPYNB.value:
        return IpynbFormatter(absolute=absolute)

    return None


def _create_delimited_formatter(
    fmt_str: str,
    *,
    absolute: bool,
    record_delimiter: str,
    kwargs: dict[str, object],
) -> Formatter | None:
    r"""Instantiate delimited formatter if matched.

    Args:
        fmt_str: Normalized format string.
        absolute: Whether to emit absolute paths.
        record_delimiter: Record terminator string ('\n' or '\0').
        kwargs: Configuration keyword arguments.

    Returns:
        Delimited formatter instance or None if not matched.
    """
    lineterminator = "\0" if record_delimiter == "\0" else "\n"

    if fmt_str == OutputFormat.CSV.value:
        csv_delim = kwargs.get("delimiter", ",")
        if csv_delim in {"\n", "\0"}:
            csv_delim = ","

        delim_str = str(csv_delim)
        quoting = kwargs.get("quoting", csv.QUOTE_MINIMAL)
        quoting_int = int(quoting) if isinstance(quoting, int) else csv.QUOTE_MINIMAL
        return CsvFormatter(
            absolute=absolute,
            delimiter=delim_str,
            quoting=quoting_int,
            lineterminator=lineterminator,
        )

    if fmt_str == OutputFormat.TSV.value:
        return TsvFormatter(absolute=absolute, lineterminator=lineterminator)

    return None


def _create_markup_formatter(
    fmt_str: str,
    *,
    absolute: bool,
    kwargs: dict[str, object],
) -> Formatter | None:
    """Instantiate markup table formatter if matched.

    Args:
        fmt_str: Normalized format string.
        absolute: Whether to emit absolute paths.
        kwargs: Configuration keyword arguments.

    Returns:
        Markup formatter instance or None if not matched.
    """
    if fmt_str == OutputFormat.MARKDOWN.value:
        return MarkdownFormatter(absolute=absolute)

    if fmt_str == OutputFormat.RST.value:
        style = kwargs.get("table_style", "grid")
        style_str = str(style) if isinstance(style, str) else "grid"
        return RstFormatter(absolute=absolute, table_style=style_str)

    return None


def get_formatter(
    format_type: OutputFormat | str,
    *,
    absolute: bool = False,
    show_tags: bool = False,
    delimiter: str | None = None,
    **kwargs: object,
) -> Formatter:
    """Retrieve the appropriate formatter instance for the given format.

    Args:
        format_type: Requested output format enum or string name.
        absolute: Whether to emit absolute paths.
        show_tags: Whether to display tags (for text format).
        delimiter: Optional delimiter string (for text/csv format).
        **kwargs: Extra formatter configuration arguments.

    Returns:
        Configured Formatter instance.

    Raises:
        UnsupportedFormatError: If format_type is not a recognized output format.
    """
    fmt_str = _normalize_format_name(format_type)

    if delimiter is not None:
        kwargs["delimiter"] = delimiter

    if fmt_str == OutputFormat.TEXT.value:
        return TextFormatter(
            absolute=absolute,
            show_tags=show_tags,
            delimiter=delimiter if delimiter is not None else "\n",
        )

    record_delim = delimiter if delimiter is not None else "\n"
    delimited = _create_delimited_formatter(
        fmt_str,
        absolute=absolute,
        record_delimiter=record_delim,
        kwargs=kwargs,
    )
    if delimited is not None:
        return delimited

    markup = _create_markup_formatter(fmt_str, absolute=absolute, kwargs=kwargs)
    if markup is not None:
        return markup

    structured = _create_structured_formatter(fmt_str, absolute=absolute, kwargs=kwargs)
    if structured is not None:
        return structured

    valid_formats = ", ".join(f.value for f in OutputFormat)
    raise UnsupportedFormatError(str(format_type), valid_formats)
