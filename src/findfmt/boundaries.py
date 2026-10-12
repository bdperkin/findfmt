"""Directory traversal boundaries and pruning evaluation engine."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from findfmt.classifier import classify_file
from findfmt.ignore import is_path_ignored, load_ancestor_specs, load_child_specs

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    import pathspec

    from findfmt.models import FileInfo, TraversalConfig

    PathSpecType = pathspec.PathSpec[Any]
else:
    PathSpecType = Any


def init_visited_dirs(
    root: Path,
    *,
    follow_symlinks: bool,
    visited: set[Path] | None,
) -> set[Path] | None:
    """Initialize or reuse the tracking set for visited directories."""
    if not follow_symlinks or visited is not None:
        return visited

    active = set()
    with contextlib.suppress(OSError):
        active.add(root.resolve())

    return active


def should_skip_symlink_dir(
    subdir: Path,
    *,
    follow_symlinks: bool,
    visited: set[Path] | None,
) -> bool:
    """Determine whether a candidate directory should be skipped to break symlink loops.

    Args:
        subdir: Directory path candidate.
        follow_symlinks: Traversal configuration flag for following symlinks.
        visited: Set of canonical directory paths already visited.

    Returns:
        True if the directory should be skipped, False otherwise.
    """
    if not (follow_symlinks and visited is not None):
        return False

    try:
        resolved = subdir.resolve()
    except OSError:
        return True

    if resolved in visited:
        return True

    visited.add(resolved)
    return False


def resolve_active_specs(
    root: Path,
    active_specs: tuple[tuple[Path, PathSpecType], ...] | None,
    *,
    respect_gitignore: bool,
) -> tuple[tuple[Path, PathSpecType], ...]:
    """Resolve active gitignore specifications for the current traversal frame."""
    if not respect_gitignore:
        return ()

    if active_specs is None:
        return load_ancestor_specs(root)

    return active_specs


def check_device_boundary(path: Path, root_dev: int | None) -> bool:
    """Check whether a path resides on the designated root filesystem device."""
    if root_dev is None:
        return True

    try:
        return path.stat().st_dev == root_dev
    except OSError:
        return False


def resolve_device(root: Path, *, one_file_system: bool, root_dev: int | None) -> int | None:
    """Resolve the active filesystem device identifier for traversal."""
    if not one_file_system:
        return None

    if root_dev is not None:
        return root_dev

    try:
        return root.stat().st_dev
    except OSError:
        return None


def check_file_limit(count: int, file_limit: int | None) -> bool:
    """Verify whether a directory entry count does not exceed the filelimit threshold."""
    if file_limit is None:
        return True

    return count <= file_limit


def check_depth_limit(current_depth: int, max_depth: int | None) -> bool:
    """Determine whether traversal can descend further based on maximum depth."""
    if max_depth is None:
        return True

    return current_depth < max_depth


def should_skip_dir(dir_name: str, *, include_hidden: bool) -> bool:
    """Determine if a directory should be skipped during descent."""
    if dir_name == ".git":
        return True

    return bool(not include_hidden and dir_name.startswith("."))


def matches_filter(file_info: FileInfo, config: TraversalConfig) -> bool:
    """Determine whether a classified file satisfies traversal filter criteria."""
    tags = file_info.tags
    if config.exclude_tags and (tags & config.exclude_tags):
        return False

    if config.include_tags:
        if config.all_tags and not config.include_tags.issubset(tags):
            return False

        if not config.all_tags and not (tags & config.include_tags):
            return False

    if config.shebang_filter:
        return bool(file_info.shebang and config.shebang_filter in file_info.shebang)

    return True


def filter_directory_entry(
    entry: os.DirEntry[str],
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    root_dev: int | None,
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

    return entry_path, is_dir


def _inspect_entries(
    entries: Sequence[os.DirEntry[str]],
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    root_dev: int | None,
) -> tuple[list[Path], bool]:
    """Inspect directory entries and return discovered subdirs or immediate match flag."""
    subdirs: list[Path] = []
    for entry in entries:
        filtered = filter_directory_entry(entry, config, specs, root_dev)
        if filtered is None:
            continue

        entry_path, is_dir = filtered
        if is_dir:
            if not should_skip_dir(entry.name, include_hidden=config.include_hidden):
                subdirs.append(entry_path)
        elif entry.is_file(follow_symlinks=config.follow_symlinks):
            info = classify_file(entry_path)
            if matches_filter(info, config):
                return [], True

    return subdirs, False


def has_matching_descendants(
    directory: Path,
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    root_dev: int | None = None,
    current_depth: int = 1,
) -> bool:
    """Determine whether a directory or any of its subtrees contain matching files.

    Args:
        directory: Directory to inspect.
        config: Traversal and filter configuration.
        specs: Active gitignore specifications.
        root_dev: Optional filesystem device identifier.
        current_depth: Current depth level.

    Returns:
        True if at least one matching file exists in directory or subtrees.
    """
    try:
        entries = sorted(os.scandir(directory), key=lambda e: e.name)
    except OSError:
        return False

    subdirs, found = _inspect_entries(entries, config, specs, root_dev)
    if found:
        return True

    if not check_depth_limit(current_depth, config.max_depth):
        return False

    for subdir in subdirs:
        child_specs = load_child_specs(subdir, specs) if config.respect_gitignore else ()
        if has_matching_descendants(
            subdir,
            config,
            child_specs,
            root_dev=root_dev,
            current_depth=current_depth + 1,
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
) -> Iterator[FileInfo]:
    """Yield FileInfo records for candidate paths that satisfy filters and pruning.

    Args:
        targets: Candidate file or directory paths to evaluate.
        config: Traversal and filter settings.
        specs: Active gitignore specifications.
        base_root: Root directory used for relative paths.
        prefix: Optional prefix for relative paths.
        root_dev: Optional filesystem device number.
        current_depth: Current traversal depth.

    Yields:
        Classified FileInfo instances that satisfy all filters.
    """
    for path in targets:
        if config.dirs_only:
            if config.prune_empty:
                child_specs = load_child_specs(path, specs) if config.respect_gitignore else ()
                if not has_matching_descendants(
                    path,
                    config,
                    child_specs,
                    root_dev=root_dev,
                    current_depth=current_depth + 1,
                ):
                    continue

            yield classify_file(path, root_path=base_root, prefix=prefix)
        else:
            info = classify_file(path, root_path=base_root, prefix=prefix)
            if matches_filter(info, config):
                yield info
