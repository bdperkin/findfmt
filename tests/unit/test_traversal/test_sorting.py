"""Unit tests for directory entry sorting, natural version keys, and stat ordering."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from findfmt.models import SortKey, TraversalConfig
from findfmt.traversal.engine import _scan_directory_entries, find_files
from findfmt.traversal.sorting import (
    _SortChunk,
    get_entry_ctime,
    get_entry_mtime,
    get_entry_size,
    is_reverse_sort,
    natural_sort_key,
    resolve_sort_key,
    sort_directory_entries,
)


def test_sort_chunk_comparisons_and_hash() -> None:
    """Verify _SortChunk equality, ordering, type mismatch, and hashing."""
    chunk_num1 = _SortChunk("1")
    chunk_num2 = _SortChunk("2")
    chunk_str_a = _SortChunk("a")
    chunk_str_b = _SortChunk("b")

    # Equality
    assert chunk_num1 == _SortChunk("1")
    assert chunk_num1 != chunk_num2
    assert chunk_num1 != "1"
    assert chunk_num1 != chunk_str_a
    assert chunk_str_a == _SortChunk("a")
    assert chunk_str_a != chunk_str_b

    # Ordering
    assert chunk_num1 < chunk_num2
    assert not (chunk_num2 < chunk_num1)
    assert chunk_num1 < chunk_str_a
    assert not (chunk_str_a < chunk_num1)
    assert chunk_str_a < chunk_str_b
    assert not (chunk_str_b < chunk_str_a)

    with pytest.raises(TypeError):
        _ = chunk_num1 < 1

    # Hashing
    assert hash(chunk_num1) == hash(_SortChunk("1"))
    assert hash(chunk_str_a) == hash(_SortChunk("a"))
    assert len({chunk_num1, _SortChunk("1"), chunk_str_a}) == 2


def test_natural_sort_key() -> None:
    """Verify natural version chunking for numbers and embedded strings."""
    assert natural_sort_key("file1.txt") < natural_sort_key("file2.txt")
    assert natural_sort_key("file2.txt") < natural_sort_key("file10.txt")
    assert natural_sort_key("v1.2.0") < natural_sort_key("v1.10.0")

    # Case sensitivity check
    lower_res = natural_sort_key("FileA.txt", ignore_case=True)
    lower_res2 = natural_sort_key("filea.txt", ignore_case=True)
    assert lower_res == lower_res2

    case_diff1 = natural_sort_key("FileA.txt", ignore_case=False)
    case_diff2 = natural_sort_key("filea.txt", ignore_case=False)
    assert case_diff1 != case_diff2


def test_version_sort_unicode_superscript_digits(tmp_path: Path) -> None:
    """Verify version sort safely handles Unicode superscript and non-decimal digits."""
    chunk_sup2 = _SortChunk("²")
    assert not chunk_sup2.is_digit
    assert chunk_sup2.val_str == "²"
    assert chunk_sup2.val_int == 0

    chunk_sup3 = _SortChunk("³")
    assert not chunk_sup3.is_digit
    assert chunk_sup3.val_str == "³"

    # Ensure comparing superscript chunk with digit chunk works without ValueError
    chunk_num = _SortChunk("2")
    assert chunk_num.is_digit
    assert chunk_num < chunk_sup2

    # Natural sort key handles superscript filenames deterministically
    names = ["²", "a²", "file10", "file2"]
    sorted_names = sorted(names, key=natural_sort_key)
    assert sorted_names == ["a²", "file2", "file10", "²"]

    # Verify sort_directory_entries with SortKey.VERSION
    (tmp_path / "²").write_text("sup")
    (tmp_path / "a²").write_text("asup")
    (tmp_path / "file10").write_text("10")
    (tmp_path / "file2").write_text("2")

    entries = list(os.scandir(tmp_path))
    sorted_entries = sort_directory_entries(
        entries.copy(),
        TraversalConfig(sort_by=SortKey.VERSION),
    )
    assert [e.name for e in sorted_entries] == ["a²", "file2", "file10", "²"]

    # Verify end-to-end traversal with find_files
    results = [
        f.path.name
        for f in find_files(TraversalConfig(root_paths=(tmp_path,), sort_by=SortKey.VERSION))
    ]
    assert results == ["a²", "file2", "file10", "²"]


def test_get_entry_stat_helpers() -> None:
    """Verify stat extraction and OSError fallback handling."""
    mock_entry = MagicMock(spec=os.DirEntry)
    mock_stat = MagicMock()
    mock_stat.st_mtime = 12345.67
    mock_stat.st_ctime = 23456.78
    mock_stat.st_size = 4096
    mock_entry.stat.return_value = mock_stat

    assert get_entry_mtime(mock_entry) == 12345.67
    assert get_entry_ctime(mock_entry) == 23456.78
    assert get_entry_size(mock_entry) == 4096

    # Verify OSError handling
    error_entry = MagicMock(spec=os.DirEntry)
    error_entry.stat.side_effect = OSError("stat failure")
    assert get_entry_mtime(error_entry) == 0.0
    assert get_entry_ctime(error_entry) == 0.0
    assert get_entry_size(error_entry) == 0


def test_is_reverse_sort() -> None:
    """Verify reverse sort resolution across ascending and descending keys."""
    # Ascending by default (NAME, VERSION)
    assert not is_reverse_sort(TraversalConfig(sort_by=SortKey.NAME))
    assert is_reverse_sort(TraversalConfig(sort_by=SortKey.NAME, reverse_sort=True))
    assert not is_reverse_sort(TraversalConfig(sort_by=SortKey.VERSION))
    assert is_reverse_sort(TraversalConfig(sort_by=SortKey.VERSION, reverse_sort=True))

    # Descending by default (TIME, MTIME, CTIME, SIZE)
    assert is_reverse_sort(TraversalConfig(sort_by=SortKey.TIME))
    assert not is_reverse_sort(TraversalConfig(sort_by=SortKey.TIME, reverse_sort=True))
    assert is_reverse_sort(TraversalConfig(sort_by=SortKey.MTIME))
    assert is_reverse_sort(TraversalConfig(sort_by=SortKey.CTIME))
    assert is_reverse_sort(TraversalConfig(sort_by=SortKey.SIZE))
    assert not is_reverse_sort(TraversalConfig(sort_by=SortKey.SIZE, reverse_sort=True))


def test_resolve_sort_key() -> None:
    """Verify parsing and validation of CLI sort strings."""
    assert resolve_sort_key(None) == SortKey.NAME
    assert resolve_sort_key(SortKey.SIZE) == SortKey.SIZE
    assert resolve_sort_key("name") == SortKey.NAME
    assert resolve_sort_key("version") == SortKey.VERSION
    assert resolve_sort_key("time") == SortKey.TIME
    assert resolve_sort_key("mtime") == SortKey.TIME
    assert resolve_sort_key("ctime") == SortKey.CTIME
    assert resolve_sort_key("size") == SortKey.SIZE
    assert resolve_sort_key("none") == SortKey.NONE
    assert resolve_sort_key("unsorted") == SortKey.NONE
    assert resolve_sort_key("size", unsorted=True) == SortKey.NONE

    with pytest.raises(ValueError, match="Invalid sort criteria 'invalid'"):
        resolve_sort_key("invalid")


def test_sort_directory_entries_criteria(tmp_path: Path) -> None:
    """Verify sorting directory entries across name, version, size, and time."""
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f10 = tmp_path / "file10.txt"

    f1.write_text("a" * 10)
    time.sleep(0.01)
    f2.write_text("b" * 100)
    time.sleep(0.01)
    f10.write_text("c" * 5)

    entries = list(os.scandir(tmp_path))

    # Natural version sort
    sorted_ver = sort_directory_entries(
        entries.copy(),
        TraversalConfig(sort_by=SortKey.VERSION),
    )
    assert [e.name for e in sorted_ver] == ["file1.txt", "file2.txt", "file10.txt"]

    # Natural version reverse sort
    sorted_ver_rev = sort_directory_entries(
        entries.copy(),
        TraversalConfig(sort_by=SortKey.VERSION, reverse_sort=True),
    )
    assert [e.name for e in sorted_ver_rev] == ["file10.txt", "file2.txt", "file1.txt"]

    # Alphabetical name sort
    sorted_name = sort_directory_entries(
        entries.copy(),
        TraversalConfig(sort_by=SortKey.NAME),
    )
    assert [e.name for e in sorted_name] == ["file1.txt", "file10.txt", "file2.txt"]

    # Size sort (largest first: f2=100, f1=10, f10=5)
    sorted_size = sort_directory_entries(
        entries.copy(),
        TraversalConfig(sort_by=SortKey.SIZE),
    )
    assert [e.name for e in sorted_size] == ["file2.txt", "file1.txt", "file10.txt"]

    # Size reverse sort (smallest first)
    sorted_size_rev = sort_directory_entries(
        entries.copy(),
        TraversalConfig(sort_by=SortKey.SIZE, reverse_sort=True),
    )
    assert [e.name for e in sorted_size_rev] == ["file10.txt", "file1.txt", "file2.txt"]

    # Modification time sort (newest first: f10, f2, f1)
    sorted_time = sort_directory_entries(
        entries.copy(),
        TraversalConfig(sort_by=SortKey.TIME),
    )
    assert [e.name for e in sorted_time] == ["file10.txt", "file2.txt", "file1.txt"]

    # Modification time reverse sort (oldest first: f1, f2, f10)
    sorted_time_rev = sort_directory_entries(
        entries.copy(),
        TraversalConfig(sort_by=SortKey.TIME, reverse_sort=True),
    )
    assert [e.name for e in sorted_time_rev] == ["file1.txt", "file2.txt", "file10.txt"]

    # Status change time sort (CTIME)
    sorted_ctime = sort_directory_entries(
        entries.copy(),
        TraversalConfig(sort_by=SortKey.CTIME),
    )
    assert len(sorted_ctime) == 3

    # Unsorted mode preserves input list ordering
    unsorted_res = sort_directory_entries(
        entries.copy(),
        TraversalConfig(sort_by=SortKey.NONE),
    )
    assert [e.name for e in unsorted_res] == [e.name for e in entries]


def test_traversal_dirs_first_and_files_first(tmp_path: Path) -> None:
    """Verify directory grouping (dirs_first vs default/files_first) during traversal."""
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    (sub_dir / "sub_file.txt").write_text("sub")
    (tmp_path / "root_file.txt").write_text("root")

    # Default / files first: root_file emitted before sub/sub_file
    files_default = list(find_files(TraversalConfig(root_paths=(tmp_path,))))
    assert [f.path.name for f in files_default] == ["root_file.txt", "sub_file.txt"]

    # Dirs first: sub/sub_file emitted before root_file
    config_dirs_first = TraversalConfig(root_paths=(tmp_path,), dirs_first=True)
    files_dirs_first = list(find_files(config_dirs_first))
    assert [f.path.name for f in files_dirs_first] == ["sub_file.txt", "root_file.txt"]


def test_scan_directory_entries_unsorted_and_file_limit(tmp_path: Path) -> None:
    """Verify _scan_directory_entries in unsorted mode with and without filelimit."""
    for i in range(5):
        (tmp_path / f"file_{i}.txt").write_text(f"content {i}")

    # Normal unsorted scan
    config_none = TraversalConfig(sort_by=SortKey.NONE)
    subdirs, files = _scan_directory_entries(tmp_path, config_none, ())
    assert len(files) == 5
    assert subdirs == []

    # Unsorted scan exceeding filelimit
    config_limit = TraversalConfig(sort_by=SortKey.NONE, file_limit=2)
    subdirs_lim, files_lim = _scan_directory_entries(tmp_path, config_limit, ())
    assert subdirs_lim == []
    assert files_lim == []

    # Unsorted scan within filelimit
    config_ok = TraversalConfig(sort_by=SortKey.NONE, file_limit=10)
    subdirs_ok, files_ok = _scan_directory_entries(tmp_path, config_ok, ())
    assert len(files_ok) == 5
    assert subdirs_ok == []

    # Single file traversal in find_files
    single_file = tmp_path / "file_0.txt"
    single_found = list(find_files(TraversalConfig(root_paths=(single_file,))))
    assert len(single_found) == 1
    assert single_found[0].path == single_file.resolve()
