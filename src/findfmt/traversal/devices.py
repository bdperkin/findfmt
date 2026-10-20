"""Filesystem device boundary resolution and validation utilities."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["check_device_boundary", "resolve_device"]


def check_device_boundary(path: Path, root_dev: int | None) -> bool:
    """Check whether a path resides on the designated root filesystem device."""
    with contextlib.suppress(OSError):
        return root_dev is None or path.stat().st_dev == root_dev

    return False


def resolve_device(root: Path, *, one_file_system: bool, root_dev: int | None) -> int | None:
    """Resolve the active filesystem device identifier for traversal."""
    if one_file_system:
        with contextlib.suppress(OSError):
            return root_dev if root_dev is not None else root.stat().st_dev

    return None
