"""String manipulation, sanitization, quoting, and metadata formatting utilities."""

from __future__ import annotations

import datetime as dt
import locale
import re
import stat
import unicodedata
from typing import TYPE_CHECKING

import rich.markup
from rich.cells import cell_len

from findfmt.i18n import get_current_locale

if TYPE_CHECKING:
    import os

DEFAULT_TIME_FORMAT = "%b %d %H:%M"
_MIN_PRINTABLE_ASCII = 32
_DEL_ASCII = 127
_C1_CONTROL_MIN = 128
_C1_CONTROL_MAX = 159

_ANSI_ESCAPE_RE = re.compile(
    r"""
    \x1b\[[0-?]*[ -/]*[@-~]                  # 7-bit CSI sequence
    | \x1b\][^\x07\x1b]*(?:\x07|\x1b\\)        # 7-bit OSC sequence
    | \x1b[ -/]*[0-~]                        # 7-bit Fe/Fs/Fp sequence
    | \x9b[0-?]*[ -/]*[@-~]                  # 8-bit C1 CSI sequence
    | \x9d[^\x07\x1b\x9c\x9d]*(?:\x07|\x1b\\|\x9c)    # 8-bit C1 OSC sequence
    """,
    re.VERBOSE,
)

_URI_FORBIDDEN_CHARS = {
    c
    for c in (chr(i) for i in range(256))
    if ord(c) < _MIN_PRINTABLE_ASCII
    or ord(c) == _DEL_ASCII
    or (_C1_CONTROL_MIN <= ord(c) <= _C1_CONTROL_MAX)
    or c == "\x1b"
}

__all__ = [
    "DEFAULT_TIME_FORMAT",
    "cell_width",
    "format_display_path",
    "format_osc8_link",
    "format_timestamp",
    "get_classification_indicator",
    "mask_control_characters",
    "pad_to_cell_width",
    "quote_filename",
    "resolve_time_format",
    "strip_ansi_escapes",
]


def strip_ansi_escapes(text: str) -> str:
    """Strip ANSI escape sequences (CSI, OSC, and 8-bit C1 sequences) from text.

    Args:
        text: Input string potentially containing ANSI escape sequences.

    Returns:
        String with all recognized ANSI escape sequences removed.
    """
    return _ANSI_ESCAPE_RE.sub("", text)


def cell_width(text: str) -> int:
    """Calculate the terminal monospace cell display width of a string.

    Accounts for ANSI escape sequences (which occupy 0 display cells) and
    East Asian full-width/double-width characters (which occupy 2 display cells).

    Args:
        text: String whose display width is to be measured.

    Returns:
        Total number of terminal display cells occupied by the string.
    """
    clean_text = strip_ansi_escapes(text)
    return cell_len(clean_text)


def pad_to_cell_width(
    text: str,
    width: int,
    align: str = "left",
    fillchar: str = " ",
) -> str:
    """Pad a string to target cell width respecting double-width CJK characters.

    Args:
        text: Input string to pad.
        width: Desired display width in terminal cells.
        align: Alignment direction ('left', 'right', or 'center').
        fillchar: Single-width character used for padding (defaults to ' ').

    Returns:
        Padded string with target cell width.
    """
    current_width = cell_width(text)
    padding = max(0, width - current_width)
    if padding == 0:
        return text

    if align == "center":
        left_pad = padding // 2
        right_pad = padding - left_pad
        return f"{fillchar * left_pad}{text}{fillchar * right_pad}"

    if align == "right":
        return f"{fillchar * padding}{text}"

    return f"{text}{fillchar * padding}"


def format_osc8_link(text: str, uri: str) -> str:
    """Wrap text in an OSC 8 terminal hyperlink escape sequence.

    Args:
        text: Display text visible in terminal.
        uri: Destination hyperlink target URI.

    Returns:
        ANSI string containing OSC 8 escape sequences wrapping the text.
    """
    clean_uri = "".join(c for c in uri if c not in _URI_FORBIDDEN_CHARS)
    return f"\033]8;;{clean_uri}\033\\{text}\033]8;;\033\\"


