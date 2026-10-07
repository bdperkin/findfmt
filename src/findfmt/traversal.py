"""Git-conscious directory traversal and filtering engine."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pathspec

from findfmt.classifier import classify_file

if TYPE_CHECKING:
    from collections.abc import Iterator

    from findfmt.models import FileInfo, TraversalConfig

PathSpecType = pathspec.PathSpec[Any]


def load_gitignore_spec(directory: Path) -> PathSpecType | None:
    """Load gitignore patterns from a directory if a .gitignore file exists.

    Args:
        directory: Directory to check for .gitignore.

    Returns:
        PathSpec instance if rules exist, or None.
    """
    gitignore_file = directory / ".gitignore"
    if gitignore_file.is_file():
        try:
            with gitignore_file.open("r", encoding="utf-8", errors="replace") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                if lines:
                    return pathspec.PathSpec.from_lines("gitignore", lines)
        except OSError:
            return None

    return None


def load_git_exclude_spec(root: Path) -> PathSpecType | None:
    """Load exclude patterns from .git/info/exclude if present.

    Args:
        root: Git repository root directory.

    Returns:
        PathSpec instance if exclude patterns exist, or None.
    """
    exclude_file = root / ".git" / "info" / "exclude"
    if exclude_file.is_file():
        try:
            with exclude_file.open("r", encoding="utf-8", errors="replace") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                if lines:
                    return pathspec.PathSpec.from_lines("gitignore", lines)
        except OSError:
            return None

    return None


def should_skip_dir(dir_name: str, *, include_hidden: bool) -> bool:
    """Determine if a directory should be skipped during descent.

    Args:
        dir_name: Basename of directory.
        include_hidden: Whether hidden directories are included.

    Returns:
        True if the directory should be skipped, False otherwise.
    """
    if dir_name == ".git":
        return True

    return bool(not include_hidden and dir_name.startswith("."))


def matches_filter(file_info: FileInfo, config: TraversalConfig) -> bool:
    """Determine whether a classified file satisfies traversal filter criteria.

    Args:
        file_info: The classified FileInfo object.
        config: The active TraversalConfig filter settings.

    Returns:
        True if the file satisfies all filters, False otherwise.
    """
    tags = file_info.tags

    # Check exclude tags first
    if config.exclude_tags and (tags & config.exclude_tags):
        return False

    # Check include tags
    if config.include_tags:
        if config.all_tags and not config.include_tags.issubset(tags):
            return False

        if not config.all_tags and not (tags & config.include_tags):
            return False

    # Check shebang filter
    if config.shebang_filter:
        return bool(file_info.shebang and config.shebang_filter in file_info.shebang)

    return True


def _load_active_specs(
    root: Path,
    active_specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    respect_gitignore: bool,
) -> tuple[tuple[Path, PathSpecType], ...]:
    """Assemble active gitignore specifications for a given directory."""
    if not respect_gitignore:
        return ()

    current_specs = list(active_specs)
    if not active_specs:
        git_exclude = load_git_exclude_spec(root)
        if git_exclude:
            current_specs.append((root, git_exclude))

    local_spec = load_gitignore_spec(root)
    if local_spec:
        current_specs.append((root, local_spec))

    return tuple(current_specs)


def _is_path_ignored(
    entry_path: Path,
    *,
    is_dir: bool,
    specs: tuple[tuple[Path, PathSpecType], ...],
) -> bool:
    """Check if an entry matches any active gitignore rule."""
    for base_dir, spec in specs:
        if not entry_path.is_relative_to(base_dir):
            continue

        rel = entry_path.relative_to(base_dir)
        rel_str = str(rel) + ("/" if is_dir else "")
        if spec.match_file(rel_str):
            return True

    return False


def _scan_directory_entries(
    root: Path,
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
) -> tuple[list[Path], list[Path]]:
    """Scan and partition directory entries into subdirectories and files."""
    try:
        entries = sorted(os.scandir(root), key=lambda e: e.name)
    except OSError:
        return [], []

    subdirs: list[Path] = []
    files: list[Path] = []

    for entry in entries:
        if not config.include_hidden and entry.name.startswith("."):
            continue

        entry_path = Path(entry.path)
        is_dir = entry.is_dir(follow_symlinks=config.follow_symlinks)

        if config.respect_gitignore and _is_path_ignored(entry_path, is_dir=is_dir, specs=specs):
            continue

        if is_dir:
            if not should_skip_dir(entry.name, include_hidden=config.include_hidden):
                subdirs.append(entry_path)
        elif entry.is_file(follow_symlinks=config.follow_symlinks):
            files.append(entry_path)

    return subdirs, files


def traverse_directory(
    root: Path,
    config: TraversalConfig,
    active_specs: tuple[tuple[Path, PathSpecType], ...] = (),
    base_root: Path | None = None,
) -> Iterator[FileInfo]:
    """Recursively traverse a directory hierarchy honoring .gitignore and filters.

    Args:
        root: The current directory to traverse.
        config: Traversal configuration options.
        active_specs: Inherited parent gitignore specs with their base paths.
        base_root: The top-level root directory used for relative paths.

    Yields:
        FileInfo objects for matching files in deterministic sorted order.
    """
    effective_base = base_root if base_root is not None else root
    specs = _load_active_specs(
        root,
        active_specs,
        respect_gitignore=config.respect_gitignore,
    )
    subdirs, files = _scan_directory_entries(root, config, specs)

    for file_path in files:
        info = classify_file(file_path, root_path=effective_base)
        if matches_filter(info, config):
            yield info

    for subdir in subdirs:
        yield from traverse_directory(
            subdir,
            config,
            specs,
            base_root=effective_base,
        )


def find_files(config: TraversalConfig) -> Iterator[FileInfo]:
    """Discover and classify files across all configured root paths.

    Args:
        config: Traversal and filtering configuration.

    Yields:
        FileInfo objects matching the criteria.
    """
    for root in sorted(config.root_paths):
        resolved_root = root.resolve()
        if not resolved_root.exists():
            continue

        if resolved_root.is_file():
            info = classify_file(resolved_root, root_path=resolved_root.parent)
            if matches_filter(info, config):
                yield info
        else:
            yield from traverse_directory(
                resolved_root,
                config,
                base_root=resolved_root,
            )
