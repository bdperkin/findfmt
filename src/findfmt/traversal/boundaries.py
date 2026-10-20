"""Directory traversal boundaries and pruning evaluation engine."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from findfmt.classifier import _resolve_relative, classify_file
from findfmt.traversal.devices import check_device_boundary, resolve_device
from findfmt.traversal.filters import matches_filter
from findfmt.traversal.ignore import (
    is_path_ignored,
    load_child_specs,
    resolve_active_specs,
)
from findfmt.traversal.symlinks import init_visited_dirs, should_skip_symlink_dir
from findfmt.traversal.tags import INTERPRETER_TAGS, can_skip_file_by_tags

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    import pathspec

    from findfmt.models import FileInfo, TraversalConfig
    from findfmt.traversal.patterns import PatternMatcher

    PathSpecType = pathspec.PathSpec[Any]
else:
    PathSpecType = Any

__all__ = [
    "can_skip_file_by_tags",
    "check_depth_limit",
    "check_device_boundary",
    "check_file_limit",
    "filter_directory_entry",
    "has_matching_descendants",
    "init_visited_dirs",
    "matches_filter",
    "resolve_active_specs",
    "resolve_device",
    "should_skip_dir",
    "should_skip_symlink_dir",
    "yield_matching_items",
]


def check_file_limit(count: int, file_limit: int | None) -> bool:
    """Verify whether directory entry count does not exceed filelimit threshold."""
    return file_limit is None or count <= file_limit


def check_depth_limit(current_depth: int, max_depth: int | None) -> bool:
    """Determine whether traversal can descend further based on maximum depth."""
    return max_depth is None or current_depth < max_depth


def should_skip_dir(dir_name: str, *, include_hidden: bool) -> bool:
    """Determine if a directory should be skipped during descent."""
    return dir_name == ".git" or bool(not include_hidden and dir_name.startswith("."))


def _is_entry_excluded(  # noqa: PLR0913
    entry_path: Path,
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    is_dir: bool,
    matcher: PatternMatcher | None,
    base_root: Path | None,
) -> bool:
    """Check if entry path is ignored by gitignore or excluded by pattern matcher."""
    if (config.respect_gitignore or specs) and is_path_ignored(
        entry_path,
        is_dir=is_dir,
        specs=specs,
    ):
        return True

    return bool(matcher and matcher.should_exclude(entry_path, is_dir=is_dir, base_root=base_root))


def filter_directory_entry(  # noqa: PLR0913
    entry: os.DirEntry[str],
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    root_dev: int | None,
    *,
    matcher: PatternMatcher | None = None,
    base_root: Path | None = None,
) -> tuple[Path, bool] | None:
    """Filter an entry based on hidden status, device boundary, and gitignore."""
    if not config.include_hidden and entry.name.startswith("."):
        return None

    entry_path = Path(entry.path)
    if root_dev is not None and not check_device_boundary(entry_path, root_dev):
        return None

    try:
        is_dir = entry.is_dir(follow_symlinks=config.follow_symlinks)
    except (OSError, RuntimeError):
        return None

    if _is_entry_excluded(
        entry_path,
        config,
        specs,
        is_dir=is_dir,
        matcher=matcher,
        base_root=base_root,
    ):
        return None

    return entry_path, is_dir


def _inspect_entries(  # noqa: PLR0913
    entries: Sequence[os.DirEntry[str]],
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    root_dev: int | None,
    *,
    matcher: PatternMatcher | None = None,
    inherited_match: bool = False,
    base_root: Path | None = None,
) -> tuple[list[Path], bool]:
    """Inspect directory entries and return discovered subdirs or match flag."""
    subdirs: list[Path] = []
    for entry in entries:
        filtered = filter_directory_entry(
            entry,
            config,
            specs,
            root_dev,
            matcher=matcher,
            base_root=base_root,
        )
        if filtered is None:
            continue

        entry_path, is_dir = filtered
        if is_dir:
            if not should_skip_dir(entry.name, include_hidden=config.include_hidden):
                subdirs.append(entry_path)
        else:
            try:
                is_file = entry.is_file(follow_symlinks=config.follow_symlinks)
            except (OSError, RuntimeError):
                continue

            if is_file:
                is_exec: bool | None = None
                if config.include_tags & INTERPRETER_TAGS:
                    with contextlib.suppress(OSError, RuntimeError):
                        is_exec = bool(
                            entry.stat(follow_symlinks=config.follow_symlinks).st_mode & 0o111,
                        )

                if can_skip_file_by_tags(entry.name, config, is_executable=is_exec):
                    continue

                info = classify_file(entry_path, entry=entry)
                if matches_filter(info, config, matcher=matcher, inherited_match=inherited_match):
                    return [], True

    return subdirs, False


def _check_visited_or_memo(
    dir_key: tuple[int, int],
    visited: set[tuple[int, int]] | None,
    memo: dict[tuple[int, int], bool] | None,
) -> tuple[bool, bool]:
    """Check if directory key is already visited or cached in memo."""
    if visited is not None and dir_key in visited:
        return True, False

    if memo is not None and dir_key in memo:
        return True, memo[dir_key]

    return False, False


def _scan_sorted_entries(
    directory: Path,
    memo: dict[tuple[int, int], bool] | None,
    dir_key: tuple[int, int],
) -> list[os.DirEntry[str]] | None:
    """Scan directory entries safely, closing handle and tracking memo on error."""
    try:
        with os.scandir(directory) as scan_it:
            return sorted(scan_it, key=lambda e: e.name)
    except (OSError, RuntimeError):
        if memo is not None:
            memo[dir_key] = False

        return None


def _has_matching_in_subdirs(  # noqa: PLR0913
    subdirs: Sequence[Path],
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    root_dev: int | None,
    current_depth: int,
    matcher: PatternMatcher | None,
    inherited_match: bool,
    effective_root: Path,
    visited: set[tuple[int, int]],
    memo: dict[tuple[int, int], bool],
) -> bool:
    """Recursively search discovered child subdirectories for matching files."""
    for subdir in subdirs:
        child_specs = load_child_specs(subdir, specs) if config.respect_gitignore else specs
        child_inherit = bool(
            matcher
            and matcher.should_inherit_match(
                subdir,
                base_root=effective_root,
                parent_inherited=inherited_match,
            ),
        )
        if has_matching_descendants(
            subdir,
            config,
            child_specs,
            root_dev=root_dev,
            current_depth=current_depth + 1,
            matcher=matcher,
            inherited_match=child_inherit,
            base_root=effective_root,
            visited=visited,
            memo=memo,
        ):
            return True

    return False


def _eval_descendants(  # noqa: PLR0913
    entries: Sequence[os.DirEntry[str]],
    directory: Path,
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    root_dev: int | None,
    current_depth: int,
    matcher: PatternMatcher | None,
    inherited_match: bool,
    base_root: Path | None,
    visited: set[tuple[int, int]],
    memo: dict[tuple[int, int], bool],
) -> bool:
    """Evaluate entries directly and descend into subdirectories if needed."""
    subdirs, found = _inspect_entries(
        entries,
        config,
        specs,
        root_dev,
        matcher=matcher,
        inherited_match=inherited_match,
        base_root=base_root,
    )
    if found:
        return True

    if not check_depth_limit(current_depth, config.max_depth):
        return False

    effective_root = base_root if base_root is not None else directory
    return _has_matching_in_subdirs(
        subdirs,
        config,
        specs,
        root_dev=root_dev,
        current_depth=current_depth,
        matcher=matcher,
        inherited_match=inherited_match,
        effective_root=effective_root,
        visited=visited,
        memo=memo,
    )


def has_matching_descendants(  # noqa: PLR0913
    directory: Path,
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    root_dev: int | None = None,
    current_depth: int = 1,
    matcher: PatternMatcher | None = None,
    inherited_match: bool = False,
    base_root: Path | None = None,
    visited: set[tuple[int, int]] | None = None,
    memo: dict[tuple[int, int], bool] | None = None,
) -> bool:
    """Determine whether a directory or any subtrees contain matching files."""
    try:
        st = directory.stat()
        dir_key = (st.st_dev, st.st_ino)
    except (OSError, RuntimeError):
        return False

    cached, val = _check_visited_or_memo(dir_key, visited, memo)
    if cached:
        return val

    entries = _scan_sorted_entries(directory, memo, dir_key)
    if entries is None:
        return False

    active_visited = visited if visited is not None else set()
    active_memo = memo if memo is not None else {}
    active_visited.add(dir_key)

    try:
        result = _eval_descendants(
            entries,
            directory,
            config,
            specs,
            root_dev=root_dev,
            current_depth=current_depth,
            matcher=matcher,
            inherited_match=inherited_match,
            base_root=base_root,
            visited=active_visited,
            memo=active_memo,
        )
    finally:
        active_visited.remove(dir_key)

    active_memo[dir_key] = result
    return result


def _should_skip_dir_prune(  # noqa: PLR0913
    path: Path,
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    base_root: Path,
    root_dev: int | None,
    current_depth: int,
    matcher: PatternMatcher | None,
    inherited_match: bool,
    prune_memo: dict[tuple[int, int], bool] | None = None,
) -> bool:
    """Determine if a directory should be skipped due to empty pruning."""
    if not (config.dirs_only and config.prune_empty):
        return False

    child_specs = load_child_specs(path, specs) if config.respect_gitignore else specs
    return not has_matching_descendants(
        path,
        config,
        child_specs,
        root_dev=root_dev,
        current_depth=current_depth + 1,
        matcher=matcher,
        inherited_match=inherited_match,
        base_root=base_root,
        memo=prune_memo,
    )


def _can_skip_candidate_file(  # noqa: PLR0913
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

    is_exec: bool | None = None
    if entry is not None and (config.include_tags & INTERPRETER_TAGS):
        with contextlib.suppress(OSError, RuntimeError):
            is_exec = bool(
                entry.stat(follow_symlinks=config.follow_symlinks).st_mode & 0o111,
            )

    return can_skip_file_by_tags(path.name, config, is_executable=is_exec)


def yield_matching_items(  # noqa: PLR0913
    targets: Sequence[Path | tuple[Path, os.DirEntry[str]]],
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    base_root: Path,
    prefix: Path | None,
    root_dev: int | None,
    current_depth: int,
    matcher: PatternMatcher | None = None,
    inherited_match: bool = False,
    accumulated_sizes: dict[Path, int] | None = None,
    prune_memo: dict[tuple[int, int], bool] | None = None,
) -> Iterator[FileInfo]:
    """Yield FileInfo records for candidate paths that satisfy filters and pruning."""
    for item in targets:
        path, entry = item if isinstance(item, tuple) else (item, None)

        if _should_skip_dir_prune(
            path,
            config,
            specs,
            base_root=base_root,
            root_dev=root_dev,
            current_depth=current_depth,
            matcher=matcher,
            inherited_match=inherited_match,
            prune_memo=prune_memo,
        ):
            continue

        if not config.dirs_only and _can_skip_candidate_file(
            path,
            entry,
            config,
            base_root=base_root,
            prefix=prefix,
            matcher=matcher,
            inherited_match=inherited_match,
        ):
            continue

        accum_size = (
            accumulated_sizes.get(path, accumulated_sizes.get(path.resolve()))
            if accumulated_sizes is not None
            else None
        )
        info = classify_file(
            path,
            root_path=base_root,
            prefix=prefix,
            accumulated_size=accum_size,
            entry=entry,
        )
        if matches_filter(info, config, matcher=matcher, inherited_match=inherited_match):
            yield info
