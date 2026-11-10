"""Internal helpers and state frames for iterative directory pruning and boundary checks."""

from __future__ import annotations

import contextlib
import os
from typing import TYPE_CHECKING, Any

from findfmt.classifier import _resolve_relative
from findfmt.exceptions import TraversalError
from findfmt.traversal.tags import INTERPRETER_TAGS, can_skip_file_by_tags

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    import pathspec

    from findfmt.models import FileInfo, TraversalConfig
    from findfmt.traversal.patterns import PatternMatcher

    PathSpecType = pathspec.PathSpec[Any]
else:
    PathSpecType = Any

__all__ = [
    "check_depth_limit",
    "check_file_limit",
    "is_candidate_file_entry",
    "should_skip_dir",
]


class _TraversalFrame:
    """Active directory frame for iterative depth-first traversal."""

    __slots__ = (
        "deferred_items",
        "depth",
        "idx",
        "inherited_match",
        "specs",
        "subdirs",
    )

    def __init__(
        self,
        *,
        subdirs: list[Path],
        specs: tuple[tuple[Path, PathSpecType], ...],
        depth: int,
        inherited_match: bool,
        deferred_items: Iterator[FileInfo] | None = None,
    ) -> None:
        self.subdirs = subdirs
        self.idx = 0
        self.specs = specs
        self.depth = depth
        self.inherited_match = inherited_match
        self.deferred_items = deferred_items


class _PruneFrame:
    """Active directory frame for iterative descendant pruning search."""

    __slots__ = (
        "depth",
        "dir_key",
        "effective_root",
        "idx",
        "inherited_match",
        "specs",
        "subdirs",
    )

    def __init__(  # noqa: PLR0913 - internal frame container
        self,
        *,
        dir_key: tuple[int, int],
        subdirs: list[Path],
        specs: tuple[tuple[Path, PathSpecType], ...],
        depth: int,
        inherited_match: bool,
        effective_root: Path,
    ) -> None:
        self.dir_key = dir_key
        self.subdirs = subdirs
        self.idx = 0
        self.specs = specs
        self.depth = depth
        self.inherited_match = inherited_match
        self.effective_root = effective_root


def check_file_limit(count: int, file_limit: int | None) -> bool:
    """Verify whether directory entry count does not exceed filelimit threshold."""
    if file_limit is not None and file_limit < 0:
        msg = f"file_limit must be non-negative, got {file_limit}"
        raise TraversalError(msg)

    return file_limit is None or count <= file_limit


def check_depth_limit(current_depth: int, max_depth: int | None) -> bool:
    """Determine whether traversal can descend further based on maximum depth."""
    if max_depth is not None and max_depth < 0:
        msg = f"max_depth must be non-negative, got {max_depth}"
        raise TraversalError(msg)

    return max_depth is None or current_depth < max_depth


def should_skip_dir(dir_name: str, *, include_hidden: bool) -> bool:
    """Determine if a directory should be skipped during descent."""
    return dir_name == ".git" or bool(not include_hidden and dir_name.startswith("."))


def is_candidate_file_entry(entry: os.DirEntry[str], *, follow_symlinks: bool) -> bool:
    """Determine if a directory entry is a candidate file or unfollowed symlink."""
    try:
        return entry.is_file(follow_symlinks=follow_symlinks) or (
            not follow_symlinks and entry.is_symlink() is True
        )
    except (OSError, RuntimeError):
        return False


def _can_skip_entry_by_tags(
    entry: os.DirEntry[str] | None,
    config: TraversalConfig,
    *,
    filename: str,
) -> bool:
    """Determine if a directory entry can be skipped early by filename/executable tags."""
    if entry is not None and config.follow_symlinks:
        with contextlib.suppress(OSError, RuntimeError):
            if entry.is_symlink() is True:
                return False

    is_exec: bool | None = None
    if entry is not None and (config.include_tags & INTERPRETER_TAGS):
        with contextlib.suppress(OSError, RuntimeError):
            is_exec = bool(
                entry.stat(follow_symlinks=config.follow_symlinks).st_mode & 0o111,
            )

    return can_skip_file_by_tags(filename, config, is_executable=is_exec)


def _can_skip_candidate_file(  # noqa: PLR0913 - wide CLI/config signature
    path: Path,
    entry: os.DirEntry[str] | None,
    config: TraversalConfig,
    *,
    base_root: Path,
    prefix: Path | None,
    matcher: PatternMatcher | None,
    inherited_match: bool,
) -> bool:
    """Check if a candidate file can be skipped before full classification."""
    rel_path = _resolve_relative(path, base_root, prefix=prefix)
    if matcher and not matcher.matches_file(rel_path, inherited_match=inherited_match):
        return True

    return _can_skip_entry_by_tags(entry, config, filename=path.name)


def _check_visited_or_memo(
    dir_key: tuple[int, int],
    visited: set[tuple[int, int]],
    memo: dict[tuple[int, int], bool],
) -> tuple[bool, bool]:
    """Check if directory key is already visited or cached in memo."""
    if dir_key in visited:
        return True, False

    if dir_key in memo:
        return True, memo[dir_key]

    return False, False


def _scan_sorted_entries(
    directory: Path,
    memo: dict[tuple[int, int], bool],
    dir_key: tuple[int, int],
    *,
    on_error: Callable[[OSError], None] | None = None,
) -> list[os.DirEntry[str]] | None:
    """Scan directory entries safely, closing handle and tracking memo on error."""
    try:
        with os.scandir(directory) as scan_it:
            return sorted(scan_it, key=lambda e: e.name)
    except (OSError, RuntimeError) as err:
        memo[dir_key] = False
        if isinstance(err, OSError) and on_error is not None:
            if not err.filename:
                err.filename = str(directory)

            on_error(err)

        return None
