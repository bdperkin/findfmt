"""Unit tests for CLI traversal boundaries: -d, -l, -x, -L, --filelimit, --prune."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.models import TraversalConfig
from findfmt.traversal import find_files


def test_cli_dirs_only(sample_repo: Path) -> None:
    """Verify -d and --dirs-only flag outputs only directories."""
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-d"])
    assert result.exit_code == 0
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert "src" in lines
    assert "scripts" in lines
    # Regular files must be suppressed
    assert not any(line.endswith(".py") for line in lines)

    result_long = runner.invoke(app, [str(sample_repo), "--dirs-only"])
    assert result_long.exit_code == 0
    assert "src" in result_long.stdout


def test_find_files_single_file_dirs_only(sample_repo: Path) -> None:
    """Verify single file root path with dirs_only produces no items."""
    target_file = sample_repo / "src" / "app.py"
    config = TraversalConfig(root_paths=(target_file,), dirs_only=True)
    items = list(find_files(config))
    assert items == []


def test_cli_max_depth(sample_repo: Path) -> None:
    """Verify -L and --max-depth restrict directory descent."""
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-L", "1"])
    assert result.exit_code == 0
    # Depth 1 only includes immediate root entries, not src/app.py or src/nested/nested.py
    assert "nested.py" not in result.stdout

    result_long = runner.invoke(app, [str(sample_repo), "--max-depth", "2"])
    assert result_long.exit_code == 0
    assert "app.py" in result_long.stdout
    assert "nested.py" not in result_long.stdout


def test_cli_filelimit(sample_repo: Path) -> None:
    """Verify --filelimit skips directories exceeding threshold."""
    runner = CliRunner()
    # Setting threshold to 1 skips src/ which has app.py, config.json, and nested/
    result = runner.invoke(app, [str(sample_repo), "--filelimit", "1"])
    assert result.exit_code == 0
    assert "app.py" not in result.stdout


def test_cli_prune(sample_repo: Path) -> None:
    """Verify --prune suppresses directories without matching files."""
    empty_dir = sample_repo / "empty_dir"
    empty_dir.mkdir()

    runner = CliRunner()
    # Search for json files with --prune in dirs-only mode
    result = runner.invoke(app, [str(sample_repo), "-t", "json", "-d", "--prune"])
    assert result.exit_code == 0
    assert "empty_dir" not in result.stdout
    assert "src" in result.stdout
    assert "scripts" not in result.stdout


def test_cli_one_file_system(sample_repo: Path) -> None:
    """Verify -x and --one-file-system restrict traversal to starting device."""
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-x"])
    assert result.exit_code == 0
    assert "app.py" in result.stdout

    result_long = runner.invoke(app, [str(sample_repo), "--one-file-system"])
    assert result_long.exit_code == 0

    with patch("os.scandir") as mock_scandir:
        entry = MagicMock(spec=os.DirEntry)
        entry.name = "diff_dev"
        entry.path = str(sample_repo / "diff_dev")
        entry.is_dir.return_value = True
        mock_scandir.return_value = [entry]
        with patch("findfmt.traversal.boundaries.check_device_boundary", return_value=False):
            res = runner.invoke(app, [str(sample_repo), "-x"])
            assert res.exit_code == 0


def test_symlink_loop_detection(tmp_path: Path) -> None:
    """Verify directory symlink cycle breaks without recursion error."""
    dir_a = tmp_path / "dir_a"
    dir_a.mkdir()
    (dir_a / "file_a.py").write_text("a = 1\n")

    dir_b = tmp_path / "dir_b"
    dir_b.mkdir()
    (dir_b / "file_b.py").write_text("b = 2\n")

    # Create recursive symlinks: dir_a/link_b -> dir_b, dir_b/link_a -> dir_a
    try:
        (dir_a / "link_b").symlink_to(dir_b, target_is_directory=True)
        (dir_b / "link_a").symlink_to(dir_a, target_is_directory=True)
    except OSError:  # pragma: no cover
        return  # Skip if filesystem does not support symlinks

    runner = CliRunner()
    result = runner.invoke(app, [str(dir_a), "-l"])
    assert result.exit_code == 0
    assert "file_a.py" in result.stdout
    assert "file_b.py" in result.stdout
