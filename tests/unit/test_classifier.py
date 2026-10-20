import os
import stat
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from findfmt import classifier
from findfmt.classifier import (
    _identify_tags,
    _inspect_metadata,
    _read_initial_buffer,
    _resolve_relative,
    classify_file,
    compute_relative_prefix,
    extract_shebang,
    extract_shebang_from_buffer,
    get_known_tags,
)


def test_get_known_tags():
    tags = get_known_tags()
    assert isinstance(tags, frozenset)
    assert "python" in tags
    assert "text" in tags
    assert len(tags) > 50


def test_extract_shebang_valid(tmp_path: Path):
    file_path = tmp_path / "script.sh"
    file_path.write_text("#!/bin/bash -e\necho 1", encoding="utf-8")
    assert extract_shebang(file_path) == "#!/bin/bash -e"


def test_extract_shebang_none(tmp_path: Path):
    file_path = tmp_path / "plain.txt"
    file_path.write_text("Hello world", encoding="utf-8")
    assert extract_shebang(file_path) is None


def test_extract_shebang_nonexistent(tmp_path: Path):
    assert extract_shebang(tmp_path / "does_not_exist.sh") is None


def test_extract_shebang_os_error(tmp_path: Path):
    file_path = tmp_path / "unreadable.sh"
    file_path.write_text("#!/bin/sh", encoding="utf-8")
    with patch.object(Path, "open", side_effect=OSError("Read error")):
        assert extract_shebang(file_path) is None


def test_classify_file_python(tmp_path: Path):
    py_file = tmp_path / "test.py"
    py_file.write_text("import sys\n", encoding="utf-8")
    info = classify_file(py_file, root_path=tmp_path)
    assert "python" in info.tags
    assert "text" in info.tags
    assert info.shebang is None
    assert info.mime_type in ("text/x-python", "text/plain")
    assert not info.is_executable
    assert not info.is_symlink
    assert info.size_bytes > 0
    assert info.relative_path == Path("test.py")


