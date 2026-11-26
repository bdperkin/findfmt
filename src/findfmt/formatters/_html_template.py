"""HTML5 document template, URL encoding, and fragment-loading helpers for HtmlFormatter."""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING

from findfmt.exceptions import FindFmtError

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "DEFAULT_TITLE",
    "HTML_TEMPLATE",
    "build_href",
    "read_utf8_fragment",
]

DEFAULT_TITLE = "Directory Tree"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{
      font-family:
        ui-monospace,
        SFMono-Regular,
        Menlo,
        Monaco,
        Consolas,
        "Liberation Mono",
        "Courier New",
        monospace;
      margin: 2rem;
      background: #ffffff;
      color: #24292f;
    }}
    h1 {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 1.5rem;
      margin-bottom: 1rem;
    }}
    .tree {{
      line-height: 1.6;
      font-size: 0.95rem;
    }}
    .tree a {{
      text-decoration: none;
      color: #0969da;
    }}
    .tree a:hover {{
      text-decoration: underline;
    }}
    .tree .dir {{
      font-weight: bold;
      color: #0969da;
    }}
    .tree .file {{
      color: #24292f;
    }}
    .tree .symlink {{
      color: #8250df;
    }}
    .tree .meta {{
      color: #57606a;
      margin-right: 0.5rem;
    }}
    .tree .size {{
      color: #1a7f37;
      margin-left: 0.5rem;
    }}
    .tree .mime {{
      color: #6e7781;
      margin-left: 0.5rem;
      font-style: italic;
    }}
    .tree .badge {{
      display: inline-block;
      padding: 0.1em 0.4em;
      font-size: 0.8em;
      font-weight: 500;
      border-radius: 4px;
      background-color: #f6f8fa;
      border: 1px solid #d0d7de;
      color: #24292f;
      margin-left: 0.25rem;
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
{intro}  <pre class="tree"><code>{listing}</code></pre>
{outro}</body>
</html>
"""


def build_href(base_href: str | None, target_path: Path) -> str:
    """Format and URL-encode path with optional base HREF prefix."""
    posix_path = target_path.as_posix()
    if posix_path in {".", ""}:
        return base_href or "."

    quoted_segments = [
        urllib.parse.quote_from_bytes(
            seg.encode("utf-8", errors="surrogateescape"),
        )
        for seg in posix_path.split("/")
        if seg
    ]
    quoted_path = "/".join(quoted_segments)

    if base_href is None or not base_href:
        return quoted_path

    if base_href.endswith("/"):
        return f"{base_href}{quoted_path}"

    return f"{base_href}/{quoted_path}"


def read_utf8_fragment(path: Path) -> str:
    """Read an HTML template fragment as UTF-8, raising FindFmtError on failure."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        msg = f"Cannot read '{path}' as UTF-8: {err}"
        raise FindFmtError(msg) from err
