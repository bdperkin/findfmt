"""Unit tests for findfmt Typer CLI application and flags."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.entrypoints import (
    main_findfilefmt,
    main_findfilemime,
    main_findfiles,
    main_findfmt0,
    main_findshebang,
    main_findsummary,
)
from findfmt.summary import parse_tag_arguments


def test_parse_tag_arguments():
    assert parse_tag_arguments(None) == frozenset()
    assert parse_tag_arguments([]) == frozenset()
    assert parse_tag_arguments(["python", "yaml"]) == frozenset(["python", "yaml"])
    assert parse_tag_arguments(["python,yaml", "json"]) == frozenset(
        ["python", "yaml", "json"],
    )
    assert parse_tag_arguments(["  PYTHON  ", ",,"]) == frozenset(["python"])


def test_cli_tag_filter(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-t", "python"])
    assert result.exit_code == 0
    assert "src/app.py" in result.stdout.replace("\\", "/")
    assert "README.md" not in result.stdout

    # Case insensitivity
    result_upper = runner.invoke(app, [str(sample_repo), "-t", "PYTHON"])
    assert result_upper.exit_code == 0
    assert "src/app.py" in result_upper.stdout.replace("\\", "/")


def test_cli_exclude_tags(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-t", "python", "-e", "executable"])
    assert result.exit_code == 0
    lines = result.stdout.strip().split("\n")
    assert any("app.py" in line for line in lines)
    assert not any("mytool" in line for line in lines)


def test_cli_all_tags(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-t", "python,executable", "--all-tags"])
    assert result.exit_code == 0
    lines = result.stdout.strip().split("\n")
    assert any("mytool" in line for line in lines)
    assert not any("app.py" in line for line in lines)


def test_cli_shebang_filter(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "--shebang", "bash"])
    assert result.exit_code == 0
    lines = result.stdout.strip().split("\n")
    assert any("runner.sh" in line for line in lines)
    assert not any("mytool" in line for line in lines)


def test_cli_no_ignore(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "--no-ignore"])
    assert result.exit_code == 0
    assert "debug.log" in result.stdout


def test_cli_hidden(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "--hidden"])
    assert result.exit_code == 0
    assert "settings.yaml" in result.stdout

    result_a = runner.invoke(app, [str(sample_repo), "-a"])
    assert result_a.exit_code == 0
    assert "settings.yaml" in result_a.stdout

    result_all = runner.invoke(app, [str(sample_repo), "--all"])
    assert result_all.exit_code == 0
    assert "settings.yaml" in result_all.stdout

    result_no_all = runner.invoke(app, [str(sample_repo), "--no-all"])
    assert result_no_all.exit_code == 0
    assert "settings.yaml" not in result_no_all.stdout


def test_cli_follow_symlinks(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-l"])
    assert result.exit_code == 0

    result_long = runner.invoke(app, [str(sample_repo), "--follow-links"])
    assert result_long.exit_code == 0


def test_cli_print0(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-t", "python", "-0"])
    assert result.exit_code == 0
    assert "\0" in result.stdout
    assert "\n" not in result.stdout


def test_cli_list_tags(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-t", "python", "--list-tags"])
    assert result.exit_code == 0
    assert "[" in result.stdout
    assert "python" in result.stdout


def test_cli_summary(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-s"])
    assert result.exit_code == 0
    assert "--- findfmt summary ---" in result.stderr
    assert "Matched files:" in result.stderr


def test_cli_absolute(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-t", "python", "--absolute"])
    assert result.exit_code == 0
    lines = result.stdout.strip().split("\n")
    for line in lines:
        if line.strip():
            assert Path(line).is_absolute()


def test_cli_summary_no_matches(tmp_path: Path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    runner = CliRunner()
    result = runner.invoke(app, [str(empty_dir), "-t", "nonexistent_tag", "-s"])
    assert result.exit_code == 0
    assert "Matched files: 0" in result.stderr
    assert "Top tags:" not in result.stderr


def test_cli_flag_negations(sample_repo: Path):
    runner = CliRunner()

    res = runner.invoke(app, [str(sample_repo), "--no-all-tags", "-t", "python"])
    assert res.exit_code == 0
    assert "src/app.py" in res.stdout.replace("\\", "/")

    res = runner.invoke(app, [str(sample_repo), "--ignore"])
    assert res.exit_code == 0
    assert "build/output.log" not in res.stdout

    res = runner.invoke(app, [str(sample_repo), "--no-hidden"])
    assert res.exit_code == 0
    assert ".config/settings.yaml" not in res.stdout

    res = runner.invoke(app, [str(sample_repo), "--no-follow-symlinks"])
    assert res.exit_code == 0

    res = runner.invoke(app, [str(sample_repo), "--no-symlinks"])
    assert res.exit_code == 0

    res = runner.invoke(app, [str(sample_repo), "--no-absolute", "-t", "python"])
    assert res.exit_code == 0
    assert "src/app.py" in res.stdout.replace("\\", "/")
    assert str(sample_repo / "src" / "app.py") not in res.stdout

    res = runner.invoke(app, [str(sample_repo), "--no-print0"])
    assert res.exit_code == 0
    assert "\0" not in res.stdout

    res = runner.invoke(app, [str(sample_repo), "--no-list-tags"])
    assert res.exit_code == 0
    assert "[" not in res.stdout

    res = runner.invoke(app, [str(sample_repo), "--no-summary"])
    assert res.exit_code == 0
    assert "--- findfmt summary ---" not in res.stderr

    res = runner.invoke(app, [str(sample_repo), "--no-exit-status"])
    assert res.exit_code == 0


def test_posix_double_dash_hyphenated_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    hyphen_dir = tmp_path / "-weird-dir"
    hyphen_dir.mkdir()
    (hyphen_dir / "script.py").write_text("#!/usr/bin/env python\nprint('posix')\n")

    runner = CliRunner()

    res_no_dash = runner.invoke(app, ["-weird-dir"])
    assert res_no_dash.exit_code != 0

    res_dash = runner.invoke(app, ["--", "-weird-dir"])
    assert res_dash.exit_code == 0
    assert "script.py" in res_dash.stdout

    assert main_findfiles(["--", "-weird-dir"]) == 0
    assert main_findfilemime(["--", "-weird-dir"]) == 0
    assert main_findfilefmt(["python", "--", "-weird-dir"]) == 0
    assert main_findfilefmt(["-t", "python", "--", "-weird-dir"]) == 0
    assert main_findfilefmt(["--", "python", "-weird-dir"]) == 0
    assert main_findshebang(["python", "--", "-weird-dir"]) == 0
    assert main_findshebang(["--shebang", "python", "--", "-weird-dir"]) == 0
    assert main_findshebang(["--", "python", "-weird-dir"]) == 0
    assert main_findfmt0(["--", "-weird-dir"]) == 0
    assert main_findsummary(["--", "-weird-dir"]) == 0


def test_cli_default_path():
    runner = CliRunner()
    with patch("findfmt.cli.runner.find_files", return_value=[]):
        result = runner.invoke(app, [])
        assert result.exit_code == 0


def test_cli_format_json(sample_repo: Path):
    runner = CliRunner()
    res = runner.invoke(app, ["--format", "json", str(sample_repo)])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert isinstance(data, list)
    assert len(data) > 0
    paths = [item["path"] for item in data]
    assert any("app.py" in p for p in paths)


def test_cli_format_jsonl(sample_repo: Path):
    runner = CliRunner()
    res = runner.invoke(app, ["-f", "jsonl", str(sample_repo)])
    assert res.exit_code == 0
    lines = [line for line in res.stdout.strip().split("\n") if line]
    assert len(lines) > 0
    record = json.loads(lines[0])
    assert "path" in record
    assert "tags" in record


def test_cli_format_yaml(sample_repo: Path):
    runner = CliRunner()
    res = runner.invoke(app, ["-f", "yaml", str(sample_repo)])
    assert res.exit_code == 0
    data = yaml.safe_load(res.stdout)
    assert isinstance(data, list)
    assert len(data) > 0
    assert "path" in data[0]


def test_cli_format_ipynb(sample_repo: Path):
    runner = CliRunner()
    res = runner.invoke(app, ["--format", "ipynb", str(sample_repo)])
    assert res.exit_code == 0
    nb = json.loads(res.stdout)
    assert nb["nbformat"] == 4
    assert len(nb["cells"]) >= 3


def test_cli_format_text(sample_repo: Path):
    runner = CliRunner()
    res = runner.invoke(app, ["--format", "text", str(sample_repo)])
    assert res.exit_code == 0
    assert "app.py" in res.stdout


def test_cli_format_invalid(sample_repo: Path):
    runner = CliRunner()
    res = runner.invoke(app, ["--format", "unsupported-fmt", str(sample_repo)])
    assert res.exit_code != 0


def test_cli_format_json_with_summary(sample_repo: Path):
    runner = CliRunner()
    res = runner.invoke(app, ["-f", "json", "--summary", str(sample_repo)])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert isinstance(data, list)
    assert "--- findfmt summary ---" in res.stderr
    assert "Matched files:" in res.stderr


def test_cli_metadata_flags(sample_repo: Path):
    runner = CliRunner()

    # Test permissions flag -p and --permissions
    res_p = runner.invoke(app, ["-p", str(sample_repo / "src")])
    assert res_p.exit_code == 0
    assert "[-r" in res_p.stdout

    res_perms = runner.invoke(app, ["--permissions", str(sample_repo / "src")])
    assert res_perms.exit_code == 0
    assert "[-r" in res_perms.stdout

    # Test user flag -u and --user
    res_u = runner.invoke(app, ["-u", str(sample_repo / "src")])
    assert res_u.exit_code == 0
    assert "[" in res_u.stdout

    res_user = runner.invoke(app, ["--user", str(sample_repo / "src")])
    assert res_user.exit_code == 0
    assert "[" in res_user.stdout

    # Test group flag -g and --group
    res_g = runner.invoke(app, ["-g", str(sample_repo / "src")])
    assert res_g.exit_code == 0
    assert "[" in res_g.stdout

    res_group = runner.invoke(app, ["--group", str(sample_repo / "src")])
    assert res_group.exit_code == 0
    assert "[" in res_group.stdout

    # Test inode and device flags
    res_inodes = runner.invoke(app, ["--inodes", str(sample_repo / "src")])
    assert res_inodes.exit_code == 0
    assert "[" in res_inodes.stdout

    res_device = runner.invoke(app, ["--device", str(sample_repo / "src")])
    assert res_device.exit_code == 0
    assert "[" in res_device.stdout

    # Test combined flags
    res_all_meta = runner.invoke(
        app,
        ["--inodes", "--device", "-p", "-u", "-g", "--list-tags", str(sample_repo / "src")],
    )
    assert res_all_meta.exit_code == 0
    assert "[" in res_all_meta.stdout


def test_cli_metadata_with_formatters(sample_repo: Path):
    runner = CliRunner(env={"COLUMNS": "200"})

    # Table format with metadata flags
    res_table = runner.invoke(
        app,
        ["-f", "table", "--inodes", "--device", "-p", "-u", "-g", str(sample_repo / "src")],
    )
    assert res_table.exit_code == 0
    assert "Inode" in res_table.stdout
    assert "Device" in res_table.stdout
    assert "Permissions" in res_table.stdout
    assert "User" in res_table.stdout
    assert "Group" in res_table.stdout

    # Tree format with metadata flags
    res_tree = runner.invoke(
        app,
        ["--tree", "--inodes", "--device", "-p", "-u", "-g", str(sample_repo / "src")],
    )
    assert res_tree.exit_code == 0
    assert "[" in res_tree.stdout

    # JSON format with metadata
    res_json = runner.invoke(app, ["-f", "json", str(sample_repo / "src")])
    assert res_json.exit_code == 0
    data = json.loads(res_json.stdout)
    assert len(data) > 0
    assert "permissions_str" in data[0]
    assert "owner_user" in data[0]
    assert "owner_group" in data[0]
    assert "inode" in data[0]
    assert "device" in data[0]


def test_cli_help_all_contains_metadata_flags():
    runner = CliRunner()
    res = runner.invoke(app, ["--help-all"])
    assert res.exit_code == 0
    assert "--permissions, -p" in res.stdout
    assert "--user, -u" in res.stdout
    assert "--group, -g" in res.stdout
    assert "--inodes" in res.stdout
    assert "--device" in res.stdout


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

    res = runner.invoke(app, [str(sample_repo), "-t", "nonexistent-tag-xyz"])
    assert res.exit_code == 0

    res = runner.invoke(app, [str(sample_repo), "--exit-status"])
    assert res.exit_code == 0
