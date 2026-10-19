"""Symlink cycle tracking and resolution utilities."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["init_visited_dirs", "should_skip_symlink_dir"]


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
    """Determine whether a directory should be skipped to break symlink loops."""
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
