"""Unit tests for findfmt CLI command flags, options, filtering, and serializers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from findfmt.cli import (
    app,
    main_findfilefmt,
    main_findfilemime,
    main_findfiles,
    main_findfmt0,
    main_findshebang,
    main_findsummary,
    parse_tag_arguments,
)


def test_parse_tag_arguments():
    assert parse_tag_arguments(None) == frozenset()
    assert parse_tag_arguments([]) == frozenset()
    tags = parse_tag_arguments(["Python, shell ", "json,"])
    assert tags == frozenset(["python", "shell", "json"])


def test_cli_tag_filter(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-t", "python"])
    assert result.exit_code == 0
    lines = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    assert any("app.py" in line for line in lines)
    assert any("nested.py" in line for line in lines)
    assert any("mytool" in line for line in lines)
    assert not any("runner.sh" in line for line in lines)


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


def test_cli_follow_symlinks(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-L"])
    assert result.exit_code == 0

    result_long = runner.invoke(app, [str(sample_repo), "--follow-symlinks"])
    assert result_long.exit_code == 0


def test_cli_print0(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-t", "python", "-0"])
    assert result.exit_code == 0
    assert "\0" in result.stdout
    assert "\n" not in result.stdout


def test_cli_list_tags(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-t", "python", "-l"])
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

    res = runner.invoke(
        app,
        [str(sample_repo), "-t", "python,executable", "--all-tags", "--no-all-tags"],
    )
    assert res.exit_code == 0
    lines = res.stdout.strip().split("\n")
    assert any("app.py" in line for line in lines)

    res = runner.invoke(app, [str(sample_repo), "--hidden", "--no-hidden"])
    assert res.exit_code == 0
    assert ".config/settings.yaml" not in res.stdout

    res = runner.invoke(app, [str(sample_repo), "--no-ignore", "--ignore"])
    assert res.exit_code == 0
    assert "debug.log" not in res.stdout

    res = runner.invoke(app, [str(sample_repo), "--follow-symlinks", "--no-follow-symlinks"])
    assert res.exit_code == 0

    res = runner.invoke(app, [str(sample_repo), "--symlinks", "--no-symlinks"])
    assert res.exit_code == 0

    res = runner.invoke(app, [str(sample_repo), "-L", "--no-follow-symlinks"])
    assert res.exit_code == 0

    res = runner.invoke(app, [str(sample_repo), "--absolute", "--no-absolute"])
    assert res.exit_code == 0
    assert not any(line.startswith("/") for line in res.stdout.splitlines())

    res = runner.invoke(app, [str(sample_repo), "--print0", "--no-print0"])
    assert res.exit_code == 0
    assert "\0" not in res.stdout

    res = runner.invoke(app, [str(sample_repo), "-0", "--no-print0"])
    assert res.exit_code == 0
    assert "\0" not in res.stdout

    res = runner.invoke(app, [str(sample_repo), "--list-tags", "--no-list-tags"])
    assert res.exit_code == 0
    assert "[" not in res.stdout

    res = runner.invoke(app, [str(sample_repo), "-l", "--no-list-tags"])
    assert res.exit_code == 0
    assert "[" not in res.stdout

    res = runner.invoke(app, [str(sample_repo), "--summary", "--no-summary"])
    assert res.exit_code == 0
    assert "--- findfmt summary ---" not in res.stderr

    res = runner.invoke(app, [str(sample_repo), "-s", "--no-summary"])
    assert res.exit_code == 0
    assert "--- findfmt summary ---" not in res.stderr


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
