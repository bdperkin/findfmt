"""Git directory pointer and linked-worktree commondir resolution helpers."""

from __future__ import annotations

import contextlib
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["resolve_effective_git_dir", "resolve_git_exclude_path"]


def _resolve_commondir(resolved_gitdir: Path) -> Path | None:
    """Resolve linked-worktree commondir preserving spaces and raw POSIX pathname bytes."""
    commondir_file = resolved_gitdir / "commondir"
    with contextlib.suppress(OSError, RuntimeError):
        if not commondir_file.is_file():
            return None

        raw = commondir_file.read_bytes().rstrip(b"\r\n")
        if not raw:
            return None

        decoded = os.fsdecode(raw)
        candidate = (resolved_gitdir / decoded).resolve()
        if candidate.is_dir():
            return candidate

    return None


def resolve_effective_git_dir(root: Path) -> Path | None:
    """Resolve the effective Git directory (or common directory for linked worktrees) for root."""
    git_path = root / ".git"
    with contextlib.suppress(OSError, RuntimeError):
        if git_path.is_dir():
            return git_path

        if git_path.is_file():
            content = git_path.read_text(encoding="utf-8", errors="replace").strip()
            if content.startswith("gitdir:"):
                gitdir_str = content.split(":", 1)[1].strip()
                resolved_gitdir = (root / gitdir_str).resolve()
                common_dir = _resolve_commondir(resolved_gitdir)
                return common_dir if common_dir is not None else resolved_gitdir

    return None


def resolve_git_exclude_path(root: Path) -> Path | None:
    """Locate the active info/exclude path for a repository, submodule, or linked worktree."""
    effective_dir = resolve_effective_git_dir(root)
    return (effective_dir / "info" / "exclude") if effective_dir is not None else None
