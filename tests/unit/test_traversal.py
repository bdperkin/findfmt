import os
from pathlib import Path
from unittest.mock import patch

import pathspec

from findfmt.models import FileInfo, TraversalConfig
from findfmt.traversal import (
    _is_path_ignored,
    _load_active_specs,
    _scan_directory_entries,
    find_files,
    load_git_exclude_spec,
    load_gitignore_spec,
    matches_filter,
    should_skip_dir,
    traverse_directory,
)


def test_load_gitignore_spec_valid(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("*.tmp\nbuild/\n", encoding="utf-8")
    spec = load_gitignore_spec(tmp_path)
    assert spec is not None
    assert spec.match_file("file.tmp")
    assert not spec.match_file("file.py")


def test_load_gitignore_spec_empty_or_comments(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("# only comments\n   \n", encoding="utf-8")
    assert load_gitignore_spec(tmp_path) is None


def test_load_gitignore_spec_missing(tmp_path: Path):
    assert load_gitignore_spec(tmp_path) is None


def test_load_gitignore_spec_os_error(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("*.tmp", encoding="utf-8")
    with patch.object(Path, "open", side_effect=OSError("Read error")):
        assert load_gitignore_spec(tmp_path) is None


def test_load_git_exclude_spec_valid(tmp_path: Path):
    git_dir = tmp_path / ".git" / "info"
    git_dir.mkdir(parents=True)
    (git_dir / "exclude").write_text("*.custom\n", encoding="utf-8")
    spec = load_git_exclude_spec(tmp_path)
    assert spec is not None
    assert spec.match_file("test.custom")


def test_load_git_exclude_spec_empty(tmp_path: Path):
    git_dir = tmp_path / ".git" / "info"
    git_dir.mkdir(parents=True)
    (git_dir / "exclude").write_text("# comment only\n", encoding="utf-8")
    assert load_git_exclude_spec(tmp_path) is None


def test_load_git_exclude_spec_missing(tmp_path: Path):
    assert load_git_exclude_spec(tmp_path) is None


def test_load_git_exclude_spec_os_error(tmp_path: Path):
    git_dir = tmp_path / ".git" / "info"
    git_dir.mkdir(parents=True)
    (git_dir / "exclude").write_text("*.custom", encoding="utf-8")
    with patch.object(Path, "open", side_effect=OSError("Error")):
        assert load_git_exclude_spec(tmp_path) is None


def test_should_skip_dir():
    assert should_skip_dir(".git", include_hidden=True)
    assert should_skip_dir(".git", include_hidden=False)
    assert should_skip_dir(".venv", include_hidden=False)
    assert not should_skip_dir(".venv", include_hidden=True)
    assert not should_skip_dir("src", include_hidden=False)


def test_matches_filter_tags():
    file_info = FileInfo(
        path=Path("foo.py"),
        relative_path=Path("foo.py"),
        tags=frozenset(["python", "text"]),
        shebang="#!/usr/bin/python3",
    )

    # Exclude tags match -> False
    cfg_exclude = TraversalConfig(exclude_tags=frozenset(["text"]))
    assert not matches_filter(file_info, cfg_exclude)

    # Include tags (any) match -> True
    cfg_include_any = TraversalConfig(include_tags=frozenset(["python", "c"]))
    assert matches_filter(file_info, cfg_include_any)

    # Include tags (any) no match -> False
    cfg_include_nomatch = TraversalConfig(include_tags=frozenset(["ruby"]))
    assert not matches_filter(file_info, cfg_include_nomatch)

    # Include tags (all) match -> True
    cfg_include_all = TraversalConfig(
        include_tags=frozenset(["python", "text"]),
        all_tags=True,
    )
    assert matches_filter(file_info, cfg_include_all)

    # Include tags (all) partial match -> False
    cfg_include_all_missing = TraversalConfig(
        include_tags=frozenset(["python", "executable"]),
        all_tags=True,
    )
    assert not matches_filter(file_info, cfg_include_all_missing)


def test_matches_filter_shebang():
    file_info = FileInfo(
        path=Path("script.sh"),
        relative_path=Path("script.sh"),
        shebang="#!/bin/bash",
    )

    cfg_shebang_ok = TraversalConfig(shebang_filter="bash")
    assert matches_filter(file_info, cfg_shebang_ok)

    cfg_shebang_bad = TraversalConfig(shebang_filter="python")
    assert not matches_filter(file_info, cfg_shebang_bad)

    no_shebang_info = FileInfo(path=Path("file.txt"), relative_path=Path("file.txt"))
    assert not matches_filter(no_shebang_info, cfg_shebang_ok)


def test_load_active_specs_no_gitignore(tmp_path: Path):
    specs = _load_active_specs(tmp_path, (), respect_gitignore=False)
    assert specs == ()


def test_is_path_ignored_not_relative(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("*.txt", encoding="utf-8")
    spec = load_gitignore_spec(tmp_path)
    assert spec is not None
    unrelated_path = Path("/other/unrelated/path.txt")
    assert not _is_path_ignored(unrelated_path, is_dir=False, specs=((tmp_path, spec),))


def test_scan_directory_entries_os_error(tmp_path: Path):
    config = TraversalConfig()
    with patch("os.scandir", side_effect=OSError("Permission denied")):
        subdirs, files = _scan_directory_entries(tmp_path, config, ())
        assert subdirs == []
        assert files == []


def test_find_files_single_file_and_missing_root(tmp_path: Path):
    test_file = tmp_path / "single.py"
    test_file.write_text("print('hello')", encoding="utf-8")

    missing = tmp_path / "does_not_exist"
    config = TraversalConfig(root_paths=(test_file, missing))
    results = list(find_files(config))

    assert len(results) == 1
    assert results[0].path == test_file.resolve()


def test_traverse_directory_and_gitignore(sample_repo: Path):
    config = TraversalConfig(root_paths=(sample_repo,))
    results = list(find_files(config))
    rel_paths = [r.relative_path.as_posix() for r in results]

    # Expected included files
    assert "src/app.py" in rel_paths
    assert "src/config.json" in rel_paths
    assert "src/nested/nested.py" in rel_paths
    assert "README.md" in rel_paths
    assert "scripts/runner.sh" in rel_paths
    assert "scripts/mytool" in rel_paths

    # Expected pruned/ignored files
    assert not any("build" in p for p in rel_paths)
    assert not any("debug.log" in p for p in rel_paths)
    assert not any(".nestedignore" in p for p in rel_paths)
    assert not any(".config" in p for p in rel_paths)
    assert not any(".gitexcluded" in p for p in rel_paths)


def test_load_active_specs_with_and_without_git_exclude(tmp_path: Path):
    # Plain dir without git exclude or gitignore
    empty_specs = _load_active_specs(tmp_path, (), respect_gitignore=True)
    assert empty_specs == ()

    # Passing existing active_specs skips root git_exclude check
    dummy_spec = pathspec.PathSpec.from_lines("gitignore", ["*.tmp"])
    existing_tuple = ((tmp_path, dummy_spec),)
    res = _load_active_specs(tmp_path, existing_tuple, respect_gitignore=True)
    assert len(res) == 1


def test_scan_directory_entries_broken_symlink(tmp_path: Path):
    config = TraversalConfig(include_hidden=True)
    broken_link = tmp_path / "broken_link"
    broken_link.symlink_to(tmp_path / "non_existent_target")
    subdirs, files = _scan_directory_entries(tmp_path, config, ())
    assert subdirs == []
    # Broken symlink is not a dir and not a regular file
    assert files == []


def test_find_files_single_file_not_matching_filter(tmp_path: Path):
    txt_file = tmp_path / "data.txt"
    txt_file.write_text("plain text", encoding="utf-8")
    config = TraversalConfig(
        root_paths=(txt_file,),
        include_tags=frozenset(["python"]),
    )
    results = list(find_files(config))
    assert results == []


def test_find_files_fifo_root(tmp_path: Path):
    fifo_path = tmp_path / "test.fifo"
    try:
        os.mkfifo(fifo_path)
    except (AttributeError, OSError):
        return  # Non-posix fallback

    config = TraversalConfig(root_paths=(fifo_path,))
    results = list(find_files(config))
    assert results == []


def test_traverse_directory_symlink_cycle(tmp_path: Path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    target_file = sub / "file.py"
    target_file.write_text("print('cycle')", encoding="utf-8")

    cycle_link = sub / "loop"
    cycle_link.symlink_to(sub, target_is_directory=True)

    config = TraversalConfig(root_paths=(tmp_path,), follow_symlinks=True)
    results = list(find_files(config))
    rel_names = [r.path.name for r in results]
    assert rel_names == ["file.py"]


def test_traverse_directory_follow_symlinks_tree(tmp_path: Path):
    external_dir = tmp_path.parent / f"{tmp_path.name}_external"
    external_dir.mkdir(exist_ok=True)
    (external_dir / "nested.py").write_text("x = 1", encoding="utf-8")

    link_dir = tmp_path / "link_dir"
    link_dir.symlink_to(external_dir, target_is_directory=True)

    config = TraversalConfig(root_paths=(tmp_path,), follow_symlinks=True)
    results = list(find_files(config))
    file_names = [r.path.name for r in results]
    assert file_names == ["nested.py"]


def test_traverse_directory_resolve_root_os_error(tmp_path: Path):
    (tmp_path / "test.py").write_text("print(1)", encoding="utf-8")
    config = TraversalConfig(follow_symlinks=True)

    orig_resolve = Path.resolve

    def mock_resolve(self: Path, *args, **kwargs):
        if self == tmp_path:
            raise OSError

        return orig_resolve(self, *args, **kwargs)

    with patch.object(Path, "resolve", autospec=True, side_effect=mock_resolve):
        res = list(traverse_directory(tmp_path, config))
        assert len(res) == 1


def test_traverse_directory_resolve_subdir_os_error(tmp_path: Path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.py").write_text("print(1)", encoding="utf-8")
    config = TraversalConfig(follow_symlinks=True)

    orig_resolve = Path.resolve

    def mock_resolve(self: Path, *args, **kwargs):
        if self.name == "sub":
            raise OSError

        return orig_resolve(self, *args, **kwargs)

    with patch.object(Path, "resolve", autospec=True, side_effect=mock_resolve):
        res = list(traverse_directory(tmp_path, config))
        assert res == []
