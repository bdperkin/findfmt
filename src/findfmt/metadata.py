"""POSIX filesystem metadata extraction and caching utilities."""

from __future__ import annotations

import functools
import stat
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import os

    from findfmt.models import FileInfo

try:
    import pwd
except ImportError:  # pragma: no cover
    pwd = None  # type: ignore[assignment]

try:
    import grp
except ImportError:  # pragma: no cover
    grp = None  # type: ignore[assignment]

__all__ = [
    "clear_metadata_cache",
    "extract_metadata",
    "format_metadata_parts",
    "format_permissions",
    "resolve_group_name",
    "resolve_user_name",
]


def format_metadata_parts(  # noqa: PLR0913
    file_info: FileInfo,
    *,
    show_inodes: bool = False,
    show_device: bool = False,
    show_permissions: bool = False,
    show_user: bool = False,
    show_group: bool = False,
) -> list[str]:
    """Format active POSIX metadata fields into string representations.

    Args:
        file_info: FileInfo instance containing metadata.
        show_inodes: Whether to include inode number.
        show_device: Whether to include device number.
        show_permissions: Whether to include permissions string.
        show_user: Whether to include owner username.
        show_group: Whether to include owner group name.

    Returns:
        List of formatted string metadata fields.
    """
    specs: tuple[tuple[bool, object], ...] = (
        (show_inodes, file_info.inode),
        (show_device, file_info.device),
        (show_permissions, file_info.permissions_str),
        (show_user, file_info.owner_user),
        (show_group, file_info.owner_group),
    )
    return [str(val) if val is not None else "-" for enabled, val in specs if enabled]


@functools.lru_cache(maxsize=1024)
def resolve_user_name(uid: int) -> str:
    """Resolve file owner username from numeric UID with caching.

    Args:
        uid: Numeric user identifier.

    Returns:
        Resolved username if available; otherwise string representation of UID.
    """
    if pwd is not None:
        try:
            return pwd.getpwuid(uid).pw_name
        except (KeyError, OSError, OverflowError):
            pass

    return str(uid)


@functools.lru_cache(maxsize=1024)
def resolve_group_name(gid: int) -> str:
    """Resolve file owner group name from numeric GID with caching.

    Args:
        gid: Numeric group identifier.

    Returns:
        Resolved group name if available; otherwise string representation of GID.
    """
    if grp is not None:
        try:
            return grp.getgrgid(gid).gr_name
        except (KeyError, OSError, OverflowError):
            pass

    return str(gid)


def format_permissions(mode: int) -> str:
    """Format file mode bits into standard ls -l permissions string.

    Args:
        mode: Integer mode bitmask (e.g., from stat_result.st_mode).

    Returns:
        Standard 10-character permissions string (e.g., '-rw-r--r--').
    """
    return stat.filemode(mode)


def extract_metadata(
    stat_result: os.stat_result | None,
) -> tuple[str | None, str | None, str | None, int | None, int | None]:
    """Extract POSIX permissions, ownership, and filesystem identifiers safely.

    Args:
        stat_result: Standard library stat_result or None if stat failed.

    Returns:
        Tuple of (permissions_str, owner_user, owner_group, inode, device).
    """
    if stat_result is None:
        return None, None, None, None, None

    permissions_str = format_permissions(stat_result.st_mode)
    owner_user = resolve_user_name(stat_result.st_uid) if hasattr(stat_result, "st_uid") else None
    owner_group = resolve_group_name(stat_result.st_gid) if hasattr(stat_result, "st_gid") else None
    inode = stat_result.st_ino if hasattr(stat_result, "st_ino") else None
    device = stat_result.st_dev if hasattr(stat_result, "st_dev") else None

    return permissions_str, owner_user, owner_group, inode, device


def clear_metadata_cache() -> None:
    """Clear in-memory caches for user and group name lookups."""
    resolve_user_name.cache_clear()
    resolve_group_name.cache_clear()
