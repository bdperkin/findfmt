"""Sorting algorithms, natural version ordering, and entry partitioning."""

from __future__ import annotations

import os
import re
import sys
from typing import TYPE_CHECKING, Any

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

from findfmt.exceptions import InvalidSortCriteriaError
from findfmt.models import SortKey

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

    from findfmt.models import TraversalConfig

__all__ = [
    "InvalidSortCriteriaError",
    "collect_directory_entries",
    "get_entry_ctime",
    "get_entry_mtime",
    "get_entry_size",
    "get_sort_key_fn",
    "is_reverse_sort",
    "natural_sort_key",
    "resolve_sort_key",
    "sort_directory_entries",
]

_RE_DIGITS = re.compile(r"(\d+)")
_DESCENDING_KEYS = {SortKey.TIME, SortKey.MTIME, SortKey.CTIME, SortKey.SIZE}
_SORT_KEY_MAP: dict[str, SortKey] = {
    "name": SortKey.NAME,
    "version": SortKey.VERSION,
    "time": SortKey.TIME,
    "mtime": SortKey.TIME,
    "ctime": SortKey.CTIME,
    "size": SortKey.SIZE,
    "none": SortKey.NONE,
    "unsorted": SortKey.NONE,
}


class _SortChunk:
    """Type-safe comparable token for natural sort keys."""

    __slots__ = ("is_digit", "val_int", "val_str")

    def __init__(self, val: str) -> None:
        if val.isdigit():
            self.is_digit = True
            self.val_int = int(val)
            self.val_str = ""
        else:
            self.is_digit = False
            self.val_int = 0
            self.val_str = val

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, _SortChunk):
            return NotImplemented

        if self.is_digit != other.is_digit:
            return self.is_digit

        if self.is_digit:
            return self.val_int < other.val_int

        return self.val_str < other.val_str

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _SortChunk):
            return False

        if self.is_digit != other.is_digit:
            return False

        return self.val_int == other.val_int if self.is_digit else self.val_str == other.val_str

    @override
    def __hash__(self) -> int:
        return hash((self.is_digit, self.val_int, self.val_str))


def natural_sort_key(
    name: str,
    *,
    ignore_case: bool = False,
) -> tuple[tuple[_SortChunk, ...], str]:
    """Generate natural version sort key chunking embedded integers.

    Args:
        name: Entry filename to chunk.
        ignore_case: Whether string chunks are compared case-insensitively.

    Returns:
        Tuple of parsed SortChunk tokens, with filename tie-breaker.
    """
    normalized = name.lower() if ignore_case else name
    chunks = tuple(
        _SortChunk(part.lower() if ignore_case else part) for part in _RE_DIGITS.split(name) if part
    )
    return chunks, normalized


def get_entry_mtime(entry: os.DirEntry[str], *, follow_symlinks: bool = False) -> float:
    """Retrieve cached modification timestamp from DirEntry stat."""
    try:
        return entry.stat(follow_symlinks=follow_symlinks).st_mtime
    except OSError:
        return 0.0


def get_entry_ctime(entry: os.DirEntry[str], *, follow_symlinks: bool = False) -> float:
    """Retrieve cached status change timestamp from DirEntry stat."""
    try:
        return entry.stat(follow_symlinks=follow_symlinks).st_ctime
    except OSError:
        return 0.0


def get_entry_size(entry: os.DirEntry[str], *, follow_symlinks: bool = False) -> int:
    """Retrieve cached file size in bytes from DirEntry stat."""
    try:
        return entry.stat(follow_symlinks=follow_symlinks).st_size
    except OSError:
        return 0


def is_reverse_sort(config: TraversalConfig) -> bool:
    """Determine whether active sort order is inverted.

    Args:
        config: Traversal configuration with active sort parameters.

    Returns:
        True if elements should be sorted in descending order, False otherwise.
    """
    if config.sort_by in _DESCENDING_KEYS:
        return not config.reverse_sort

    return config.reverse_sort


def get_sort_key_fn(config: TraversalConfig) -> Callable[[os.DirEntry[str]], Any]:
    """Obtain comparison key extractor function for directory entries.

    Args:
        config: Active traversal configuration.

    Returns:
        Callable extracting sort key from an os.DirEntry instance.
    """
    follow = config.follow_symlinks
    ic = config.ignore_case

    match config.sort_by:
        case SortKey.VERSION:
            return lambda e: natural_sort_key(e.name, ignore_case=ic)
        case SortKey.TIME | SortKey.MTIME:
            return lambda e: get_entry_mtime(e, follow_symlinks=follow)
        case SortKey.CTIME:
            return lambda e: get_entry_ctime(e, follow_symlinks=follow)
        case SortKey.SIZE:
            return lambda e: get_entry_size(e, follow_symlinks=follow)
        case _:
            return lambda e: e.name.lower() if ic else e.name


def sort_directory_entries(
    entries: list[os.DirEntry[str]],
    config: TraversalConfig,
) -> list[os.DirEntry[str]]:
    """Sort directory entries according to traversal configuration.

    Args:
        entries: Mutable list of os.DirEntry objects to sort.
        config: Traversal configuration containing sort criteria.

    Returns:
        Sorted list of directory entries.
    """
    if config.sort_by == SortKey.NONE:
        return entries

    if config.sort_by in _DESCENDING_KEYS:
        entries.sort(key=lambda e: e.name.lower() if config.ignore_case else e.name)

    entries.sort(
        key=get_sort_key_fn(config),
        reverse=is_reverse_sort(config),
    )
    return entries


def collect_directory_entries(
    root: Path,
    config: TraversalConfig,
) -> Iterable[os.DirEntry[str]] | None:
    """Collect and optionally sort directory entries from filesystem root.

    Args:
        root: Directory path to scan.
        config: Traversal configuration with sort and file_limit parameters.

    Returns:
        Iterable of os.DirEntry objects, or None on error or exceeded limit.
    """
    try:
        scandir_iter = os.scandir(root)
    except OSError:
        return None

    if config.sort_by == SortKey.NONE:
        if config.file_limit is None:
            return scandir_iter

        entries: list[os.DirEntry[str]] = []
        for entry in scandir_iter:
            entries.append(entry)
            if len(entries) > config.file_limit:
                return None

        return entries

    entries_list = list(scandir_iter)
    if config.file_limit is not None and len(entries_list) > config.file_limit:
        return None

    return sort_directory_entries(entries_list, config)


def resolve_sort_key(value: str | SortKey | None, *, unsorted: bool = False) -> SortKey:
    """Resolve CLI sort parameter and unsorted flag to canonical SortKey enum.

    Args:
        value: Input string or SortKey enum from CLI.
        unsorted: Whether the raw unsorted flag (-U) was passed.

    Returns:
        Canonical SortKey enum value.

    Raises:
        ValueError: If input string does not match any recognized criteria.
    """
    if unsorted:
        return SortKey.NONE

    if value is None:
        return SortKey.NAME

    if isinstance(value, SortKey):
        return value

    key = _SORT_KEY_MAP.get(value.strip().lower())
    if key is not None:
        return key

    raise InvalidSortCriteriaError(value)
