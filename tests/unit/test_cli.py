import runpy
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from findfmt.cli import app, get_version, main, parse_tag_arguments


def test_get_version():
    ver = get_version()
    assert isinstance(ver, str)
    assert len(ver) > 0


def test_get_version_package_not_found():
    with patch("findfmt.cli.version", side_effect=PackageNotFoundError):
        assert get_version() == "0.1.1.dev0"


def test_parse_tag_arguments():
    assert parse_tag_arguments(None) == frozenset()
    assert parse_tag_arguments([]) == frozenset()
    tags = parse_tag_arguments(["Python, shell ", "json,"])
    assert tags == frozenset(["python", "shell", "json"])


def test_cli_known_tags():
    runner = CliRunner()
    result = runner.invoke(app, ["--known-tags"])
    assert result.exit_code == 0
    assert "python\n" in result.stdout
    assert "text\n" in result.stdout


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "findfmt " in result.stdout

    result_short = runner.invoke(app, ["-v"])
    assert result_short.exit_code == 0
    assert "findfmt " in result_short.stdout


def test_cli_help():
    runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert "findfmt" in result.stdout

    result_short = runner.invoke(app, ["-h"])
    assert result_short.exit_code == 0
    assert "Usage:" in result_short.stdout
    assert "findfmt" in result_short.stdout


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
    # 'mytool' is executable, so it should be excluded
    assert any("app.py" in line for line in lines)
    assert not any("mytool" in line for line in lines)


def test_cli_all_tags(sample_repo: Path):
    runner = CliRunner()
    result = runner.invoke(app, [str(sample_repo), "-t", "python,executable", "--all-tags"])
    assert result.exit_code == 0
    lines = result.stdout.strip().split("\n")
    # Only 'mytool' is both python and executable
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


def test_cli_main_wrapper(sample_repo: Path):
    assert main([str(sample_repo), "-t", "python"]) == 0
    assert main(["--nonexistent-flag-xyz"]) != 0


def test_main_module():
    with patch("sys.argv", ["findfmt", "--version"]):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("findfmt.__main__", run_name="__main__")

        assert exc_info.value.code == 0
