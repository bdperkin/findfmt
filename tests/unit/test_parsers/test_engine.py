"""Unit tests for listing ingestion coordinator and offline classification."""

from __future__ import annotations

import io
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from findfmt.models import FileInfo, SortKey, TraversalConfig
from findfmt.parsers.engine import (
    _read_lines,
    _resolve_and_classify,
    _sort_file_infos,
    classify_file_offline,
    detect_input_format,
    ingest_from_file,
)
from findfmt.parsers.flat_parser import ParsedEntry


def test_detect_input_format() -> None:
    """Verify input format auto-detection between flat and outline structures."""
    assert detect_input_format(["foo.py", "bar.py"]) == "flat"
    assert detect_input_format(["", "# comment", "src/main.py"]) == "flat"
    assert detect_input_format([]) == "flat"

    assert detect_input_format(["src", "\tmain.py"]) == "outline"
    assert detect_input_format(["src", "  main.py"]) == "outline"
    assert detect_input_format(["root", "├── child.py"]) == "outline"


def test_classify_file_offline_posix_and_symlink() -> None:
    """Verify offline classification on POSIX with symlink attributes."""
    info = classify_file_offline(
        Path("/remote/dir/script.py"),
        relative_path=Path("script.py"),
        is_symlink=True,
        symlink_target="target.py",
    )
    assert info.path == Path("/remote/dir/script.py")
    assert info.relative_path == Path("script.py")
    assert "python" in info.tags
    assert "symlink" in info.tags
    assert info.is_symlink is True
    assert info.symlink_target == "target.py"
    assert info.mime_type == "text/x-python"
    assert info.size_bytes == 0


def test_classify_file_offline_windows_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify offline classification under Windows executable rules."""
    exe_path = Path("app.exe")
    txt_path = Path("notes.txt")
    monkeypatch.setattr("os.name", "nt")
    monkeypatch.setenv("PATHEXT", ".EXE;.BAT")
    exe_info = classify_file_offline(
        exe_path,
        relative_path=exe_path,
    )
    assert exe_info.is_executable is True
    assert "executable" in exe_info.tags

    txt_info = classify_file_offline(
        txt_path,
        relative_path=txt_path,
    )
    assert txt_info.is_executable is False
    assert "non-executable" in txt_info.tags


def test_classify_file_offline_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify offline classification under POSIX rules."""
    script_path = Path("script.sh")
    monkeypatch.setattr("os.name", "posix")
    info = classify_file_offline(
        script_path,
        relative_path=script_path,
    )
    assert info.is_executable is False
    assert "executable" not in info.tags


def test_resolve_and_classify_online_vs_offline(tmp_path: Path) -> None:
    """Verify online inspection of real disk files and offline overrides."""
    real_file = tmp_path / "actual.py"
    real_file.write_text("#!/usr/bin/env python3\nprint('hello')\n")

    cfg_online = TraversalConfig(root_paths=(tmp_path,))
    cfg_offline = TraversalConfig(root_paths=(tmp_path,), offline=True)

    entry_relative = ParsedEntry(path_str="actual.py")
    info_online = _resolve_and_classify(entry_relative, tmp_path, cfg_online)
    assert info_online.size_bytes > 0
    assert "python" in info_online.tags

    info_offline = _resolve_and_classify(entry_relative, tmp_path, cfg_offline)
    assert info_offline.size_bytes == 0
    assert info_offline.shebang is None

    # Absolute path handling
    entry_abs = ParsedEntry(path_str=str(real_file))
    info_abs = _resolve_and_classify(entry_abs, tmp_path, cfg_online)
    assert info_abs.path == real_file

    # Nonexistent path in online mode falls back gracefully
    entry_nonexistent = ParsedEntry(path_str="missing.rs")
    info_missing = _resolve_and_classify(entry_nonexistent, tmp_path, cfg_online)
    assert "rust" in info_missing.tags or "text" in info_missing.tags
    assert info_missing.size_bytes == 0

    # Symlink override on existing file
    entry_symlink = ParsedEntry(path_str="actual.py", is_symlink=True, symlink_target="dest.py")
    info_sym = _resolve_and_classify(entry_symlink, tmp_path, cfg_online)
    assert info_sym.is_symlink is True
    assert info_sym.symlink_target == "dest.py"


def test_read_lines(tmp_path: Path) -> None:
    """Verify _read_lines from file, stdin, and None."""
    assert _read_lines(None) == []

    # From file
    f = tmp_path / "input.txt"
    f.write_text("line1\nline2\n")
    assert _read_lines(str(f)) == ["line1", "line2"]

    # From stdin stream
    stream = io.StringIO("stdin1\nstdin2\n")
    assert _read_lines("-", stream=stream) == ["stdin1", "stdin2"]


