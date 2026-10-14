"""Terminal OSC 8 hyperlink generation and URI construction utilities."""

from __future__ import annotations

import urllib.parse
from pathlib import Path

__all__ = [
    "build_file_uri",
    "format_hyperlink",
    "format_osc8_link",
    "format_rich_link",
]


def _normalize_schema(schema: str) -> tuple[str, str]:
    """Parse scheme and rest components from a URI schema specification."""
    schema_str = schema if "://" in schema else f"{schema}://"
    scheme, rest = schema_str.split("://", 1)
    return scheme, rest.strip("/")


def build_file_uri(
    path: Path | str,
    *,
    schema: str = "file://",
    authority: str | None = None,
) -> str:
    """Construct a well-formed URI for a filesystem path.

    Args:
        path: Filesystem path object or string.
        schema: URI schema prefix (e.g. 'file://', 'vscode://file/', 'subl://').
        authority: Optional URI authority component (e.g. 'localhost', hostname).

    Returns:
        Fully qualified, URL-encoded URI string.
    """
    p = Path(path) if isinstance(path, str) else path
    posix_path = p.as_posix()
    if not posix_path.startswith("/"):
        posix_path = f"/{posix_path}"

    quoted_path = urllib.parse.quote(posix_path, safe="/")
    scheme, rest_clean = _normalize_schema(schema)

    if authority:
        if rest_clean:
            return f"{scheme}://{authority}/{rest_clean}{quoted_path}"

        return f"{scheme}://{authority}{quoted_path}"

    if rest_clean:
        return f"{scheme}://{rest_clean}{quoted_path}"

    return f"{scheme}://{quoted_path}"


def format_osc8_link(text: str, uri: str) -> str:
    """Wrap text in an OSC 8 terminal hyperlink escape sequence.

    Args:
        text: Display text visible in terminal.
        uri: Destination hyperlink target URI.

    Returns:
        ANSI string containing OSC 8 escape sequences wrapping the text.
    """
    return f"\033]8;;{uri}\033\\{text}\033]8;;\033\\"


def format_rich_link(text: str, uri: str) -> str:
    """Format text as Rich console hyperlink markup.

    Args:
        text: Display text visible in terminal.
        uri: Destination hyperlink target URI.

    Returns:
        Rich markup string in [link=uri]text[/link] format.
    """
    return f"[link={uri}]{text}[/link]"


def format_hyperlink(text: str, uri: str, *, rich_markup: bool = False) -> str:
    """Format a clickable hyperlink using either raw OSC 8 escapes or Rich markup.

    Args:
        text: Display text visible in terminal.
        uri: Destination hyperlink target URI.
        rich_markup: If True, returns Rich markup; otherwise raw OSC 8 sequence.

    Returns:
        Formatted hyperlink string.
    """
    if rich_markup:
        return format_rich_link(text, uri)

    return format_osc8_link(text, uri)
