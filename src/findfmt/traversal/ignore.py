"""Git ignore specifications and ancestor repository discovery engine."""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pathspec

if TYPE_CHECKING:
    PathSpecType = pathspec.PathSpec[Any]
else:
    PathSpecType = Any

__all__ = [
    "PathSpecType",
    "find_git_repo_root",
    "find_global_gitignore_path",
    "is_path_ignored",
    "load_ancestor_specs",
    "load_child_specs",
    "load_custom_gitignore_spec",
    "load_git_exclude_spec",
    "load_gitignore_spec",
    "load_global_gitignore_spec",
    "load_spec_file",
    "resolve_active_specs",
]


def _trim_gitignore_line(raw_line: str) -> str:
    r"""Trim gitignore pattern line preserving significant leading and escaped trailing spaces.

    According to the Gitignore specification, trailing spaces are ignored unless
    escaped with a backslash. Leading spaces are significant and must be preserved.
    Carriage returns (\r) and newlines (\n) are trimmed.

    Args:
        raw_line: Raw line read from a gitignore file.

    Returns:
        Trimmed pattern line.
    """
    line = raw_line.rstrip("\r\n")
    while line.endswith(" "):
        num_slashes = 0
        idx = len(line) - 2
        while idx >= 0 and line[idx] == "\\":
            num_slashes += 1
            idx -= 1

        if num_slashes % 2 == 1:
            break

        line = line[:-1]

    return line


def load_spec_file(spec_file: Path) -> PathSpecType | None:
    """Load and compile pathspec patterns from a specification file."""
    try:
        if not spec_file.is_file():
            return None

        with spec_file.open("r", encoding="utf-8", errors="replace") as f:
            lines: list[str] = []
            for raw_line in f:
                line = _trim_gitignore_line(raw_line)
                if line.strip() and not line.startswith("#"):
                    lines.append(line)

            return pathspec.PathSpec.from_lines("gitignore", lines) if lines else None
    except (OSError, ValueError, re.error):
        return None


def _find_git_config_excludes_file() -> Path | None:
    """Find core.excludesFile from git config if available and existing."""
    git_path = shutil.which("git")
    if not git_path:
        return None

    try:
        proc = subprocess.run(  # noqa: S603
            [git_path, "config", "--get", "core.excludesFile"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            configured = Path(proc.stdout.strip()).expanduser()
            return configured if configured.is_file() else None
    except (OSError, subprocess.SubprocessError):
        pass

    return None


def _find_standard_global_gitignore() -> Path | None:
    """Find global gitignore from standard XDG or home directory paths."""
    xdg_env = os.environ.get("XDG_CONFIG_HOME")
    if xdg_env:
        xdg_path = Path(xdg_env) / "git" / "ignore"
        if xdg_path.is_file():
            return xdg_path
    else:
        with contextlib.suppress(OSError, RuntimeError):
            xdg_path = Path.home() / ".config" / "git" / "ignore"
            if xdg_path.is_file():
                return xdg_path

    with contextlib.suppress(OSError, RuntimeError):
        legacy_path = Path.home() / ".gitignore"
        if legacy_path.is_file():
            return legacy_path

    return None


def find_global_gitignore_path() -> Path | None:
    """Find path to user's global gitignore file from git config or standard paths."""
    return _find_git_config_excludes_file() or _find_standard_global_gitignore()


def load_global_gitignore_spec(spec_file: Path | None = None) -> PathSpecType | None:
    """Load global gitignore patterns from git config or standard user paths."""
    path = spec_file if spec_file is not None else find_global_gitignore_path()
    return load_spec_file(path) if path is not None else None


def load_custom_gitignore_spec(path: Path | str | None) -> PathSpecType | None:
    """Load custom gitignore patterns from an external specification file."""
    if path is None:
        return None

    return load_spec_file(Path(path).expanduser())


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
    with contextlib.suppress(OSError, RuntimeError):
        if git_path.is_dir():
            return load_spec_file(git_path / "info" / "exclude")

        if git_path.is_file():
            content = git_path.read_text(encoding="utf-8", errors="replace").strip()
            if content.startswith("gitdir:"):
                gitdir_str = content.split(":", 1)[1].strip()
                return load_spec_file((root / gitdir_str).resolve() / "info" / "exclude")

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
    except (OSError, RuntimeError):
        resolved = start_dir

    for directory in (resolved, *resolved.parents):
        with contextlib.suppress(OSError, RuntimeError):
            if (directory / ".git").exists():
                return directory

    return None


def _collect_ancestor_dirs(resolved: Path, git_root: Path | None) -> list[Path]:
    """Collect ancestor directories from resolved path up to git root."""
    ancestors = [resolved]
    for parent in resolved.parents:
        ancestors.append(parent)
        if git_root is not None and parent == git_root:
            break

    ancestors.reverse()
    return ancestors


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
    except (OSError, RuntimeError):
        resolved = root

    git_root = find_git_repo_root(resolved)
    ancestors = _collect_ancestor_dirs(resolved, git_root)

    specs: list[tuple[Path, PathSpecType]] = []
    global_spec = load_global_gitignore_spec()
    if global_spec:
        base_dir = git_root if git_root is not None else resolved
        specs.append((base_dir, global_spec))

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
    except (OSError, RuntimeError):
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
    if not specs:
        return False

    entry_str = entry_path.as_posix()
    for base_dir, spec in reversed(specs):
        base_str = base_dir.as_posix()
        prefix = base_str if base_str.endswith("/") else base_str + "/"
        if entry_str.startswith(prefix):
            rel_str = entry_str[len(prefix) :]
        elif entry_str == base_str:
            rel_str = ""
        else:
            continue

        target_str = (rel_str + "/") if is_dir else rel_str
        check = spec.check_file(target_str)
        if check.include is not None:
            return bool(check.include)

    return False


def resolve_active_specs(
    root: Path,
    active_specs: tuple[tuple[Path, PathSpecType], ...] | None,
    *,
    respect_gitignore: bool,
    gitignore_file: Path | None = None,
) -> tuple[tuple[Path, PathSpecType], ...]:
    """Resolve active gitignore specifications for current traversal frame."""
    if active_specs is not None:
        return active_specs

    specs: list[tuple[Path, PathSpecType]] = []
    if respect_gitignore:
        specs.extend(load_ancestor_specs(root))

    if gitignore_file is not None and (custom_spec := load_custom_gitignore_spec(gitignore_file)):
        specs.append((root, custom_spec))

    return tuple(specs)
