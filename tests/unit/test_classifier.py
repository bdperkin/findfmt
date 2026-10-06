import stat
from pathlib import Path
from unittest.mock import patch

from findfmt.classifier import classify_file, extract_shebang, get_known_tags


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
