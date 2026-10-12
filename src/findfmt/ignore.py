"""Git ignore specifications and ancestor repository discovery engine."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import pathspec

if TYPE_CHECKING:
    from pathlib import Path

    PathSpecType = pathspec.PathSpec[Any]
else:
    PathSpecType = Any


def load_spec_file(spec_file: Path) -> PathSpecType | None:
    """Load and compile pathspec patterns from a specification file."""
    try:
        if not spec_file.is_file():
            return None

        with spec_file.open("r", encoding="utf-8", errors="replace") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            return pathspec.PathSpec.from_lines("gitignore", lines) if lines else None
    except (OSError, ValueError, re.error):
        return None


def load_gitignore_spec(directory: Path) -> PathSpecType | None:
    """Load gitignore patterns from a directory if a .gitignore file exists.

    Args:
        directory: Directory to check for .gitignore.

    Returns:
        PathSpec instance if rules exist, or None.
    """
    return load_spec_file(directory / ".gitignore")


def load_git_exclude_spec(root: Path) -> PathSpecType | None:
    """Load exclude patterns from .git/info/exclude if present.

    Supports both standard Git repositories with a .git directory and
    submodules or worktrees with a .git pointer file.

    Args:
        root: Git repository root directory.

    Returns:
        PathSpec instance if exclude patterns exist, or None.
    """
    git_path = root / ".git"
    try:
        if git_path.is_dir():
            return load_spec_file(git_path / "info" / "exclude")

        if git_path.is_file():
            content = git_path.read_text(encoding="utf-8", errors="replace").strip()
            if content.startswith("gitdir:"):
                gitdir_str = content.split(":", 1)[1].strip()
                gitdir = (root / gitdir_str).resolve()
                return load_spec_file(gitdir / "info" / "exclude")
    except OSError:
        return None

    return None


def find_git_repo_root(start_dir: Path) -> Path | None:
    """Find the enclosing Git repository root for a directory.

    Searches upward from start_dir to locate the nearest ancestor directory
    containing a .git directory or file.

    Args:
        start_dir: Directory to start searching upwards from.

    Returns:
        Path to the repository root, or None if not inside a Git repository.
    """
    try:
        resolved = start_dir.resolve()
    except OSError:
        resolved = start_dir

    for directory in (resolved, *resolved.parents):
        git_marker = directory / ".git"
        try:
            if git_marker.exists():
                return directory
        except OSError:
            continue

    return None


def load_ancestor_specs(root: Path) -> tuple[tuple[Path, PathSpecType], ...]:
    """Discover and compile ancestor .gitignore and .git/info/exclude specifications.

    Traverses upward from root to find enclosing Git repository root or filesystem root,
    and collects specs in hierarchical order (shallowest to deepest).

    Args:
        root: Target directory being traversed.

    Returns:
        Tuple of (base_directory, compiled_spec) pairs.
    """
    try:
        resolved = root.resolve()
    except OSError:
        resolved = root

    git_root = find_git_repo_root(resolved)

    ancestors = [resolved]
    for parent in resolved.parents:
        ancestors.append(parent)
        if git_root is not None and parent == git_root:
            break

    ancestors.reverse()

    specs: list[tuple[Path, PathSpecType]] = []
    if git_root is not None:
        git_exclude = load_git_exclude_spec(git_root)
        if git_exclude:
            specs.append((git_root, git_exclude))

    for directory in ancestors:
        spec = load_gitignore_spec(directory)
        if spec:
            specs.append((directory, spec))

    return tuple(specs)


def load_child_specs(
    child_dir: Path,
    active_specs: tuple[tuple[Path, PathSpecType], ...],
) -> tuple[tuple[Path, PathSpecType], ...]:
    """Load additional specs for a child directory during downward descent.

    Checks for nested Git repository or submodule exclude files and local .gitignore.

    Args:
        child_dir: Child directory being entered.
        active_specs: Current active specs from parent directory.

    Returns:
        Updated tuple of active specs including any newly discovered specs.
    """
    new_specs: list[tuple[Path, PathSpecType]] = []

    git_marker = child_dir / ".git"
    try:
        is_nested_repo = git_marker.exists()
    except OSError:
        is_nested_repo = False

    if is_nested_repo:
        git_exclude = load_git_exclude_spec(child_dir)
        if git_exclude:
            new_specs.append((child_dir, git_exclude))

    local_spec = load_gitignore_spec(child_dir)
    if local_spec:
        new_specs.append((child_dir, local_spec))

    if new_specs:
        return (*active_specs, *new_specs)

    return active_specs


def is_path_ignored(
    entry_path: Path,
    *,
    is_dir: bool,
    specs: tuple[tuple[Path, PathSpecType], ...],
) -> bool:
    """Check if an entry matches any active gitignore rule.

    Evaluates specs in reverse hierarchical order (deepest to shallowest).

    Args:
        entry_path: Path of the directory or file entry to test.
        is_dir: Whether the entry is a directory.
        specs: Active (base_path, spec) pairs.

    Returns:
        True if the entry is ignored, False otherwise.
    """
    for base_dir, spec in reversed(specs):
        if not entry_path.is_relative_to(base_dir):
            continue

        rel = entry_path.relative_to(base_dir)
        rel_str = rel.as_posix() + ("/" if is_dir else "")
        check = spec.check_file(rel_str)
        if check.include is not None:
            return bool(check.include)

    return False
