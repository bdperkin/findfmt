"""Output formatting engines for findfmt."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from findfmt.formatters.base import (
    TABLE_FIELD_NAMES,
    Formatter,
    OutputFormat,
    UnsupportedFormatError,
)
from findfmt.formatters.delimited import (
    CsvFormatter,
    CsvTableFormatter,
    TsvFormatter,
)
from findfmt.formatters.html_formatter import HtmlFormatter
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
from findfmt.formatters.visual import (
    RichTableFormatter,
    RichTreeFormatter,
)
from findfmt.formatters.xml_formatter import XmlFormatter

__all__ = [
    "TABLE_FIELD_NAMES",
    "CsvFormatter",
    "CsvTableFormatter",
    "Formatter",
    "HtmlFormatter",
    "IpynbFormatter",
    "JsonFormatter",
    "JsonlFormatter",
    "MarkdownFormatter",
    "OutputFormat",
    "RichTableFormatter",
    "RichTreeFormatter",
    "RstFormatter",
    "TextFormatter",
    "TsvFormatter",
    "UnsupportedFormatError",
    "UnsupportedTableStyleError",
    "XmlFormatter",
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

    if val == OutputFormat.NDJSON.value:
        return OutputFormat.JSONL.value

    return val


def _resolve_indent(kwargs: dict[str, object], default: int = 2) -> int | None:
    """Extract integer indent or default."""
    indent = kwargs.get("indent", default)
    return indent if isinstance(indent, int) or indent is None else default


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
    no_indent = bool(kwargs.get("no_indent", False))
    if fmt_str == OutputFormat.JSON.value:
        return JsonFormatter(
            absolute=absolute,
            indent=_resolve_indent(kwargs, 2),
            no_indent=no_indent,
        )

    if fmt_str == OutputFormat.JSONL.value:
        return JsonlFormatter(absolute=absolute)

    if fmt_str == OutputFormat.YAML.value:
        indent_val = _resolve_indent(kwargs, 2)
        indent_int = indent_val if isinstance(indent_val, int) else 2
        return YamlFormatter(absolute=absolute, indent=indent_int, no_indent=no_indent)

    if fmt_str == OutputFormat.IPYNB.value:
        return IpynbFormatter(absolute=absolute)

    return None


def _extract_common_formatter_kwargs(kwargs: dict[str, object]) -> dict[str, Any]:
    """Extract POSIX metadata and rendering kwargs for tree-based serializers."""
    time_fmt_raw = kwargs.get("time_format")
    time_fmt = str(time_fmt_raw) if time_fmt_raw is not None else None
    schema_raw = kwargs.get("hyperlink_schema")
    schema = str(schema_raw) if schema_raw is not None else "file://"
    auth_raw = kwargs.get("hyperlink_authority")
    auth = str(auth_raw) if auth_raw is not None else None
    return {
        "show_permissions": bool(kwargs.get("show_permissions", False)),
        "show_user": bool(kwargs.get("show_user", False)),
        "show_group": bool(kwargs.get("show_group", False)),
        "show_inodes": bool(kwargs.get("show_inodes", False)),
        "show_device": bool(kwargs.get("show_device", False)),
        "show_size": bool(kwargs.get("show_size", False)),
        "human_readable": bool(kwargs.get("human_readable", False)),
        "show_si": bool(kwargs.get("show_si", False)),
        "accumulate_size": bool(kwargs.get("accumulate_size", False)),
        "show_mtime": bool(kwargs.get("show_mtime", False)),
        "show_ctime": bool(kwargs.get("show_ctime", False)),
        "time_format": time_fmt,
        "classify": bool(kwargs.get("classify", False)),
        "hide_control_chars": bool(kwargs.get("hide_control_chars", False)),
        "literal": bool(kwargs.get("literal", False)),
        "quote_name": bool(kwargs.get("quote_name", False)),
        "hyperlink": bool(kwargs.get("hyperlink", False)),
        "hyperlink_schema": schema,
        "hyperlink_authority": auth,
    }


def _as_str(val: object | None) -> str | None:
    """Cast non-None value to string."""
    return str(val) if val is not None else None


def _as_path(val: object | None) -> Path | None:
    """Return value if Path instance, otherwise None."""
    return val if isinstance(val, Path) else None


def _create_html_formatter(
    *,
    absolute: bool,
    common: dict[str, Any],
    kwargs: dict[str, object],
) -> HtmlFormatter:
    """Instantiate configured HtmlFormatter."""
    return HtmlFormatter(
        absolute=absolute,
        base_href=_as_str(kwargs.get("base_href")),
        title=_as_str(kwargs.get("title")),
        intro=_as_str(kwargs.get("intro")),
        intro_file=_as_path(kwargs.get("intro_file")),
        outro=_as_str(kwargs.get("outro")),
        outro_file=_as_path(kwargs.get("outro_file")),
        no_links=bool(kwargs.get("no_links", False)),
        no_indent=bool(kwargs.get("no_indent", False)),
        **common,  # type: ignore[arg-type]
    )


def _create_document_formatter(
    fmt_str: str,
    *,
    absolute: bool,
    kwargs: dict[str, object],
) -> Formatter | None:
    """Instantiate XML or HTML document serializer if matched."""
    if fmt_str == OutputFormat.XML.value:
        common = _extract_common_formatter_kwargs(kwargs)
        for key in ("hyperlink", "hyperlink_schema", "hyperlink_authority"):
            common.pop(key, None)

        return XmlFormatter(
            absolute=absolute,
            no_indent=bool(kwargs.get("no_indent", False)),
            **common,  # type: ignore[arg-type]
        )

    if fmt_str == OutputFormat.HTML.value:
        common = _extract_common_formatter_kwargs(kwargs)
        for key in ("hyperlink", "hyperlink_schema", "hyperlink_authority"):
            common.pop(key, None)

        return _create_html_formatter(absolute=absolute, common=common, kwargs=kwargs)

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

    if fmt_str == OutputFormat.CSV_TABLE.value:
        style = kwargs.get("table_style", "rounded")
        style_str = style if isinstance(style, str) else "rounded"
        color_raw = kwargs.get("force_color")
        color = color_raw if isinstance(color_raw, bool) else None
        return CsvTableFormatter(absolute=absolute, table_style=style_str, force_color=color)

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
        return MarkdownFormatter(
            absolute=absolute,
            no_indent=bool(kwargs.get("no_indent", False)),
        )

    if fmt_str == OutputFormat.RST.value:
        style = kwargs.get("table_style", "grid")
        style_str = str(style) if isinstance(style, str) else "grid"
        return RstFormatter(absolute=absolute, table_style=style_str)

    return None


def _create_visual_formatter(
    fmt_str: str,
    *,
    absolute: bool,
    kwargs: dict[str, object],
) -> Formatter | None:
    """Instantiate visual formatter if matched.

    Args:
        fmt_str: Normalized format string.
        absolute: Whether to emit absolute paths.
        kwargs: Configuration keyword arguments.

    Returns:
        Visual formatter instance or None if not matched.
    """
    force_color_raw = kwargs.get("force_color")
    force_color = force_color_raw if isinstance(force_color_raw, bool) else None
    common = _extract_common_formatter_kwargs(kwargs)

    if fmt_str == OutputFormat.TABLE.value:
        style = kwargs.get("table_style", "rounded")
        style_str = str(style) if isinstance(style, str) else "rounded"
        return RichTableFormatter(
            absolute=absolute,
            table_style=style_str,
            force_color=force_color,
            **common,  # type: ignore[arg-type]
        )

    if fmt_str == OutputFormat.TREE.value:
        return RichTreeFormatter(
            absolute=absolute,
            force_color=force_color,
            no_indent=bool(kwargs.get("no_indent", False)),
            ansi_lines=bool(kwargs.get("ansi_lines", False)),
            cp437=bool(kwargs.get("cp437", False)),
            **common,  # type: ignore[arg-type]
        )

    return None


def _create_text_formatter(
    *,
    absolute: bool,
    show_tags: bool,
    delimiter: str | None,
    kwargs: dict[str, object],
) -> TextFormatter:
    """Instantiate text formatter."""
    delim = delimiter if delimiter is not None else "\n"
    common = _extract_common_formatter_kwargs(kwargs)
    common.pop("accumulate_size", None)
    return TextFormatter(
        absolute=absolute,
        show_tags=show_tags,
        delimiter=delim,
        **common,  # type: ignore[arg-type]
    )


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
        return _create_text_formatter(
            absolute=absolute,
            show_tags=show_tags,
            delimiter=delimiter,
            kwargs=kwargs,
        )

    visual = _create_visual_formatter(fmt_str, absolute=absolute, kwargs=kwargs)
    if visual is not None:
        return visual

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

    document = _create_document_formatter(fmt_str, absolute=absolute, kwargs=kwargs)
    if document is not None:
        return document

    valid_formats = ", ".join(f.value for f in OutputFormat)
    raise UnsupportedFormatError(str(format_type), valid_formats)
