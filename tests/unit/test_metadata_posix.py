"""Unit tests for POSIX filesystem metadata extraction and caching."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

from findfmt.classifier import classify_file
from findfmt.metadata import (
    clear_metadata_cache,
    extract_metadata,
    format_permissions,
    resolve_group_name,
    resolve_user_name,
)


def test_format_permissions_regular_file() -> None:
    """Verify format_permissions converts file mode bits to ls -l style string."""
    assert format_permissions(stat.S_IFREG | 0o644) == "-rw-r--r--"
    assert format_permissions(stat.S_IFREG | 0o755) == "-rwxr-xr-x"
    assert format_permissions(stat.S_IFREG | 0o600) == "-rw-------"
    assert format_permissions(stat.S_IFDIR | 0o755) == "drwxr-xr-x"
    assert format_permissions(stat.S_IFLNK | 0o777) == "lrwxrwxrwx"


def test_resolve_user_name_real() -> None:
    """Verify resolve_user_name resolves current user UID and utilizes caching."""
    clear_metadata_cache()
    if hasattr(os, "getuid"):
        current_uid = os.getuid()
        username = resolve_user_name(current_uid)
        assert isinstance(username, str)
        assert len(username) > 0

        # Verify cache hit
        cached_name = resolve_user_name(current_uid)
        assert cached_name == username
        info = resolve_user_name.cache_info()
        assert info.hits >= 1
    else:
        assert resolve_user_name(1000) == "1000"


def test_resolve_user_name_fallbacks() -> None:
    """Verify resolve_user_name gracefully falls back to UID string on errors."""
    clear_metadata_cache()
    unknown_uid = 99999999

    # Test unknown UID raising KeyError
    with patch("findfmt.metadata.pwd") as mock_pwd:
        mock_pwd.getpwuid.side_effect = KeyError("UID not found")
        assert resolve_user_name(unknown_uid) == "99999999"

    # Test OSError during NSS lookup
    clear_metadata_cache()
    with patch("findfmt.metadata.pwd") as mock_pwd:
        mock_pwd.getpwuid.side_effect = OSError("NSS lookup failure")
        assert resolve_user_name(unknown_uid) == "99999999"

    # Test OverflowError
    clear_metadata_cache()
    with patch("findfmt.metadata.pwd") as mock_pwd:
        mock_pwd.getpwuid.side_effect = OverflowError("UID out of range")
        assert resolve_user_name(unknown_uid) == "99999999"

    # Test when pwd module is None (Windows simulation)
    clear_metadata_cache()
    with patch("findfmt.metadata.pwd", None):
        assert resolve_user_name(1000) == "1000"


def test_resolve_group_name_real() -> None:
    """Verify resolve_group_name resolves current group GID and utilizes caching."""
    clear_metadata_cache()
    if hasattr(os, "getgid"):
        current_gid = os.getgid()
        groupname = resolve_group_name(current_gid)
        assert isinstance(groupname, str)
        assert len(groupname) > 0

        # Verify cache hit
        cached_name = resolve_group_name(current_gid)
        assert cached_name == groupname
        info = resolve_group_name.cache_info()
        assert info.hits >= 1
    else:
        assert resolve_group_name(1000) == "1000"


def test_resolve_group_name_fallbacks() -> None:
    """Verify resolve_group_name gracefully falls back to GID string on errors."""
    clear_metadata_cache()
    unknown_gid = 99999999

    # Test unknown GID raising KeyError
    with patch("findfmt.metadata.grp") as mock_grp:
        mock_grp.getgrgid.side_effect = KeyError("GID not found")
        assert resolve_group_name(unknown_gid) == "99999999"

    # Test OSError during NSS lookup
    clear_metadata_cache()
    with patch("findfmt.metadata.grp") as mock_grp:
        mock_grp.getgrgid.side_effect = OSError("NSS lookup failure")
        assert resolve_group_name(unknown_gid) == "99999999"

    # Test OverflowError
    clear_metadata_cache()
    with patch("findfmt.metadata.grp") as mock_grp:
        mock_grp.getgrgid.side_effect = OverflowError("GID out of range")
        assert resolve_group_name(unknown_gid) == "99999999"

    # Test when grp module is None (Windows simulation)
    clear_metadata_cache()
    with patch("findfmt.metadata.grp", None):
        assert resolve_group_name(1000) == "1000"


def test_extract_metadata_none() -> None:
    """Verify extract_metadata returns all Nones when stat_result is None."""
    perms, user, group, inode, device = extract_metadata(None)
    assert perms is None
    assert user is None
    assert group is None
    assert inode is None
    assert device is None


def test_extract_metadata_real(tmp_path: Path) -> None:
    """Verify extract_metadata extracts accurate attributes from a real file."""
    f = tmp_path / "sample.txt"
    f.write_text("content", encoding="utf-8")
    st = f.stat()

    perms, user, group, inode, device = extract_metadata(st)
    assert perms == format_permissions(st.st_mode)
    assert user == resolve_user_name(st.st_uid)
    assert group == resolve_group_name(st.st_gid)
    assert inode == st.st_ino
    assert device == st.st_dev


def test_extract_metadata_missing_attributes() -> None:
    """Verify extract_metadata handles stat_result objects without optional attributes."""
    mock_stat = MagicMock(spec=["st_mode"])
    mock_stat.st_mode = stat.S_IFREG | 0o644

    perms, user, group, inode, device = extract_metadata(mock_stat)
    assert perms == "-rw-r--r--"
    assert user is None
    assert group is None
    assert inode is None
    assert device is None


def test_clear_metadata_cache() -> None:
    """Verify clear_metadata_cache empties both user and group lookup caches."""
    resolve_user_name(0)
    resolve_group_name(0)
    clear_metadata_cache()
    assert resolve_user_name.cache_info().currsize == 0
    assert resolve_group_name.cache_info().currsize == 0


def test_classify_file_with_posix_metadata(tmp_path: Path) -> None:
    """Verify classify_file populates all POSIX metadata fields on real files."""
    f = tmp_path / "hello.py"
    f.write_text("print('hello')\n", encoding="utf-8")
    info = classify_file(f, root_path=tmp_path)

    st = f.stat()
    assert info.permissions_str == format_permissions(st.st_mode)
    assert info.owner_user == resolve_user_name(st.st_uid)
    assert info.owner_group == resolve_group_name(st.st_gid)
    assert info.inode == st.st_ino
    assert info.device == st.st_dev


def test_classify_file_symlink_metadata(tmp_path: Path) -> None:
    """Verify classify_file captures symlink-specific metadata and permission string."""
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    info = classify_file(link, root_path=tmp_path)
    assert info.is_symlink is True
    assert info.permissions_str is not None
    assert info.permissions_str.startswith("l")


def test_classify_file_stat_failure_metadata(tmp_path: Path) -> None:
    """Verify classify_file gracefully sets metadata to None if stat fails."""
    target = tmp_path / "broken.txt"
    target.write_text("broken", encoding="utf-8")

    with patch.object(Path, "stat", side_effect=OSError("Permission denied")):
        info = classify_file(target, root_path=tmp_path)
        assert info.permissions_str is None
        assert info.owner_user is None
        assert info.owner_group is None
        assert info.inode is None
        assert info.device is None
