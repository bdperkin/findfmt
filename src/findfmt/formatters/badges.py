"""Tag badge formatting and color mapping for visual renderers."""

from __future__ import annotations

import rich.markup

__all__ = ["TAG_COLOR_MAP", "format_tag_badge"]

TAG_COLOR_MAP: dict[str, str] = {
    "binary": "red",
    "c": "bright_cyan",
    "cpp": "blue",
    "executable": "yellow",
    "json": "cyan",
    "markdown": "bright_magenta",
    "python": "bright_blue",
    "rust": "bright_red",
    "shell": "bright_yellow",
    "text": "green",
    "yaml": "magenta",
}


def format_tag_badge(tag: str) -> str:
    """Render a colorful tag pill badge in Rich markup format."""
    color = TAG_COLOR_MAP.get(tag.lower(), "cyan")
    escaped_tag = rich.markup.escape(tag)
    return f"[black on {color}] {escaped_tag} [/]"
