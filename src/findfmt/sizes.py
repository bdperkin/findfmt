"""File size calculation, formatting, and disk usage accumulation utilities."""

from __future__ import annotations

import os
from pathlib import Path

from findfmt.i18n import format_number

__all__ = [
    "BINARY_UNITS",
    "SI_UNITS",
    "calculate_accumulated_sizes",
    "format_size",
    "format_size_binary",
    "format_size_bytes",
    "format_size_si",
]

BINARY_UNITS: tuple[str, ...] = ("B", "K", "M", "G", "T", "P", "E")
SI_UNITS: tuple[str, ...] = ("B", "kB", "MB", "GB", "TB", "PB", "EB")

_IEC_BASE = 1024
_SI_BASE = 1000

_KIB, _MIB, _GIB = 1024, 1024 * 1024, 1024 * 1024 * 1024


def format_size_bytes(size_bytes: int) -> str:
    """Format byte count into exact byte representation with unit suffix.

    Args:
        size_bytes: Size in integer bytes.

    Returns:
        Exact byte count string (e.g., '1024 B').
    """
    return f"{size_bytes} B"


def format_size_binary(size_bytes: int) -> str:
    """Format byte count using IEC binary units (powers of 1024: K, M, G, T, P, E).

    Args:
        size_bytes: Size in integer bytes.

    Returns:
        Formatted binary size string (e.g., '1.0 K', '2.5 M').
    """
    if size_bytes < _IEC_BASE:
        return f"{size_bytes} B"

    value = float(size_bytes)
    for unit in BINARY_UNITS[1:-1]:
        value /= _IEC_BASE
        if value < _IEC_BASE:
            return f"{format_number(value, 1)} {unit}"

    return f"{format_number(value / _IEC_BASE, 1)} {BINARY_UNITS[-1]}"


def format_size_si(size_bytes: int) -> str:
    """Format byte count using SI decimal metric units (powers of 1000: kB, MB, GB, TB, PB, EB).

    Args:
        size_bytes: Size in integer bytes.

    Returns:
        Formatted SI decimal size string (e.g., '1.0 kB', '2.5 MB').
    """
    if size_bytes < _SI_BASE:
        return f"{size_bytes} B"

    value = float(size_bytes)
    for unit in SI_UNITS[1:-1]:
        value /= _SI_BASE
        if value < _SI_BASE:
            return f"{format_number(value, 1)} {unit}"

    return f"{format_number(value / _SI_BASE, 1)} {SI_UNITS[-1]}"


def format_size(
    size_bytes: int,
    *,
    human_readable: bool = False,
    si: bool = False,
    exact: bool = False,
) -> str:
    """Format byte count into human-readable representation according to active flags.

    Args:
        size_bytes: File size in integer bytes.
        human_readable: Whether to format using binary units (powers of 1024: K, M, G).
        si: Whether to format using SI decimal units (powers of 1000: kB, MB, GB).
        exact: Whether to format using exact bytes.

    Returns:
        Formatted size representation string.
    """
    if si:
        return format_size_si(size_bytes)

    if human_readable:
        return format_size_binary(size_bytes)

    if exact or size_bytes < _KIB:
        return format_size_bytes(size_bytes)

    if size_bytes < _MIB:
        return f"{format_number(size_bytes / _KIB, 1)} KB"

    if size_bytes < _GIB:
        return f"{format_number(size_bytes / _MIB, 1)} MB"

    return f"{format_number(size_bytes / _GIB, 1)} GB"


def _get_root_file_size(root: Path, *, follow_symlinks: bool) -> int:
    """Return size of non-directory root path, or 0 on error."""
    try:
        st = root.stat(follow_symlinks=follow_symlinks)
    except OSError:
        return 0
    else:
        return st.st_size


def _scan_dir_entries(
    root: Path,
    *,
    follow_symlinks: bool,
    include_hidden: bool,
) -> tuple[int, list[Path]]:
    """Scan immediate child entries, returning total file size and subdirectory paths."""
    files_size = 0
    subdirs: list[Path] = []
    try:
        with os.scandir(root) as it:
            for entry in it:
                try:
                    if not include_hidden and entry.name.startswith("."):
                        continue

                    if entry.is_dir(follow_symlinks=follow_symlinks):
                        subdirs.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=follow_symlinks):
                        files_size += entry.stat(follow_symlinks=follow_symlinks).st_size
                except OSError:
                    continue
    except OSError:
        pass

    return files_size, subdirs


def calculate_accumulated_sizes(
    root: Path,
    *,
    follow_symlinks: bool = False,
    include_hidden: bool = True,
    visited: set[Path] | None = None,
) -> dict[Path, int]:
    """Calculate accumulated directory sizes recursively using post-order traversal.

    Args:
        root: Target directory path to accumulate.
        follow_symlinks: Whether to traverse directory symlinks.
        include_hidden: Whether to include hidden files and directories.
        visited: Set of visited resolved paths to detect and break symlink cycles.

    Returns:
        Dictionary mapping each directory path to its accumulated size in bytes.
    """
    active_visited = visited if visited is not None else set()
    try:
        resolved = root.resolve()
        is_directory = root.is_dir()
    except OSError:
        return {root: 0}

    if resolved in active_visited:
        return {}

    active_visited.add(resolved)
    if not is_directory:
        return {root: _get_root_file_size(root, follow_symlinks=follow_symlinks)}

    current_files_size, subdirs = _scan_dir_entries(
        root,
        follow_symlinks=follow_symlinks,
        include_hidden=include_hidden,
    )
    sizes: dict[Path, int] = {}
    subdirs_total = 0
    for subdir in subdirs:
        child_sizes = calculate_accumulated_sizes(
            subdir,
            follow_symlinks=follow_symlinks,
            include_hidden=include_hidden,
            visited=active_visited,
        )
        sizes.update(child_sizes)
        subdirs_total += child_sizes.get(subdir, 0)

    sizes[root] = current_files_size + subdirs_total
    return sizes
