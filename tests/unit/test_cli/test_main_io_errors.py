"""Unit tests for findfmt CLI atomic output writing, exit codes, and traversal I/O errors."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from findfmt.cli import app


def test_output_file_written_atomically(tmp_path: Path) -> None:
    """Verify -o/--output writes atomically via temporary file and os.replace."""
    runner = CliRunner()
    target_file = tmp_path / "output.txt"
    sample_file = tmp_path / "sample.py"
    sample_file.write_text("print('hello')\n", encoding="utf-8")

    # 1. Clean completion: verify atomic replace occurred and file content is correct
    with patch("os.replace", wraps=os.replace) as mock_replace:
        result = runner.invoke(app, [str(sample_file), "-o", str(target_file)])
        assert result.exit_code == 0
        assert mock_replace.called
        src_arg, dst_arg = mock_replace.call_args[0]
        assert Path(dst_arg).resolve() == target_file.resolve()
        assert Path(src_arg).parent.resolve() == target_file.parent.resolve()
        assert str(src_arg) != str(dst_arg)

    assert target_file.is_file()
    assert "sample.py" in target_file.read_text(encoding="utf-8")

    # Verify no temporary staging files remain in destination directory
    tmp_files = [
        p for p in tmp_path.iterdir() if p.name.startswith(".") and p.name.endswith(".tmp")
    ]
    assert tmp_files == []

    # 2. Simulated crash with pre-existing destination file: prior contents remain untouched
    target_file.write_text("prior pristine content", encoding="utf-8")
    crash_msg = "Simulated crash"

    with (
        patch("findfmt.cli.runner.find_files", side_effect=RuntimeError(crash_msg)),
        pytest.raises(RuntimeError, match=crash_msg),
    ):
        runner.invoke(app, [str(sample_file), "-o", str(target_file)], catch_exceptions=False)

    assert target_file.read_text(encoding="utf-8") == "prior pristine content"
    tmp_files = [
        p for p in tmp_path.iterdir() if p.name.startswith(".") and p.name.endswith(".tmp")
    ]
    assert tmp_files == []

    # 3. Simulated crash where target file did not previously exist: no partial file exists
    new_target = tmp_path / "never_created.txt"
    with (
        patch("findfmt.cli.runner.find_files", side_effect=RuntimeError(crash_msg)),
        pytest.raises(RuntimeError, match=crash_msg),
    ):
        runner.invoke(app, [str(sample_file), "-o", str(new_target)], catch_exceptions=False)

    assert not new_target.exists()
    tmp_files = [
        p for p in tmp_path.iterdir() if p.name.startswith(".") and p.name.endswith(".tmp")
    ]
    assert tmp_files == []


def test_output_file_open_failure_exit_code(tmp_path: Path) -> None:
    """Verify target file open failures exit with code 2."""
    runner = CliRunner()
    sample_file = tmp_path / "sample.py"
    sample_file.write_text("print('hello')\n", encoding="utf-8")

    # Non-existent directory
    invalid_path = tmp_path / "nonexistent_dir" / "out.txt"
    result = runner.invoke(app, [str(sample_file), "-o", str(invalid_path)])
    assert result.exit_code == 2
    assert "Error opening output file" in result.stderr

    # Target path is an existing directory
    dir_target = tmp_path / "existing_dir"
    dir_target.mkdir()
    result_dir = runner.invoke(app, [str(sample_file), "-o", str(dir_target)])
    assert result_dir.exit_code == 2
    assert "Error opening output file" in result_dir.stderr


def test_exit_status_flag_no_matches_returns_1(sample_repo: Path) -> None:
    """Verify --exit-status exits with status 1 on zero matches, 0 otherwise."""
    runner = CliRunner()
    res = runner.invoke(app, [str(sample_repo), "-t", "nonexistent-tag-xyz", "--exit-status"])
    assert res.exit_code == 1
    assert runner.invoke(app, [str(sample_repo), "-t", "nonexistent-tag-xyz"]).exit_code == 0
    assert runner.invoke(app, [str(sample_repo), "--exit-status"]).exit_code == 0


def test_missing_path_reports_error_and_exits_1(tmp_path: Path) -> None:
    """Verify missing root path emits stderr diagnostic and exits with code 1."""
    missing = tmp_path / "nonexistent"
    res = CliRunner().invoke(app, [str(missing)])
    assert res.exit_code == 1
    assert "cannot open" in res.stderr
    assert str(missing) in res.stderr


def test_missing_and_existing_paths_mixed(tmp_path: Path) -> None:
    """Verify existing paths are still output when mixed with missing paths, exiting 1."""
    valid_dir = tmp_path / "valid"
    valid_dir.mkdir()
    (valid_dir / "found.py").write_text("x = 1\n", encoding="utf-8")
    missing = tmp_path / "missing"
    res = CliRunner().invoke(app, [str(missing), str(valid_dir)])
    assert res.exit_code == 1
    assert "found.py" in res.stdout
    assert "cannot open" in res.stderr
    assert str(missing) in res.stderr


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="chmod 000 permissions not enforced on Windows or for root",
)
def test_unreadable_subdirectory_reports_and_continues(tmp_path: Path) -> None:
    """Verify unreadable subdirectory emits one stderr line, lists siblings, and exits 1."""
    runner = CliRunner()
    (tmp_path / "sibling.py").write_text("x = 1\n", encoding="utf-8")
    unreadable = tmp_path / "locked"
    unreadable.mkdir()
    unreadable.chmod(0o000)
    try:
        res = runner.invoke(app, [str(tmp_path)])
        assert res.exit_code == 1
        assert "sibling.py" in res.stdout
        err_lines = [line for line in res.stderr.splitlines() if line.strip()]
        assert len(err_lines) == 1
        assert "cannot open" in err_lines[0]
        assert str(unreadable) in err_lines[0]
    finally:
        unreadable.chmod(0o755)


def test_help_all_exit_code_table_matches_behaviour(tmp_path: Path) -> None:
    """Parse the exit-code table from --help-all and assert each documented code is produced."""
    runner = CliRunner()
    help_res = runner.invoke(app, ["--help-all"])
    assert help_res.exit_code == 0
    section = help_res.stdout.split("Exit Codes:\n", 1)[1].split("\n\n", 1)[0]
    documented_codes = {
        int(m.group(1)) for line in section.splitlines() if (m := re.match(r"^\s+(\d+)\s+", line))
    }
    assert documented_codes == {0, 1, 2, 130}

    assert runner.invoke(app, [str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, [str(tmp_path / "missing")]).exit_code == 1
    assert runner.invoke(app, ["--unknown-flag"]).exit_code == 2
    with patch("findfmt.cli.runner.find_files", side_effect=KeyboardInterrupt):
        assert runner.invoke(app, [str(tmp_path)]).exit_code == 130
