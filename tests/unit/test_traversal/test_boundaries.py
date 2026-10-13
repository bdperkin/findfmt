"""Unit tests for traversal boundaries, device checks, depth limits, and pruning."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pathspec

from findfmt.models import TraversalConfig
from findfmt.traversal.boundaries import (
    _inspect_entries,
    check_depth_limit,
    check_device_boundary,
    check_file_limit,
    filter_directory_entry,
    has_matching_descendants,
    init_visited_dirs,
    resolve_active_specs,
    resolve_device,
    should_skip_symlink_dir,
    yield_matching_items,
)


def test_init_visited_dirs(tmp_path: Path) -> None:
    """Verify visited directory tracker initialization and error suppression."""
    assert init_visited_dirs(tmp_path, follow_symlinks=False, visited=None) is None

    existing: set[Path] = {tmp_path}
    assert init_visited_dirs(tmp_path, follow_symlinks=True, visited=existing) is existing

    created = init_visited_dirs(tmp_path, follow_symlinks=True, visited=None)
    assert created == {tmp_path.resolve()}

    with patch.object(Path, "resolve", side_effect=OSError("Access denied")):
        error_res = init_visited_dirs(tmp_path, follow_symlinks=True, visited=None)
        assert error_res == set()


def test_should_skip_symlink_dir(tmp_path: Path) -> None:
    """Verify loop prevention when traversing directory symlinks."""
    d = tmp_path / "sub"
    d.mkdir()
    assert not should_skip_symlink_dir(d, follow_symlinks=False, visited=None)
    assert not should_skip_symlink_dir(d, follow_symlinks=True, visited=None)

    visited: set[Path] = set()
    assert not should_skip_symlink_dir(d, follow_symlinks=True, visited=visited)
    assert d.resolve() in visited
    assert should_skip_symlink_dir(d, follow_symlinks=True, visited=visited)

    with patch.object(Path, "resolve", side_effect=OSError("Broken link")):
        assert should_skip_symlink_dir(d, follow_symlinks=True, visited=visited)


def test_resolve_active_specs(tmp_path: Path) -> None:
    """Verify resolution of active specs based on gitignore configuration."""
    assert resolve_active_specs(tmp_path, None, respect_gitignore=False) == ()

    mock_spec: pathspec.PathSpec[Any] = pathspec.PathSpec([])
    specs: tuple[tuple[Path, pathspec.PathSpec[Any]], ...] = ((tmp_path, mock_spec),)
    assert resolve_active_specs(tmp_path, specs, respect_gitignore=True) == specs

    ancestor = resolve_active_specs(tmp_path, None, respect_gitignore=True)
    assert isinstance(ancestor, tuple)


def test_check_device_boundary(tmp_path: Path) -> None:
    """Verify one-filesystem boundary checks and error handling."""
    assert check_device_boundary(tmp_path, None) is True

    current_dev = tmp_path.stat().st_dev
    assert check_device_boundary(tmp_path, current_dev) is True
    assert check_device_boundary(tmp_path, current_dev + 1) is False

    with patch.object(Path, "stat", side_effect=OSError("stat error")):
        assert check_device_boundary(tmp_path, current_dev) is False


def test_resolve_device(tmp_path: Path) -> None:
    """Verify filesystem device resolution logic."""
    assert resolve_device(tmp_path, one_file_system=False, root_dev=None) is None
    assert resolve_device(tmp_path, one_file_system=True, root_dev=999) == 999

    dev = resolve_device(tmp_path, one_file_system=True, root_dev=None)
    assert dev == tmp_path.stat().st_dev

    with patch.object(Path, "stat", side_effect=OSError("stat error")):
        assert resolve_device(tmp_path, one_file_system=True, root_dev=None) is None


def test_check_file_limit() -> None:
    """Verify file entry limit checks."""
    assert check_file_limit(10, None) is True
    assert check_file_limit(5, 5) is True
    assert check_file_limit(4, 5) is True
    assert check_file_limit(6, 5) is False


def test_check_depth_limit() -> None:
    """Verify traversal max depth limits."""
    assert check_depth_limit(1, None) is True
    assert check_depth_limit(1, 2) is True
    assert check_depth_limit(2, 2) is False
    assert check_depth_limit(3, 2) is False


def test_filter_directory_entry(tmp_path: Path) -> None:
    """Verify entry filtering on hidden files, device boundary, and gitignore."""
    config = TraversalConfig(include_hidden=False, respect_gitignore=True)
    entry = MagicMock(spec=os.DirEntry)
    entry.name = ".hidden"
    entry.path = str(tmp_path / ".hidden")
    assert filter_directory_entry(entry, config, (), None) is None

    entry.name = "visible.txt"
    entry.path = str(tmp_path / "visible.txt")
    with patch("findfmt.traversal.boundaries.check_device_boundary", return_value=False):
        assert filter_directory_entry(entry, config, (), 123) is None

    with (
        patch("findfmt.traversal.boundaries.check_device_boundary", return_value=True),
        patch("findfmt.traversal.boundaries.is_path_ignored", return_value=True),
    ):
        entry.is_dir.return_value = False
        assert filter_directory_entry(entry, config, (), None) is None

    with (
        patch("findfmt.traversal.boundaries.check_device_boundary", return_value=True),
        patch("findfmt.traversal.boundaries.is_path_ignored", return_value=False),
    ):
        entry.is_dir.return_value = False
        res = filter_directory_entry(entry, config, (), None)
        assert res == (Path(entry.path), False)


def test_has_matching_descendants_and_inspect_entries(tmp_path: Path) -> None:
    """Verify detection of matching files across directory trees."""
    config = TraversalConfig(include_tags=frozenset({"python"}))
    with patch("os.scandir", side_effect=OSError("perm error")):
        assert has_matching_descendants(tmp_path, config, ()) is False

    empty_sub = tmp_path / "empty_dir"
    empty_sub.mkdir()
    assert has_matching_descendants(empty_sub, config, ()) is False

    py_file = empty_sub / "test.py"
    py_file.write_text("print(1)\n")
    assert has_matching_descendants(tmp_path, config, ()) is True

    # Multi-subdir traversal: first subdir has no matches, second has matches
    tree_root = tmp_path / "tree_root"
    tree_root.mkdir()
    (tree_root / "sub1").mkdir()
    sub2 = tree_root / "sub2"
    sub2.mkdir()
    (sub2 / "sample.py").write_text("print(2)\n")
    assert has_matching_descendants(tree_root, config, ()) is True

    # Multi-subdir traversal where no subdir contains matches
    no_matches_dir = tmp_path / "no_matches_dir"
    no_matches_dir.mkdir()
    (no_matches_dir / "empty_a").mkdir()
    (no_matches_dir / "empty_b").mkdir()
    assert has_matching_descendants(no_matches_dir, config, ()) is False

    # Depth limit prevents detection in subdirectories
    config_depth = TraversalConfig(include_tags=frozenset({"python"}), max_depth=1)
    assert has_matching_descendants(tmp_path, config_depth, (), current_depth=1) is False

    # Immediate file inspect with skipped directory and non-file entry
    entries = list(os.scandir(empty_sub))
    subdirs, found = _inspect_entries(entries, config, (), None)
    assert found is True
    assert subdirs == []

    # Mock entries covering should_skip_dir and not entry.is_file
    mock_git_dir = MagicMock(spec=os.DirEntry)
    mock_git_dir.name = ".git"
    mock_git_dir.path = str(tmp_path / ".git")
    mock_git_dir.is_dir.return_value = True

    mock_other = MagicMock(spec=os.DirEntry)
    mock_other.name = "special_device"
    mock_other.path = str(tmp_path / "special_device")
    mock_other.is_dir.return_value = False
    mock_other.is_file.return_value = False

    mock_entries: list[Any] = [mock_git_dir, mock_other]
    config_hidden = TraversalConfig(include_hidden=True)
    subdirs_mock, found_mock = _inspect_entries(mock_entries, config_hidden, (), None)
    assert found_mock is False
    assert subdirs_mock == []


def test_yield_matching_items(tmp_path: Path) -> None:
    """Verify candidate item emission with dirs_only and prune_empty settings."""
    sub_empty = tmp_path / "empty"
    sub_empty.mkdir()
    sub_with_file = tmp_path / "with_py"
    sub_with_file.mkdir()
    (sub_with_file / "a.py").write_text("x = 1\n")

    config = TraversalConfig(
        dirs_only=True,
        prune_empty=True,
        include_tags=frozenset({"python"}),
    )
    results = list(
        yield_matching_items(
            [sub_empty, sub_with_file],
            config,
            (),
            base_root=tmp_path,
            prefix=None,
            root_dev=None,
            current_depth=1,
        ),
    )
    assert len(results) == 1
    assert results[0].path == sub_with_file.resolve()
