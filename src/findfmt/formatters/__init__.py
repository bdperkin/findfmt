"""Output formatting engines for findfmt."""

from __future__ import annotations

from findfmt.formatters.base import Formatter, OutputFormat, UnsupportedFormatError
from findfmt.formatters.structured import (
    IpynbFormatter,
    JsonFormatter,
    JsonlFormatter,
    YamlFormatter,
)
from findfmt.formatters.text import TextFormatter

__all__ = [
    "Formatter",
    "IpynbFormatter",
    "JsonFormatter",
    "JsonlFormatter",
    "OutputFormat",
    "TextFormatter",
    "UnsupportedFormatError",
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
        return format_type.value

    return str(format_type).lower().strip()


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


def get_formatter(
    format_type: OutputFormat | str,
    *,
    absolute: bool = False,
    show_tags: bool = False,
    delimiter: str = "\n",
    **kwargs: object,
) -> Formatter:
    """Retrieve the appropriate formatter instance for the given format.

    Args:
        format_type: Requested output format enum or string name.
        absolute: Whether to emit absolute paths.
        show_tags: Whether to display tags (for text format).
        delimiter: Delimiter string (for text format).
        **kwargs: Extra formatter configuration arguments.

    Returns:
        Configured Formatter instance.

    Raises:
        UnsupportedFormatError: If format_type is not a recognized output format.
    """
    fmt_str = _normalize_format_name(format_type)

    if fmt_str == OutputFormat.TEXT.value:
        return TextFormatter(
            absolute=absolute,
            show_tags=show_tags,
            delimiter=delimiter,
        )

    structured = _create_structured_formatter(fmt_str, absolute=absolute, kwargs=kwargs)
    if structured is not None:
        return structured

    valid_formats = ", ".join(f.value for f in OutputFormat)
    raise UnsupportedFormatError(str(format_type), valid_formats)
