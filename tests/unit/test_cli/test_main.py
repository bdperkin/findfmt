"""Unit tests for findfmt Typer CLI application and flags."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import yaml
from typer.main import get_command
from typer.testing import CliRunner

from findfmt.cli import (
    app,
    main_findfilefmt,
    main_findfilemime,
    main_findfiles,
    main_findfmt0,
    main_findshebang,
    main_findsummary,
)
from findfmt.cli.help import HELP_VERBOSE, get_help_all
from findfmt.cli.pager import resolve_pager_flag
from findfmt.cli.summary import parse_tag_arguments
from findfmt.exceptions import FindFmtError
from findfmt.formatters.html_formatter import HtmlFormatter

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


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
    assert runner.invoke(app, [str(sample_repo), "--no-follow-symlinks"]).exit_code == 0
    assert runner.invoke(app, [str(sample_repo), "--no-symlinks"]).exit_code == 0
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
    assert runner.invoke(app, [str(sample_repo), "--no-exit-status"]).exit_code == 0


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
    for flag in ("-p", "--permissions"):
        res = runner.invoke(app, [flag, str(sample_repo / "src")])
        assert res.exit_code == 0
        assert "[-r" in res.stdout

    for flag in ("-u", "--user", "-g", "--group", "--inodes", "--device"):
        res = runner.invoke(app, [flag, str(sample_repo / "src")])
        assert res.exit_code == 0
        assert "[" in res.stdout

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


def test_invalid_table_style_is_usage_error(tmp_path: Path) -> None:
    """Verify invalid --table-style for table/csv-table exits with code 2 and no traceback."""
    runner = CliRunner()
    result = runner.invoke(app, ["-f", "table", "--table-style", "bogus", str(tmp_path)])
    assert result.exit_code == 2
    assert "rounded" in result.stderr
    assert "simple" in result.stderr
    assert "Traceback" not in result.output

    res_csv_table = runner.invoke(app, ["-f", "csv-table", "--table-style", "bogus", str(tmp_path)])
    assert res_csv_table.exit_code == 2
    assert "rounded" in res_csv_table.stderr
    assert "Traceback" not in res_csv_table.output


def test_incompatible_table_style_for_rst(tmp_path: Path) -> None:
    """Verify incompatible --table-style for rst exits with code 2 and no traceback."""
    runner = CliRunner()
    result = runner.invoke(app, ["-f", "rst", "--table-style", "rounded", str(tmp_path)])
    assert result.exit_code == 2
    assert "grid" in result.stderr
    assert "simple" in result.stderr
    assert "Traceback" not in result.output


def test_non_utf8_intro_file_is_clean_error(tmp_path: Path) -> None:
    """Verify non-UTF-8 --intro/--outro files produce a clean error and exit 2 without traceback."""
    latin1_file = tmp_path / "intro_latin1.html"
    latin1_file.write_bytes("Café résumé\n".encode("latin-1"))

    runner = CliRunner()
    result = runner.invoke(app, ["-f", "html", "--intro", str(latin1_file), str(tmp_path)])
    assert result.exit_code == 2
    assert "UTF-8" in result.stderr
    assert "Traceback" not in result.output

    with pytest.raises(FindFmtError, match="UTF-8"):
        HtmlFormatter(intro_file=latin1_file)


def test_domain_exception_base_caught_in_runner(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    """Verify any FindFmtError subclass raised during formatter creation exits 2 cleanly."""

    class _CustomDomainError(FindFmtError):
        pass

    mocker.patch(
        "findfmt.cli.runner.get_formatter",
        side_effect=_CustomDomainError("custom domain failure"),
    )
    runner = CliRunner()
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 2
    err_lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert err_lines == ["Error: custom domain failure"]
    assert "Traceback" not in result.output


def test_typer_app_pretty_exceptions_disabled() -> None:
    """Verify Typer pretty exceptions and local variable dumps are disabled."""
    assert app.pretty_exceptions_enable is False
    assert app.pretty_exceptions_show_locals is False


def test_negative_numeric_options_rejected(tmp_path: Path) -> None:
    """Verify negative values for -L/--max-depth and --filelimit exit with code 2."""
    runner = CliRunner()
    for args in (
        ["-L", "-1", str(tmp_path)],
        ["--max-depth", "-1", str(tmp_path)],
        ["--filelimit", "-5", str(tmp_path)],
    ):
        result = runner.invoke(app, args)
        assert result.exit_code == 2
        assert "Traceback" not in result.output

    assert "extended runtime diagnostics" in str(HELP_VERBOSE)
    assert "verbose output" not in str(HELP_VERBOSE).lower()
    assert str(HELP_VERBOSE) in get_help_all()
    assert resolve_pager_flag.__doc__ is not None
    assert "-P" not in resolve_pager_flag.__doc__


def test_help_all_generated_from_click() -> None:
    """Verify --help-all dynamically includes every Click option, flag, and Choice value."""
    manual = get_help_all()
    command = get_command(app)
    ctx = command.context_class(command)

    options = [
        param for param in command.get_params(ctx) if any(opt.startswith("-") for opt in param.opts)
    ]
    assert options

    for param in options:
        for flag in (*param.opts, *param.secondary_opts):
            assert flag in manual, f"Option {param.name!r} flag {flag!r} missing from --help-all"

        type_source = getattr(param, "type", None) or getattr(param, "type_descriptor", None)
        choices = getattr(type_source, "choices", None)
        if choices is not None:
            expected_choices = ", ".join(str(getattr(c, "value", c)) for c in choices)
            assert f"(choices: {expected_choices})" in manual

    assert "time (mtime)" in manual
    assert "--csv-safe / --no-csv-safe" in manual
