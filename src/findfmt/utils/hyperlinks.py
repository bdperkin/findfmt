"""Terminal OSC 8 hyperlink generation and URI construction utilities."""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING

from findfmt.utils.strings import _ANSI_ESCAPE_RE, _URI_FORBIDDEN_CHARS, format_osc8_link

if TYPE_CHECKING:
    from pathlib import PurePath

__all__ = [
    "build_file_uri",
    "format_hyperlink",
    "format_osc8_link",
    "format_rich_link",
]

_ESCAPE_SEQ_RE = _ANSI_ESCAPE_RE


def _sanitize_uri_component(comp: str) -> str:
    """Sanitize authority or scheme against ANSI escapes and control characters."""
    stripped = _ESCAPE_SEQ_RE.sub("", comp)
    return "".join(c for c in stripped if c not in _URI_FORBIDDEN_CHARS)


def _normalize_schema(schema: str) -> tuple[str, str]:
    """Parse scheme and rest components from a URI schema specification."""
    schema_str = schema if "://" in schema else f"{schema}://"
    scheme, rest = schema_str.split("://", 1)
    return scheme, rest.strip("/")


def build_file_uri(
    path: PurePath | str,
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
    posix_path = path.replace("\\", "/") if isinstance(path, str) else path.as_posix()

    if not posix_path.startswith("/"):
        posix_path = f"/{posix_path}"

    raw_bytes = posix_path.encode("utf-8", errors="surrogateescape")
    quoted_path = urllib.parse.quote_from_bytes(raw_bytes, safe=b"/:")
    sanitized_schema = _sanitize_uri_component(schema)
    scheme, rest_clean = _normalize_schema(sanitized_schema)

    if authority:
        sanitized_auth = _sanitize_uri_component(authority)
        if rest_clean:
            return f"{scheme}://{sanitized_auth}/{rest_clean}{quoted_path}"

        return f"{scheme}://{sanitized_auth}{quoted_path}"

    if rest_clean:
        return f"{scheme}://{rest_clean}{quoted_path}"

    return f"{scheme}://{quoted_path}"


def format_rich_link(text: str, uri: str) -> str:
    """Format text as Rich console hyperlink markup.

    Args:
        text: Display text visible in terminal.
        uri: Destination hyperlink target URI.

    Returns:
        Rich markup string in [link=uri]text[/link] format.
    """
    clean_uri = (
        "".join(c for c in uri if c not in _URI_FORBIDDEN_CHARS)
        .replace("[", "%5B")
        .replace("]", "%5D")
        .replace('"', "%22")
    )
    return f"[link={clean_uri}]{text}[/link]"


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
