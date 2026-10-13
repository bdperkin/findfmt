"""Directory traversal boundaries and pruning evaluation engine."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from findfmt.classifier import classify_file
from findfmt.traversal.ignore import (
    is_path_ignored,
    load_ancestor_specs,
    load_child_specs,
)
from findfmt.traversal.patterns import matches_pattern_criteria
from findfmt.traversal.symlinks import init_visited_dirs, should_skip_symlink_dir

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    import pathspec

    from findfmt.models import FileInfo, TraversalConfig
    from findfmt.traversal.patterns import PatternMatcher

    PathSpecType = pathspec.PathSpec[Any]
else:
    PathSpecType = Any

__all__ = [
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


def resolve_active_specs(
    root: Path,
    active_specs: tuple[tuple[Path, PathSpecType], ...] | None,
    *,
    respect_gitignore: bool,
) -> tuple[tuple[Path, PathSpecType], ...]:
    """Resolve active gitignore specifications for current traversal frame."""
    if not respect_gitignore:
        return ()

    return active_specs if active_specs is not None else load_ancestor_specs(root)


def check_device_boundary(path: Path, root_dev: int | None) -> bool:
    """Check whether a path resides on the designated root filesystem device."""
    with contextlib.suppress(OSError):
        return root_dev is None or path.stat().st_dev == root_dev

    return False


def resolve_device(root: Path, *, one_file_system: bool, root_dev: int | None) -> int | None:
    """Resolve the active filesystem device identifier for traversal."""
    if not one_file_system:
        return None

    with contextlib.suppress(OSError):
        return root_dev if root_dev is not None else root.stat().st_dev

    return None


def check_file_limit(count: int, file_limit: int | None) -> bool:
    """Verify whether directory entry count does not exceed filelimit threshold."""
    return file_limit is None or count <= file_limit


def check_depth_limit(current_depth: int, max_depth: int | None) -> bool:
    """Determine whether traversal can descend further based on maximum depth."""
    return max_depth is None or current_depth < max_depth


def should_skip_dir(dir_name: str, *, include_hidden: bool) -> bool:
    """Determine if a directory should be skipped during descent."""
    return dir_name == ".git" or bool(not include_hidden and dir_name.startswith("."))


def _matches_shebang(shebang: str | None, filter_str: str | None) -> bool:
    """Check if file shebang satisfies the shebang filter criteria."""
    return not filter_str or bool(shebang and filter_str in shebang)


def _matches_tags(tags: frozenset[str], config: TraversalConfig) -> bool:
    """Check if file tags satisfy inclusion and exclusion criteria."""
    if config.exclude_tags and (tags & config.exclude_tags):
        return False

    if not config.include_tags:
        return True

    if config.all_tags:
        return config.include_tags.issubset(tags)

    return bool(tags & config.include_tags)


def matches_filter(
    file_info: FileInfo,
    config: TraversalConfig,
    *,
    matcher: PatternMatcher | None = None,
    inherited_match: bool = False,
) -> bool:
    """Determine whether a classified file satisfies filter criteria."""
    if not file_info.path.is_dir():
        if not _matches_tags(file_info.tags, config):
            return False

        if not _matches_shebang(file_info.shebang, config.shebang_filter):
            return False

    return matches_pattern_criteria(
        file_info,
        config,
        matcher=matcher,
        inherited_match=inherited_match,
    )


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
    if not check_device_boundary(entry_path, root_dev):
        return None

    is_dir = entry.is_dir(follow_symlinks=config.follow_symlinks)
    if config.respect_gitignore and is_path_ignored(entry_path, is_dir=is_dir, specs=specs):
        return None

    if matcher and matcher.should_exclude(entry_path, is_dir=is_dir, base_root=base_root):
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
        elif entry.is_file(follow_symlinks=config.follow_symlinks):
            info = classify_file(entry_path)
            if matches_filter(info, config, matcher=matcher, inherited_match=inherited_match):
                return [], True

    return subdirs, False


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
) -> bool:
    """Determine whether a directory or any subtrees contain matching files."""
    try:
        entries = sorted(os.scandir(directory), key=lambda e: e.name)
    except OSError:
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
        return True

    if not check_depth_limit(current_depth, config.max_depth):
        return False

    effective_root = base_root if base_root is not None else directory
    for subdir in subdirs:
        child_specs = load_child_specs(subdir, specs) if config.respect_gitignore else ()
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
        ):
            return True

    return False


def yield_matching_items(  # noqa: PLR0913
    targets: list[Path],
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    base_root: Path,
    prefix: Path | None,
    root_dev: int | None,
    current_depth: int,
    matcher: PatternMatcher | None = None,
    inherited_match: bool = False,
) -> Iterator[FileInfo]:
    """Yield FileInfo records for candidate paths that satisfy filters and pruning."""
    for path in targets:
        if config.dirs_only and config.prune_empty:
            child_specs = load_child_specs(path, specs) if config.respect_gitignore else ()
            if not has_matching_descendants(
                path,
                config,
                child_specs,
                root_dev=root_dev,
                current_depth=current_depth + 1,
                matcher=matcher,
                inherited_match=inherited_match,
                base_root=base_root,
            ):
                continue

        info = classify_file(path, root_path=base_root, prefix=prefix)
        if matches_filter(info, config, matcher=matcher, inherited_match=inherited_match):
            yield info
