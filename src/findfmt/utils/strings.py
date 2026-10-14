"""String manipulation, sanitization, quoting, and metadata formatting utilities."""

from __future__ import annotations

import datetime as dt
import stat
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import os

DEFAULT_TIME_FORMAT = "%b %d %H:%M"
_MIN_PRINTABLE_ASCII = 32
_DEL_ASCII = 127

__all__ = [
    "DEFAULT_TIME_FORMAT",
    "format_display_path",
    "format_timestamp",
    "get_classification_indicator",
    "mask_control_characters",
    "quote_filename",
]


def mask_control_characters(text: str) -> str:
    """Replace non-printable control characters with question marks.

    Args:
        text: Input string potentially containing control characters.

    Returns:
        String with characters with ASCII ordinal < 32 or == 127 replaced by '?'.
    """
    return "".join(
        "?" if ord(c) < _MIN_PRINTABLE_ASCII or ord(c) == _DEL_ASCII else c for c in text
    )


def quote_filename(text: str) -> str:
    """Enclose filename in double quotes, escaping embedded quotes and backslashes.

    Args:
        text: Input filename or path string.

    Returns:
        Double-quoted string with interior backslashes and double quotes escaped.
    """
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def format_display_path(
    path_str: str,
    *,
    quote_name: bool = False,
    hide_control_chars: bool = False,
    literal: bool = False,
    indicator: str | None = None,
) -> str:
    """Format path string applying control character masking, quoting, and indicators.

    Args:
        path_str: Raw path or filename string.
        quote_name: Whether to enclose in double quotes with backslash escaping.
        hide_control_chars: Whether to mask non-printable characters as '?'.
        literal: Whether to output characters verbatim without masking.
        indicator: Optional classification indicator character to append.

    Returns:
        Formatted path or filename string.
    """
    result = path_str
    if hide_control_chars and not literal:
        result = mask_control_characters(result)

    if quote_name:
        result = quote_filename(result)

    if indicator:
        result = f"{result}{indicator}"

    return result


def format_timestamp(ts: float | None, fmt: str | None = None) -> str:
    """Format POSIX timestamp into a human-readable date/time string.

    Args:
        ts: Epoch timestamp in seconds, or None if unavailable.
        fmt: Optional strftime format string (defaults to '%b %d %H:%M').

    Returns:
        Formatted date/time string, or '-' if timestamp is None or cannot be formatted.
    """
    if ts is None:
        return "-"

    time_fmt = fmt if fmt is not None else DEFAULT_TIME_FORMAT
    try:
        date_obj = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).astimezone()
        return date_obj.strftime(time_fmt)
    except (OSError, OverflowError, ValueError):
        return "-"


def get_classification_indicator(
    *,
    is_dir: bool = False,
    is_symlink: bool = False,
    is_executable: bool = False,
    stat_result: os.stat_result | None = None,
) -> str | None:
    """Return the POSIX classification indicator character for a file.

    Args:
        is_dir: Whether the path represents a directory.
        is_symlink: Whether the path represents a symbolic link.
        is_executable: Whether the path is executable.
        stat_result: Optional stat_result for inspecting mode bits.

    Returns:
        Indicator character ('/', '*', '@', '=', '|', '>') or None.
    """
    if is_dir:
        return "/"

    if is_symlink:
        return "@"

    if stat_result is not None:
        mode = stat_result.st_mode
        if stat.S_ISSOCK(mode):
            return "="

        if stat.S_ISFIFO(mode):
            return "|"

        if hasattr(stat, "S_ISDOOR") and stat.S_ISDOOR(mode):
            return ">"

    return "*" if is_executable else None
