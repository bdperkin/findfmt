"""Directory traversal boundaries and pruning evaluation engine."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from findfmt.classifier import classify_file
from findfmt.traversal._pruning import (
    _can_skip_candidate_file,
    _can_skip_entry_by_tags,
    _check_visited_or_memo,
    _PruneFrame,
    _scan_sorted_entries,
    check_depth_limit,
    check_file_limit,
    is_candidate_file_entry,
    should_skip_dir,
)
from findfmt.traversal.devices import check_device_boundary, resolve_device
from findfmt.traversal.filters import matches_filter
from findfmt.traversal.ignore import (
    is_path_ignored,
    load_child_specs,
    resolve_active_specs,
)
from findfmt.traversal.symlinks import init_visited_dirs, should_skip_symlink_dir
from findfmt.traversal.tags import can_skip_file_by_tags

if TYPE_CHECKING:
    import os
    from collections.abc import Callable, Iterator, Sequence

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
    "is_candidate_file_entry",
    "matches_filter",
    "resolve_active_specs",
    "resolve_device",
    "should_skip_dir",
    "should_skip_symlink_dir",
    "yield_matching_items",
]


def _is_entry_excluded(  # noqa: PLR0913 - wide CLI/config signature
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


def filter_directory_entry(  # noqa: PLR0913 - wide CLI/config signature
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
    if root_dev is not None and not check_device_boundary(
        entry_path,
        root_dev,
        entry=entry,
        follow_symlinks=config.follow_symlinks,
    ):
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


def _inspect_entries(  # noqa: PLR0913 - wide CLI/config signature
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
        elif is_candidate_file_entry(entry, follow_symlinks=config.follow_symlinks):
            if _can_skip_entry_by_tags(entry, config, filename=entry.name):
                continue

            info = classify_file(
                entry_path,
                entry=entry,
                follow_symlinks=config.follow_symlinks,
            )
            if matches_filter(info, config, matcher=matcher, inherited_match=inherited_match):
                return [], True

    return subdirs, False


def _step_prune_directory(  # noqa: PLR0913 - wide CLI/config signature
    directory: Path,
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    root_dev: int | None,
    current_depth: int,
    matcher: PatternMatcher | None,
    inherited_match: bool,
    base_root: Path | None,
    active_visited: set[tuple[int, int]],
    active_memo: dict[tuple[int, int], bool],
    stack: list[_PruneFrame],
    on_error: Callable[[OSError], None] | None = None,
) -> bool:
    """Inspect a single directory for matching files or push its subdirs onto stack."""
    try:
        st = directory.stat()
        dir_key = (st.st_dev, st.st_ino)
    except (OSError, RuntimeError):
        return False

    cached, val = _check_visited_or_memo(dir_key, active_visited, active_memo)
    if cached:
        return val

    entries = _scan_sorted_entries(directory, active_memo, dir_key, on_error=on_error)
    if entries is None:
        return False

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
        active_memo[dir_key] = True
        return True

    if not check_depth_limit(current_depth, config.max_depth) or not subdirs:
        active_memo[dir_key] = False
        return False

    active_visited.add(dir_key)
    effective_root = base_root if base_root is not None else directory
    stack.append(
        _PruneFrame(
            dir_key=dir_key,
            subdirs=subdirs,
            specs=specs,
            depth=current_depth,
            inherited_match=inherited_match,
            effective_root=effective_root,
        ),
    )
    return False


def _step_prune_subdir(  # noqa: PLR0913 - wide CLI/config signature
    top: _PruneFrame,
    config: TraversalConfig,
    *,
    root_dev: int | None,
    matcher: PatternMatcher | None,
    active_visited: set[tuple[int, int]],
    active_memo: dict[tuple[int, int], bool],
    stack: list[_PruneFrame],
    on_error: Callable[[OSError], None] | None = None,
) -> bool:
    """Advance top prune frame by one subdirectory and return True on immediate match."""
    subdir = top.subdirs[top.idx]
    top.idx += 1
    child_specs = load_child_specs(subdir, top.specs) if config.respect_gitignore else top.specs
    child_inherit = bool(
        matcher
        and matcher.should_inherit_match(
            subdir,
            base_root=top.effective_root,
            parent_inherited=top.inherited_match,
        ),
    )
    return _step_prune_directory(
        subdir,
        config,
        child_specs,
        root_dev=root_dev,
        current_depth=top.depth + 1,
        matcher=matcher,
        inherited_match=child_inherit,
        base_root=top.effective_root,
        active_visited=active_visited,
        active_memo=active_memo,
        stack=stack,
        on_error=on_error,
    )


def has_matching_descendants(  # noqa: PLR0913 - wide CLI/config signature
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
    on_error: Callable[[OSError], None] | None = None,
) -> bool:
    """Determine whether a directory or any subtrees contain matching files."""
    active_visited = visited if visited is not None else set()
    active_memo = memo if memo is not None else {}
    stack: list[_PruneFrame] = []

    if _step_prune_directory(
        directory,
        config,
        specs,
        root_dev=root_dev,
        current_depth=current_depth,
        matcher=matcher,
        inherited_match=inherited_match,
        base_root=base_root,
        active_visited=active_visited,
        active_memo=active_memo,
        stack=stack,
        on_error=on_error,
    ):
        return True

    try:
        while stack:
            top = stack[-1]
            if top.idx >= len(top.subdirs):
                stack.pop()
                active_visited.discard(top.dir_key)
                active_memo[top.dir_key] = False
            elif _step_prune_subdir(
                top,
                config,
                root_dev=root_dev,
                matcher=matcher,
                active_visited=active_visited,
                active_memo=active_memo,
                stack=stack,
                on_error=on_error,
            ):
                for frame in stack:
                    active_memo[frame.dir_key] = True

                return True
    finally:
        for frame in stack:
            active_visited.discard(frame.dir_key)

    return False


def _should_skip_dir_prune(  # noqa: PLR0913 - wide CLI/config signature
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
    on_error: Callable[[OSError], None] | None = None,
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
        on_error=on_error,
    )


def yield_matching_items(  # noqa: PLR0913 - wide CLI/config signature
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
    on_error: Callable[[OSError], None] | None = None,
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
            on_error=on_error,
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

        accum_size = accumulated_sizes.get(path) if accumulated_sizes is not None else None
        info = classify_file(
            path,
            root_path=base_root,
            prefix=prefix,
            accumulated_size=accum_size,
            entry=entry,
            follow_symlinks=config.follow_symlinks,
        )
        if matches_filter(info, config, matcher=matcher, inherited_match=inherited_match):
            yield info