def test_classify_file_with_shebang(tmp_path: Path):
    script = tmp_path / "runner"
    script.write_text("#!/usr/bin/env python3\nprint(1)\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)

    info = classify_file(script, root_path=tmp_path)
    assert "python" in info.tags
    assert info.shebang == "#!/usr/bin/env python3"
    assert info.is_executable


def test_classify_file_symlink(tmp_path: Path):
    target = tmp_path / "target.txt"
    target.write_text("content", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    info = classify_file(link, root_path=tmp_path)
    assert info.is_symlink
    assert "symlink" in info.tags or "text" in info.tags


def test_classify_file_nonexistent(tmp_path: Path):
    nonexistent = tmp_path / "missing.py"
    info = classify_file(nonexistent, root_path=tmp_path)
    assert "python" in info.tags
    assert info.size_bytes == 0
    assert not info.is_executable


def test_classify_file_no_root_path(tmp_path: Path):
    file_path = tmp_path / "sample.json"
    file_path.write_text('{"a": 1}', encoding="utf-8")
    info = classify_file(file_path)
    assert info.relative_path == file_path
    assert "json" in info.tags


def test_classify_file_relative_to_unrelated_root(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("data", encoding="utf-8")
    other_dir = Path("/some/unrelated/directory")
    info = classify_file(file_path, root_path=other_dir)
    assert info.relative_path == file_path


def test_classify_file_stat_os_error(tmp_path: Path):
    target = tmp_path / "error.txt"
    target.write_text("hello", encoding="utf-8")
    with patch.object(Path, "stat", side_effect=OSError("Stat failed")):
        info = classify_file(target, root_path=tmp_path)
        assert info.size_bytes == 0


def test_classify_file_identify_raises_value_error(tmp_path: Path):
    target = tmp_path / "weird_file.py"
    target.write_text("code", encoding="utf-8")
    with patch("identify.identify.tags_from_path", side_effect=ValueError("identify error")):
        info = classify_file(target, root_path=tmp_path)
        assert "python" in info.tags


def test_classify_file_is_symlink_os_error(tmp_path: Path):
    target = tmp_path / "target.txt"
    target.write_text("hello", encoding="utf-8")
    with patch.object(Path, "is_symlink", side_effect=OSError("Permission error")):
        info = classify_file(target, root_path=tmp_path)
        assert not info.is_symlink


def test_classify_file_exists_os_error(tmp_path: Path):
    target = tmp_path / "target.txt"
    target.write_text("hello", encoding="utf-8")
    with patch.object(Path, "exists", side_effect=OSError("Permission error")):
        info = classify_file(target, root_path=tmp_path)
        assert not info.is_executable


def test_classify_file_windows_executable(tmp_path: Path, monkeypatch):
    target = tmp_path / "script.bat"
    target.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr("os.name", "nt")
    info = classify_file(target, root_path=tmp_path)
    assert info.is_executable
    assert "executable" in info.tags
    assert "non-executable" not in info.tags


def test_classify_file_windows_non_executable(tmp_path: Path, monkeypatch):
    target = tmp_path / "doc.txt"
    target.write_text("hello\n", encoding="utf-8")
    monkeypatch.setattr("os.name", "nt")
    info = classify_file(target, root_path=tmp_path)
    assert not info.is_executable
    assert "non-executable" in info.tags
    assert "executable" not in info.tags


def test_classify_file_posix_execution(tmp_path: Path, monkeypatch):
    target = tmp_path / "script.sh"
    target.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr("os.name", "posix")
    info = classify_file(target, root_path=tmp_path)
    assert info.path.name == "script.sh"


def test_extract_shebang_directory(tmp_path: Path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    assert extract_shebang(sub) is None


def test_classify_file_is_file_os_error(tmp_path: Path):
    target = tmp_path / "target.py"
    target.write_text("print('test')", encoding="utf-8")
    with patch.object(Path, "is_file", side_effect=OSError("Permission denied")):
        info = classify_file(target, root_path=tmp_path)
        assert "python" in info.tags


def test_classify_file_fifo(tmp_path: Path):
    fifo_path = tmp_path / "stream.pipe"
    try:
        os.mkfifo(fifo_path)
    except (AttributeError, OSError):
        return

    info = classify_file(fifo_path, root_path=tmp_path)
    assert info.shebang is None


def test_compute_relative_prefix() -> None:
    # Non-absolute relative root
    assert compute_relative_prefix(Path("assets")) == Path("assets")
    assert compute_relative_prefix(Path("./assets")) == Path("assets")
    assert compute_relative_prefix(Path()) is None

    # Absolute root inside cwd
    cwd = Path.cwd()
    inside_dir = cwd / "src"
    assert compute_relative_prefix(inside_dir) == Path("src")
    assert compute_relative_prefix(cwd) is None

    # Absolute root outside cwd (unrelated)
    unrelated = Path("/some/unrelated/directory/outside/cwd").resolve()
    assert compute_relative_prefix(unrelated) == unrelated

    with patch.object(Path, "relative_to", side_effect=ValueError("outside cwd")):
        assert compute_relative_prefix(cwd) == cwd


def test_classify_file_with_prefix(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    f = sub / "doc.txt"
    f.write_text("hello", encoding="utf-8")

    info = classify_file(f, root_path=sub, prefix=Path("my_prefix"))
    assert info.relative_path == Path("my_prefix/doc.txt")

    # Prefix "." or empty returns un-prefixed relative path
    info_dot = classify_file(f, root_path=sub, prefix=Path())
    assert info_dot.relative_path == Path("doc.txt")


def test_resolve_relative_relpath_error(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    with patch("os.path.relpath", side_effect=ValueError("different drive")):
        assert _resolve_relative(f, Path("/other/root")) == f


def test_resolve_relative_sibling_unrelated(tmp_path: Path) -> None:
    dir_a = tmp_path / "dir_a"
    dir_b = tmp_path / "dir_b"
    dir_a.mkdir()
    dir_b.mkdir()
    f = dir_a / "a.txt"
    f.write_text("data", encoding="utf-8")
    assert _resolve_relative(f, dir_b) == f


def test_identify_tags_empty_shebang_and_errors(tmp_path: Path) -> None:
    # Buffer starting with #! but with invalid or unknown shebang that yields empty parts
    with patch("identify.identify.parse_shebang", return_value=()):
        tags = _identify_tags(
            tmp_path / "script",
            str(tmp_path / "script"),
            exists=True,
            is_regular_or_symlink=True,
            buffer=b"#!\n",
            is_executable=True,
        )
        assert "file" in tags
        assert "executable" in tags

    # tags_from_path raises OSError when buffer is None
    with patch("identify.identify.tags_from_path", side_effect=OSError("read error")):
        tags_err = _identify_tags(
            tmp_path / "err.py",
            str(tmp_path / "err.py"),
            exists=True,
            is_regular_or_symlink=True,
            buffer=None,
        )
        assert "python" in tags_err


def test_inspect_metadata_direntry_error_branches(tmp_path: Path) -> None:
    mock_entry = MagicMock(spec=os.DirEntry)
    mock_entry.is_symlink.side_effect = OSError("symlink check error")
    mock_entry.stat.side_effect = OSError("stat error")

    is_sym, exists, is_file, size, st = _inspect_metadata(tmp_path / "file", entry=mock_entry)
    assert not is_sym
    assert not exists
    assert not is_file
    assert size == 0
    assert st is None

    # is_symlink=True and exists=True, but path.is_file() raises OSError
    mock_entry2 = MagicMock(spec=os.DirEntry)
    mock_entry2.is_symlink.return_value = True
    fake_stat = tmp_path.stat()
    mock_entry2.stat.return_value = fake_stat

    with patch.object(Path, "is_file", side_effect=OSError("is_file error")):
        is_sym2, exists2, is_file2, size2, _ = _inspect_metadata(
            tmp_path / "sym",
            entry=mock_entry2,
        )
        assert is_sym2
        assert exists2
        assert not is_file2
        assert size2 == fake_stat.st_size


def test_extract_shebang_from_buffer() -> None:
    assert extract_shebang_from_buffer(b"#!/bin/bash\necho hi") == "#!/bin/bash"
    assert extract_shebang_from_buffer(b"no shebang here") is None


def test_classify_file_with_direntry(tmp_path: Path) -> None:
    f = tmp_path / "script.py"
    f.write_text("print('hello')", encoding="utf-8")
    entries = list(os.scandir(tmp_path))
    py_entry = next(e for e in entries if e.name == "script.py")

    info = classify_file(f, root_path=tmp_path, entry=py_entry)
    assert "python" in info.tags
    assert info.size_bytes > 0
    assert info.path == f


def test_fifo_swap_does_not_block(tmp_path: Path) -> None:
    """Verify swapped FIFO never blocks execution and is treated as non-regular."""
    # 1. Real POSIX FIFO test (when mkfifo is available)
    if hasattr(os, "mkfifo"):
        swap_path = tmp_path / "swap.pipe"
        swap_path.write_text("initial regular content\n", encoding="utf-8")
        orig_inspect = _inspect_metadata

        def swapped_inspect(path: Path, entry: os.DirEntry[str] | None = None):
            res = orig_inspect(path, entry=entry)
            path.unlink()
            os.mkfifo(path)
            return res

        start = time.perf_counter()
        with patch.object(classifier, "_inspect_metadata", side_effect=swapped_inspect):
            info = classify_file(swap_path, root_path=tmp_path)

        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"FIFO swap took {elapsed}s, expected < 1.0s"
        assert info.indicator == "|"
        assert info.shebang is None
        assert "file" not in info.tags
        assert info.permissions_str is not None
        assert info.permissions_str.startswith("p")

    # 2. Mocked FIFO swap test (ensures coverage across all platforms including Windows)
    mock_path = tmp_path / "mock_swap.pipe"
    mock_path.write_text("initial content\n", encoding="utf-8")
    mock_stat = MagicMock(spec=os.stat_result)
    mock_stat.st_mode = stat.S_IFIFO | 0o644
    mock_stat.st_size = 0
    mock_stat.st_mtime = 1000.0
    mock_stat.st_ctime = 1000.0
    mock_stat.st_uid = 1000
    mock_stat.st_gid = 1000
    mock_stat.st_ino = 12345
    mock_stat.st_dev = 67890

    with (
        patch("os.open", return_value=99),
        patch("os.fstat", return_value=mock_stat),
        patch("os.close") as mock_close,
    ):
        info_mock = classify_file(mock_path, root_path=tmp_path)

    mock_close.assert_called_once_with(99)
    assert info_mock.indicator == "|"
    assert info_mock.shebang is None
    assert "file" not in info_mock.tags
    assert info_mock.permissions_str is not None
    assert info_mock.permissions_str.startswith("p")


def test_read_initial_buffer_error_handling(tmp_path: Path) -> None:
    """Verify _read_initial_buffer handles open and fstat OSError conditions gracefully."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("data", encoding="utf-8")

    # os.open failure returns (b"", None)
    with patch("os.open", side_effect=OSError("Open denied")):
        assert _read_initial_buffer(test_file) == (b"", None)

    # os.fstat failure closes fd and returns (b"", None)
    with (
        patch("os.open", return_value=88),
        patch("os.fstat", side_effect=OSError("fstat error")),
        patch("os.close") as mock_close,
    ):
        assert _read_initial_buffer(test_file) == (b"", None)
        mock_close.assert_called_once_with(88)