def mask_control_characters(text: str) -> str:
    """Replace non-printable and bidirectional control characters with question marks.

    Args:
        text: Input string potentially containing control characters.

    Returns:
        String with C0 (ord < 32), DEL (ord == 127), C1 (128 <= ord <= 159),
        and Unicode format (Cf) control characters replaced by '?'.
    """
    return "".join(
        "?"
        if ord(c) < _MIN_PRINTABLE_ASCII
        or ord(c) == _DEL_ASCII
        or (_C1_CONTROL_MIN <= ord(c) <= _C1_CONTROL_MAX)
        or (ord(c) > _DEL_ASCII and unicodedata.category(c) == "Cf")
        else c
        for c in text
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


def format_display_path(  # noqa: PLR0913
    path_str: str,
    *,
    quote_name: bool = False,
    hide_control_chars: bool = False,
    literal: bool = False,
    indicator: str | None = None,
    hyperlink: bool = False,
    uri: str | None = None,
    escape_markup: bool = False,
) -> str:
    """Format path string applying control character masking, quoting, indicators, and links.

    Args:
        path_str: Raw path or filename string.
        quote_name: Whether to enclose in double quotes with backslash escaping.
        hide_control_chars: Whether to mask non-printable and bidirectional control
            characters as '?'.
        literal: Whether to output characters verbatim without masking.
        indicator: Optional classification indicator character to append.
        hyperlink: Whether to wrap formatted path in an OSC 8 terminal hyperlink.
        uri: Target destination URI for terminal hyperlink.
        escape_markup: Whether to escape Rich console markup characters ([ and ]).

    Returns:
        Formatted path or filename string.
    """
    result = path_str
    if not literal:
        result = strip_ansi_escapes(result)
        result = mask_control_characters(result)
    elif hide_control_chars:
        result = mask_control_characters(result)

    if quote_name:
        result = quote_filename(result)

    if indicator:
        result = f"{result}{indicator}"

    if escape_markup:
        result = rich.markup.escape(result)

    if hyperlink and uri:
        if escape_markup and result.startswith("\\"):
            result = format_osc8_link(f"\\{result}", uri)
        else:
            result = format_osc8_link(result, uri)

    return result


def resolve_time_format(fmt: str | None = None) -> str:
    """Resolve the active strftime format string respecting active locale.

    If fmt is provided, it is returned verbatim.
    Otherwise, if standard POSIX nl_langinfo(locale.D_T_FMT) is available and
    the current locale is not C/POSIX, the localized datetime format is used.
    If nl_langinfo is unavailable or raises an exception, a regional fallback or
    DEFAULT_TIME_FORMAT is used.

    Args:
        fmt: Explicit strftime format string or None.

    Returns:
        Resolved strftime format string.
    """
    if fmt is not None:
        return fmt

    if hasattr(locale, "nl_langinfo") and hasattr(locale, "D_T_FMT"):
        try:
            lang_fmt = locale.nl_langinfo(locale.D_T_FMT)
            if lang_fmt:
                curr = get_current_locale()
                if curr in ("C", "POSIX") and lang_fmt == "%a %b %e %H:%M:%S %Y":
                    return DEFAULT_TIME_FORMAT

                return lang_fmt
        except (locale.Error, ValueError, OSError):
            pass

    curr = get_current_locale()
    prefix = curr.split("_", maxsplit=1)[0].split(".", maxsplit=1)[0].lower()
    fallback_formats = {
        "ja": "%Y年%m月%d日 %H時%M分%S秒",
        "de": "%d.%m.%Y %H:%M:%S",
        "fr": "%d/%m/%Y %H:%M:%S",
        "es": "%d/%m/%Y %H:%M:%S",
    }
    return fallback_formats.get(prefix, DEFAULT_TIME_FORMAT)


def format_timestamp(ts: float | None, fmt: str | None = None) -> str:
    """Format POSIX timestamp into a human-readable date/time string.

    Args:
        ts: Epoch timestamp in seconds, or None if unavailable.
        fmt: Optional strftime format string (defaults to localized format or '%b %d %H:%M').

    Returns:
        Formatted date/time string, or '-' if timestamp is None or cannot be formatted.
    """
    if ts is None:
        return "-"

    time_fmt = resolve_time_format(fmt)
    try:
        date_obj = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).astimezone()
        try:
            return date_obj.strftime(time_fmt)
        except ValueError:
            return date_obj.strftime(DEFAULT_TIME_FORMAT)
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
