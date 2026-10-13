"""Core directory traversal routines with .gitignore and boundaries integration."""

from __future__ import annotations

import os
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Any

from findfmt.classifier import classify_file, compute_relative_prefix
from findfmt.traversal.boundaries import (
    check_depth_limit,
    check_file_limit,
    filter_directory_entry,
    has_matching_descendants,
    init_visited_dirs,
    matches_filter,
    resolve_active_specs,
    resolve_device,
    should_skip_dir,
    should_skip_symlink_dir,
    yield_matching_items,
)
from findfmt.traversal.ignore import (
    is_path_ignored,
    load_ancestor_specs,
    load_child_specs,
    load_custom_gitignore_spec,
    load_git_exclude_spec,
    load_gitignore_spec,
    load_global_gitignore_spec,
    load_spec_file,
)
from findfmt.traversal.patterns import create_pattern_matcher

if TYPE_CHECKING:
    from collections.abc import Iterator

    import pathspec

    from findfmt.models import FileInfo, TraversalConfig
    from findfmt.traversal.patterns import PatternMatcher

    PathSpecType = pathspec.PathSpec[Any]
else:
    PathSpecType = Any

_load_spec_file = load_spec_file
_is_path_ignored = is_path_ignored

__all__ = [
    "find_files",
    "load_custom_gitignore_spec",
    "load_git_exclude_spec",
    "load_gitignore_spec",
    "load_global_gitignore_spec",
    "matches_filter",
    "should_skip_dir",
    "traverse_directory",
]


def _load_active_specs(
    root: Path,
    active_specs: tuple[tuple[Path, PathSpecType], ...] | None,
    *,
    respect_gitignore: bool,
) -> tuple[tuple[Path, PathSpecType], ...]:
    """Load active gitignore specs for a directory from parent or ancestors."""
    if not respect_gitignore:
        return ()

    if not active_specs:
        return load_ancestor_specs(root)

    return load_child_specs(root, active_specs)


def _scan_directory_entries(  # noqa: PLR0913
    root: Path,
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    root_dev: int | None = None,
    matcher: PatternMatcher | None = None,
    base_root: Path | None = None,
) -> tuple[list[Path], list[Path]]:
    """Scan and partition directory entries into subdirectories and files."""
    try:
        entries = sorted(os.scandir(root), key=lambda e: e.name)
    except OSError:
        return [], []

    if not check_file_limit(len(entries), config.file_limit):
        return [], []

    subdirs: list[Path] = []
    files: list[Path] = []

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
            files.append(entry_path)

    return subdirs, files


_should_skip_symlink_dir = should_skip_symlink_dir
_init_visited_dirs = init_visited_dirs
_resolve_active_specs = resolve_active_specs


def traverse_directory(  # noqa: PLR0913
    root: Path,
    config: TraversalConfig,
    active_specs: tuple[tuple[Path, PathSpecType], ...] | None = None,
    *,
    base_root: Path | None = None,
    visited_dirs: set[Path] | None = None,
    prefix: Path | None = None,
    root_dev: int | None = None,
    current_depth: int = 1,
    matcher: PatternMatcher | None = None,
    inherited_match: bool = False,
) -> Iterator[FileInfo]:
    """Recursively traverse a directory hierarchy honoring .gitignore, filters, and boundaries."""
    effective_base = base_root if base_root is not None else root
    active_matcher = matcher if matcher is not None else create_pattern_matcher(config)
    effective_dev = resolve_device(
        root,
        one_file_system=config.one_file_system,
        root_dev=root_dev,
    )
    active_visited = _init_visited_dirs(
        root,
        follow_symlinks=config.follow_symlinks,
        visited=visited_dirs,
    )
    specs = _resolve_active_specs(
        root,
        active_specs,
        respect_gitignore=config.respect_gitignore,
        gitignore_file=config.gitignore_file,
    )

    subdirs, files = _scan_directory_entries(
        root,
        config,
        specs,
        root_dev=effective_dev,
        matcher=active_matcher,
        base_root=effective_base,
    )

    targets = subdirs if config.dirs_only else files
    yield from yield_matching_items(
        targets,
        config,
        specs,
        base_root=effective_base,
        prefix=prefix,
        root_dev=effective_dev,
        current_depth=current_depth,
        matcher=active_matcher,
        inherited_match=inherited_match,
    )

    if not check_depth_limit(current_depth, config.max_depth):
        return

    for subdir in subdirs:
        child_specs = load_child_specs(subdir, specs) if config.respect_gitignore else specs
        child_inherit = active_matcher.should_inherit_match(
            subdir,
            base_root=effective_base,
            parent_inherited=inherited_match,
        )
        if config.prune_empty and not has_matching_descendants(
            subdir,
            config,
            child_specs,
            root_dev=effective_dev,
            current_depth=current_depth + 1,
            matcher=active_matcher,
            inherited_match=child_inherit,
            base_root=effective_base,
        ):
            continue

        if _should_skip_symlink_dir(
            subdir,
            follow_symlinks=config.follow_symlinks,
            visited=active_visited,
        ):
            continue

        yield from traverse_directory(
            subdir,
            config,
            active_specs=child_specs,
            base_root=effective_base,
            visited_dirs=active_visited,
            prefix=prefix,
            root_dev=effective_dev,
            current_depth=current_depth + 1,
            matcher=active_matcher,
            inherited_match=child_inherit,
        )


def find_files(config: TraversalConfig) -> Iterator[FileInfo]:
    """Discover and classify files across all configured root paths."""
    matcher = create_pattern_matcher(config)
    for root in sorted(config.root_paths):
        resolved_root = root.resolve()
        if not resolved_root.exists():
            continue

        if resolved_root.is_file():
            if config.dirs_only:
                continue

            prefix = compute_relative_prefix(root.parent) if config.relative_prefix else None
            info = classify_file(resolved_root, root_path=resolved_root.parent, prefix=prefix)
            if matches_filter(info, config, matcher=matcher):
                yield info
        else:
            prefix = compute_relative_prefix(root) if config.relative_prefix else None
            yield from traverse_directory(
                resolved_root,
                config,
                base_root=resolved_root,
                prefix=prefix,
                matcher=matcher,
            )
