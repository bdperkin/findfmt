"""Tab-indented and whitespace outline directory structure parser."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from findfmt.parsers.flat_parser import ParsedEntry
from findfmt.parsers.symlink_parser import parse_symlink_target

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

__all__ = ["parse_tab_outline"]

_TREE_BRANCH_RE = re.compile(r"^([│|`\s]*[├└──+\\]──?\s*)")


def _clean_outline_line(raw: str) -> tuple[int, str, bool, str | None, bool] | None:
    """Extract column indent, clean token, symlink info, and directory flag from line."""
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
        return None

    leading_ws = raw[: len(raw) - len(raw.lstrip())]
    indent_col = len(leading_ws.expandtabs(4))

    content = raw.lstrip()
    branch_match = _TREE_BRANCH_RE.match(content)
    if branch_match:
        content = content[branch_match.end() :]
        indent_col += len(branch_match.group(1).expandtabs(4))

    token, is_symlink, target = parse_symlink_target(content)
    has_slash = token.endswith(("/", "\\"))
    clean_name = token.rstrip("/\\").strip()
    if not clean_name or clean_name in (".", "./", ".\\"):
        return None

    return indent_col, clean_name, is_symlink, target, has_slash


def parse_tab_outline(lines: Iterable[str]) -> Iterator[ParsedEntry]:
    """Parse hierarchical outline text into reconstructed full path entries.

    Reconstructs nested directory hierarchies based on indentation depth
    (supporting tabs or consistent whitespace), resolving parent-child
    relationships and symlink targets.

    Args:
        lines: Iterable yielding raw lines of outline text.

    Yields:
        ParsedEntry instances with fully qualified path strings.
    """
    parsed_items: list[tuple[int, str, bool, str | None, bool]] = []
    for line in lines:
        item = _clean_outline_line(line.rstrip("\r\n"))
        if item is not None:
            parsed_items.append(item)

    if not parsed_items:
        return

    stack: list[tuple[int, str]] = []
    total = len(parsed_items)

    for i in range(total):
        col, name, is_symlink, target, has_slash = parsed_items[i]
        has_children = i + 1 < total and parsed_items[i + 1][0] > col
        is_dir = has_slash or has_children

        while stack and stack[-1][0] >= col:
            stack.pop()

        stack.append((col, name))
        full_path = "/".join(segment for _, segment in stack)

        yield ParsedEntry(
            path_str=full_path,
            is_symlink=is_symlink,
            symlink_target=target,
            is_dir=is_dir,
        )
