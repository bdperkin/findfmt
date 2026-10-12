"""Unit tests for relative path prefixing (--relative / --no-relative)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.cli_help import get_help_all
from findfmt.models import TraversalConfig
from findfmt.traversal import find_files


@pytest.fixture
def multi_dir_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    """Create two directories with sample files inside a working directory."""
    monkeypatch.chdir(tmp_path)
    dir_a = tmp_path / "dir_a"
    dir_b = tmp_path / "dir_b"
    dir_a.mkdir()
    dir_b.mkdir()

    (dir_a / "first.py").write_text("print(1)\n", encoding="utf-8")
    (dir_a / "second.json").write_text("{}\n", encoding="utf-8")
    (dir_b / "third.py").write_text("print(3)\n", encoding="utf-8")

    return tmp_path, dir_a, dir_b


def test_traversal_relative_prefix_disabled_by_default(
    multi_dir_setup: tuple[Path, Path, Path],
) -> None:
    """Verify that by default relative_prefix is disabled and roots are stripped."""
    tmp_path, dir_a, _ = multi_dir_setup
    config = TraversalConfig(
        root_paths=(dir_a.relative_to(tmp_path),),
        relative_prefix=False,
    )
    results = list(find_files(config))
    rel_names = {r.relative_path.as_posix() for r in results}

    assert "first.py" in rel_names
    assert "second.json" in rel_names
    assert "dir_a/first.py" not in rel_names


def test_traversal_relative_prefix_single_directory(
    multi_dir_setup: tuple[Path, Path, Path],
) -> None:
    """Verify that relative_prefix=True preserves input directory prefix."""
    tmp_path, dir_a, _ = multi_dir_setup
    config = TraversalConfig(
        root_paths=(dir_a.relative_to(tmp_path),),
        relative_prefix=True,
    )
    results = list(find_files(config))
    rel_names = {r.relative_path.as_posix() for r in results}

    assert "dir_a/first.py" in rel_names
    assert "dir_a/second.json" in rel_names
    assert "first.py" not in rel_names


def test_traversal_relative_prefix_multiple_directories(
    multi_dir_setup: tuple[Path, Path, Path],
) -> None:
    """Verify that relative_prefix=True prefixes each file with its respective root."""
    tmp_path, dir_a, dir_b = multi_dir_setup
    config = TraversalConfig(
        root_paths=(dir_a.relative_to(tmp_path), dir_b.relative_to(tmp_path)),
        relative_prefix=True,
    )
    results = list(find_files(config))
    rel_names = {r.relative_path.as_posix() for r in results}

    assert "dir_a/first.py" in rel_names
    assert "dir_a/second.json" in rel_names
    assert "dir_b/third.py" in rel_names


def test_traversal_relative_prefix_single_file(
    multi_dir_setup: tuple[Path, Path, Path],
) -> None:
    """Verify that single file paths retain their input relative prefix."""
    tmp_path, dir_a, _ = multi_dir_setup
    file_path = (dir_a / "first.py").relative_to(tmp_path)
    config = TraversalConfig(root_paths=(file_path,), relative_prefix=True)
    results = list(find_files(config))
    assert len(results) == 1
    assert results[0].relative_path == file_path

    # Verify behavior when prefixing is disabled
    config_disabled = TraversalConfig(root_paths=(file_path,), relative_prefix=False)
    results_disabled = list(find_files(config_disabled))
    assert len(results_disabled) == 1
    assert results_disabled[0].relative_path == Path("first.py")


@pytest.mark.usefixtures("multi_dir_setup")
def test_cli_relative_flags_toggle() -> None:
    """Test --relative and negative toggle --no-relative via CLI."""
    runner = CliRunner()

    res_default = runner.invoke(app, ["dir_a/"])
    assert res_default.exit_code == 0
    stdout_default = res_default.stdout.replace("\\", "/")
    assert "first.py" in stdout_default
    assert "dir_a/first.py" not in stdout_default

    res_rel = runner.invoke(app, ["dir_a/", "--relative"])
    assert res_rel.exit_code == 0
    stdout_rel = res_rel.stdout.replace("\\", "/")
    assert "dir_a/first.py" in stdout_rel

    res_rel_path = runner.invoke(app, ["dir_a/", "--relative-path"])
    assert res_rel_path.exit_code == 0
    stdout_rel_path = res_rel_path.stdout.replace("\\", "/")
    assert "dir_a/first.py" in stdout_rel_path

    res_no_rel = runner.invoke(app, ["dir_a/", "--relative", "--no-relative"])
    assert res_no_rel.exit_code == 0
    stdout_no_rel = res_no_rel.stdout.replace("\\", "/")
    assert "dir_a/first.py" not in stdout_no_rel
    assert "first.py" in stdout_no_rel

    res_no_rel_path = runner.invoke(app, ["dir_a/", "--relative", "--no-relative-path"])
    assert res_no_rel_path.exit_code == 0
    stdout_no_rel_path = res_no_rel_path.stdout.replace("\\", "/")
    assert "dir_a/first.py" not in stdout_no_rel_path


@pytest.mark.usefixtures("multi_dir_setup")
def test_cli_relative_multiple_paths() -> None:
    """Test CLI behavior with multiple directory inputs and --relative."""
    runner = CliRunner()
    result = runner.invoke(app, ["dir_a", "dir_b", "--relative"])
    assert result.exit_code == 0
    stdout = result.stdout.replace("\\", "/")
    assert "dir_a/first.py" in stdout
    assert "dir_a/second.json" in stdout
    assert "dir_b/third.py" in stdout


@pytest.mark.usefixtures("multi_dir_setup")
def test_cli_relative_single_file() -> None:
    """Test CLI behavior with single file input and --relative."""
    runner = CliRunner()
    result = runner.invoke(app, ["dir_a/first.py", "--relative"])
    assert result.exit_code == 0
    assert "dir_a/first.py" in result.stdout.replace("\\", "/")


@pytest.mark.usefixtures("multi_dir_setup")
def test_cli_relative_current_directory() -> None:
    """Test that current directory (.) does not add ./ clutter with --relative."""
    runner = CliRunner()
    result = runner.invoke(app, [".", "--relative"])
    assert result.exit_code == 0
    stdout = result.stdout.replace("\\", "/")
    assert "dir_a/first.py" in stdout
    assert "./dir_a/first.py" not in stdout


@pytest.mark.usefixtures("multi_dir_setup")
def test_cli_relative_all_formats() -> None:
    """Test that --relative behaves consistently across all serialized formats."""
    runner = CliRunner()
    formats = [
        "text",
        "json",
        "jsonl",
        "yaml",
        "csv",
        "tsv",
        "markdown",
        "rst",
        "table",
        "tree",
        "csv-table",
    ]

    for fmt in formats:
        res = runner.invoke(app, ["dir_a", "--relative", "-f", fmt])
        assert res.exit_code == 0, f"Format {fmt} failed with code {res.exit_code}"
        output = res.stdout.replace("\\", "/")
        assert "dir_a" in output, f"Format {fmt} did not contain 'dir_a'"

    # Verify structured JSON output contains prefixed path
    res_json = runner.invoke(app, ["dir_a", "--relative", "-f", "json"])
    data = json.loads(res_json.stdout)
    paths = [item["path"].replace("\\", "/") for item in data]
    rel_paths = [item["relative_path"].replace("\\", "/") for item in data]
    assert any("dir_a/first.py" in p for p in paths)
    assert any("dir_a/first.py" in p for p in rel_paths)


@pytest.mark.usefixtures("multi_dir_setup")
def test_cli_relative_with_absolute_precedence() -> None:
    """Verify --absolute emits absolute paths while structured records keep relative_path."""
    runner = CliRunner()
    res = runner.invoke(app, ["dir_a", "--relative", "--absolute", "-f", "json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert len(data) >= 1
    # 'path' must be absolute
    assert Path(data[0]["path"]).is_absolute()
    # 'relative_path' must preserve the relative prefix
    rel_path_norm = data[0]["relative_path"].replace("\\", "/")
    assert rel_path_norm.startswith("dir_a")


def test_cli_help_all_includes_relative() -> None:
    """Verify that get_help_all and --help include the --relative options."""
    manual = get_help_all()
    assert "--relative" in manual
    assert "--relative-path" in manual

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--relative" in result.stdout
    assert "--no-relative" in result.stdout