def test_sort_file_infos(tmp_path: Path) -> None:
    """Verify sorting and grouping permutations on FileInfo instances."""
    f1 = tmp_path / "item1.txt"
    f2 = tmp_path / "item2.txt"
    f10 = tmp_path / "item10.txt"
    f1.write_text("1")
    f2.write_text("22")
    f10.write_text("333")

    info1 = classify_file_offline(f1, relative_path=Path("item1.txt"))
    info2 = classify_file_offline(f2, relative_path=Path("item2.txt"))
    info10 = classify_file_offline(f10, relative_path=Path("item10.txt"))
    infos = [info10, info1, info2]

    # SortKey.NONE
    cfg_none = TraversalConfig(sort_by=SortKey.NONE)
    assert _sort_file_infos(infos, cfg_none) == infos

    # SortKey.VERSION
    cfg_ver = TraversalConfig(sort_by=SortKey.VERSION)
    sorted_ver = _sort_file_infos(infos, cfg_ver)
    assert [f.relative_path.name for f in sorted_ver] == ["item1.txt", "item2.txt", "item10.txt"]

    # SortKey.NAME reverse
    cfg_name_rev = TraversalConfig(sort_by=SortKey.NAME, reverse_sort=True)
    sorted_name_rev = _sort_file_infos(infos, cfg_name_rev)
    expected_rev = ["item2.txt", "item10.txt", "item1.txt"]
    assert [f.relative_path.name for f in sorted_name_rev] == expected_rev

    # SortKey.SIZE
    info1_sized = FileInfo(path=f1, relative_path=Path("item1.txt"), size_bytes=100)
    info2_sized = FileInfo(path=f2, relative_path=Path("item2.txt"), size_bytes=200)
    cfg_size = TraversalConfig(sort_by=SortKey.SIZE)
    sorted_size = _sort_file_infos([info1_sized, info2_sized], cfg_size)
    assert [f.size_bytes for f in sorted_size] == [200, 100]

    # SortKey.TIME
    cfg_time = TraversalConfig(sort_by=SortKey.TIME)
    sorted_time = _sort_file_infos([info1, info2], cfg_time)
    assert len(sorted_time) == 2

    with patch.object(Path, "stat", side_effect=OSError("stat failed")):
        sorted_time_err = _sort_file_infos([info1, info2], cfg_time)
        assert len(sorted_time_err) == 2

    # Grouping dirs_first and files_first
    dir_info = FileInfo(
        path=tmp_path / "somedir",
        relative_path=Path("somedir"),
        tags=frozenset({"directory"}),
    )
    cfg_df = TraversalConfig(dirs_first=True)
    res_df = _sort_file_infos([info1, dir_info], cfg_df)
    assert res_df[0] == dir_info

    cfg_ff = TraversalConfig(files_first=True)
    res_ff = _sort_file_infos([dir_info, info1], cfg_ff)
    assert res_ff[0] == info1


def test_ingest_from_file_flat_and_outline(tmp_path: Path) -> None:
    """Verify end-to-end ingestion from flat and outline inputs with filtering."""
    # Flat listing
    flat_content = "fileA.py\nfileB.txt\n"
    stream_flat = io.StringIO(flat_content)
    cfg_flat = TraversalConfig(from_file="-", root_paths=(tmp_path,))
    results_flat = list(ingest_from_file(cfg_flat, input_stream=stream_flat))
    assert [f.relative_path.name for f in results_flat] == ["fileA.py", "fileB.txt"]

    # Outline listing with directory suppression in default mode
    outline_content = "parent\n\tchild.py\n\tsubdir/\n"
    stream_outline = io.StringIO(outline_content)
    cfg_outline = TraversalConfig(from_file="-", root_paths=(tmp_path,))
    results_outline = list(ingest_from_file(cfg_outline, input_stream=stream_outline))
    assert [f.relative_path.name for f in results_outline] == ["child.py"]

    # Outline listing with dirs_only
    stream_dirs = io.StringIO(outline_content)
    cfg_dirs = TraversalConfig(from_file="-", dirs_only=True, root_paths=(tmp_path,))
    results_dirs = list(ingest_from_file(cfg_dirs, input_stream=stream_dirs))
    assert [f.relative_path.name for f in results_dirs] == ["parent", "subdir"]


def test_sort_file_infos_ctime_uses_status_change_time(tmp_path: Path) -> None:
    """Verify CTIME sorts on st_ctime while TIME and MTIME keep using st_mtime."""
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("a")
    file_b.write_text("b")

    info_a = classify_file_offline(file_a, relative_path=Path("a.txt"))
    info_b = classify_file_offline(file_b, relative_path=Path("b.txt"))

    # os.stat_result tuple order: mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime.
    # a.txt is older by mtime but newer by ctime; b.txt is the inverse.
    stats = {
        "a.txt": os.stat_result((0, 0, 0, 1, 0, 0, 1, 1000.0, 1000.0, 2000.0)),
        "b.txt": os.stat_result((0, 0, 0, 1, 0, 0, 1, 2000.0, 2000.0, 1000.0)),
    }

    def _fake_stat(self: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        assert follow_symlinks is True
        return stats[self.name]

    with patch.object(Path, "stat", _fake_stat):
        # Time keys default to descending order (newest first), so CTIME must yield
        # a.txt (ctime 2000) before b.txt (ctime 1000) -- the inverse of the mtime order.
        cfg_ctime = TraversalConfig(sort_by=SortKey.CTIME)
        sorted_ctime = _sort_file_infos([info_b, info_a], cfg_ctime)
        assert [f.relative_path.name for f in sorted_ctime] == ["a.txt", "b.txt"]

        for sort_key in (SortKey.TIME, SortKey.MTIME):
            cfg_mtime = TraversalConfig(sort_by=sort_key)
            sorted_mtime = _sort_file_infos([info_b, info_a], cfg_mtime)
            assert [f.relative_path.name for f in sorted_mtime] == ["b.txt", "a.txt"]
