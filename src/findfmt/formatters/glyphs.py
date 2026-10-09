"""Line drawing glyph sets and console box styles for findfmt formatters."""

from __future__ import annotations

from rich.box import Box

__all__ = [
    "CP437_BOX",
    "TREE_GUIDE_SETS",
    "resolve_tree_guides",
]

# Rich Tree guide lines tuple: (space, continue, fork, end)
TREE_GUIDE_SETS: dict[str, tuple[str, str, str, str]] = {
    "unicode": ("    ", "│   ", "├── ", "└── "),
    "ansi": ("    ", "\x1b(0x\x1b(B   ", "\x1b(0tqq\x1b(B ", "\x1b(0mqq\x1b(B "),
    "cp437": ("    ", "\xb3   ", "\xc3\xc4\xc4 ", "\xc0\xc4\xc4 "),
    "none": ("", "", "", ""),
}

# Code Page 437 (IBM-PC) table box style using hardware box drawing characters
CP437_BOX = Box(
    "\xda\xc4\xc2\xbf\n"
    "\xb3 \xb3\xb3\n"
    "\xc3\xc4\xc5\xb4\n"
    "\xb3 \xb3\xb3\n"
    "\xc3\xc4\xc5\xb4\n"
    "\xc3\xc4\xc5\xb4\n"
    "\xb3 \xb3\xb3\n"
    "\xc0\xc4\xc1\xd9\n",
)


def resolve_tree_guides(
    *,
    no_indent: bool = False,
    ansi_lines: bool = False,
    cp437: bool = False,
) -> tuple[str, str, str, str]:
    """Resolve tree guide line drawing glyph set based on formatting flags.

    Precedence order:
    1. If no_indent is True, return empty strings (indentation omitted).
    2. If ansi_lines is True, return ANSI/VT100 alternate character set escapes.
    3. If cp437 is True, return CP437 box-drawing characters.
    4. Otherwise, return standard Unicode box-drawing characters.

    Args:
        no_indent: Whether to suppress branch indentation lines.
        ansi_lines: Whether to use ANSI/VT100 escape sequences.
        cp437: Whether to use CP437 console characters.

    Returns:
        4-tuple of (space, continue, fork, end) guide strings.
    """
    if no_indent:
        return TREE_GUIDE_SETS["none"]

    if ansi_lines:
        return TREE_GUIDE_SETS["ansi"]

    if cp437:
        return TREE_GUIDE_SETS["cp437"]

    return TREE_GUIDE_SETS["unicode"]
