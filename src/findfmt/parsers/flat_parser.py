"""Flat newline-delimited directory and path listing parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from findfmt.parsers.symlink_parser import parse_symlink_target

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

__all__ = ["ParsedEntry", "parse_flat_listing"]

_TREE_TRAILER_RE = re.compile(
    r"^(?:[\d.,]+[A-Za-z]*\s+used\s+in\s+)?"
    r"\d+\s+director(?:y|ies)(?:,\s+\d+\s+files?)?$",
    re.IGNORECASE,
)


def is_tree_trailer(line: str) -> bool:
    """Return True if *line* matches a Unix/ASCII tree summary trailer."""
    return bool(_TREE_TRAILER_RE.match(line.strip()))


@dataclass(frozen=True, slots=True)
class ParsedEntry:
    """Represents an ingested entry extracted from an external input stream.

    Attributes:
        path_str: Reconstructed relative or absolute path string.
        is_symlink: Whether the entry was designated as a symbolic link.
        symlink_target: Target path if entry is a symlink, otherwise None.
        is_dir: Whether the entry represents a directory node.
    """

    path_str: str
    is_symlink: bool = False
    symlink_target: str | None = None
    is_dir: bool = False


def parse_flat_listing(lines: Iterable[str]) -> Iterator[ParsedEntry]:
    """Parse newline-delimited flat file paths into structured ParsedEntry records.

    Supports outputs from standard Unix tools such as 'find', 'git ls-files',
    and 'findfmt -i', normalizing leading './' indicators and detecting directory
    suffixes.

    Args:
        lines: Iterable yielding raw lines of input text.

    Yields:
        ParsedEntry instances for non-empty path records.
    """
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or is_tree_trailer(stripped):
            continue

        token, is_symlink, target = parse_symlink_target(stripped)
        token = token.removeprefix("./").removeprefix(".\\")

        if token in ("", ".", ".\\"):
            continue

        is_dir = token.endswith(("/", "\\"))
        clean_path = token.rstrip("/\\")
        if not clean_path or clean_path == ".":
            continue

        yield ParsedEntry(
            path_str=clean_path,
            is_symlink=is_symlink,
            symlink_target=target,
            is_dir=is_dir,
        )
