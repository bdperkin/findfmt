"""Unit tests for CLI sorting flags, grouping options, and validation handling."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.cli.config import build_traversal_config, validate_cli_options
from findfmt.formatters import OutputFormat
from findfmt.models import SortKey

runner = CliRunner()


def test_cli_sort_version_and_reverse(tmp_path: Path) -> None:
    """Verify --sort=version and -r CLI behavior."""
    (tmp_path / "item1.txt").write_text("1")
    (tmp_path / "item2.txt").write_text("2")
    (tmp_path / "item10.txt").write_text("10")

    result = runner.invoke(app, [str(tmp_path), "--sort", "version", "--no-pager"])
    assert result.exit_code == 0
    lines = [line.strip() for line in result.output.strip().splitlines() if line.strip()]
    assert lines == ["item1.txt", "item2.txt", "item10.txt"]

    # Reverse version
    res_rev = runner.invoke(app, [str(tmp_path), "--sort", "version", "-r", "--no-pager"])
    assert res_rev.exit_code == 0
    lines_rev = [line.strip() for line in res_rev.output.strip().splitlines() if line.strip()]
    assert lines_rev == ["item10.txt", "item2.txt", "item1.txt"]


def test_cli_unsorted_and_sort_none(tmp_path: Path) -> None:
    """Verify -U and --sort=none CLI execution."""
    (tmp_path / "alpha.txt").write_text("a")
    (tmp_path / "beta.txt").write_text("b")

    res_u = runner.invoke(app, [str(tmp_path), "-U", "--no-pager"])
    assert res_u.exit_code == 0

    res_none = runner.invoke(app, [str(tmp_path), "--sort", "none", "--no-pager"])
    assert res_none.exit_code == 0


def _normalize_lines(output: str) -> list[str]:
    return [line.strip().replace("\\", "/") for line in output.strip().splitlines() if line.strip()]


def test_cli_dirsfirst_and_filesfirst(tmp_path: Path) -> None:
    """Verify --dirsfirst and --filesfirst CLI flags."""
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    (sub_dir / "child.txt").write_text("c")
    (tmp_path / "root.txt").write_text("r")

    # --dirsfirst
    res_df = runner.invoke(app, [str(tmp_path), "--dirsfirst", "--no-pager"])
    assert res_df.exit_code == 0
    assert _normalize_lines(res_df.output) == ["subdir/child.txt", "root.txt"]

    # --group-directories-first alias
    res_gdf = runner.invoke(app, [str(tmp_path), "--group-directories-first", "--no-pager"])
    assert res_gdf.exit_code == 0
    assert _normalize_lines(res_gdf.output) == ["subdir/child.txt", "root.txt"]

    # --filesfirst
    res_ff = runner.invoke(app, [str(tmp_path), "--filesfirst", "--no-pager"])
    assert res_ff.exit_code == 0
    assert _normalize_lines(res_ff.output) == ["root.txt", "subdir/child.txt"]


def test_cli_conflicting_grouping_options(tmp_path: Path) -> None:
    """Verify mutual exclusivity validation when specifying both dirsfirst and filesfirst."""
    result = runner.invoke(app, [str(tmp_path), "--dirsfirst", "--filesfirst"])
    assert result.exit_code == 2
    assert "Cannot specify both --dirsfirst and --filesfirst" in result.output


def test_cli_invalid_sort_option(tmp_path: Path) -> None:
    """Verify validation error when passing an unrecognized sort criterion."""
    result = runner.invoke(app, [str(tmp_path), "--sort", "unrecognized"])
    assert result.exit_code == 2
    assert "Invalid sort criteria 'unrecognized'" in result.output


def test_build_traversal_config_options() -> None:
    """Verify build_traversal_config correctly maps all parameters to TraversalConfig."""
    cfg = build_traversal_config(
        [Path("/test")],
        ["python"],
        ["draft"],
        all_tags=True,
        shebang="python",
        no_ignore=True,
        hidden=True,
        follow_symlinks=True,
        dirs_only=True,
        one_file_system=True,
        max_depth=3,
        file_limit=50,
        prune=True,
        pattern=["*.py"],
        exclude_pattern=["test_*"],
        ignore_case=True,
        match_dirs=True,
        absolute=True,
        relative=True,
        print0=True,
        list_tags=True,
        summary=True,
        output_format=OutputFormat.JSON,
        sort="size",
        reverse=True,
        dirs_first=True,
        files_first=False,
    )
    assert cfg.sort_by == SortKey.SIZE
    assert cfg.reverse_sort
    assert cfg.dirs_first
    assert not cfg.files_first
    assert cfg.output_format == "json"


def test_validate_cli_options_missing_gitignore(tmp_path: Path) -> None:
    """Verify validate_cli_options rejects non-existent gitignore_file path."""
    with pytest.raises(typer.Exit) as exc_info:
        validate_cli_options(
            gitignore_file=tmp_path / "nonexistent.ignore",
            sort=None,
            unsorted=False,
            dirs_first=False,
            files_first=False,
        )

    assert exc_info.value.exit_code == 2
