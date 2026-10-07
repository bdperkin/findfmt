import runpy
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from findfmt.cli import (
    _consume_option,
    _extract_first_positional,
    _has_option,
    app,
    get_version,
    main,
    main_findfilefmt,
    main_findfilemime,
    main_findfiles,
    main_findfmt0,
    main_findshebang,
    main_findsummary,
    parse_tag_arguments,
)


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


def test_has_option():
    assert _has_option(["-t", "python"], {"-t", "--type", "--tag"})
    assert _has_option(["--tag=python"], {"-t", "--type", "--tag"})
    assert not _has_option(["--shebang", "bash"], {"-t", "--type", "--tag"})


def test_consume_option():
    assert _consume_option("-t", "python") == 2
    assert _consume_option("-t", None) == 1
    assert _consume_option("--hidden", "python") == 1
    assert _consume_option("-t=python", "src/") == 1


def test_extract_first_positional():
    assert _extract_first_positional([]) == (None, [])
    assert _extract_first_positional(["python"]) == ("python", [])
    assert _extract_first_positional(["python", "src/"]) == ("python", ["src/"])
    assert _extract_first_positional(["--hidden", "python", "src/"]) == (
        "python",
        ["--hidden", "src/"],
    )
    assert _extract_first_positional(["--exclude", "test", "python", "src/"]) == (
        "python",
        ["--exclude", "test", "src/"],
    )
    assert _extract_first_positional(["--", "python", "src/"]) == (
        "python",
        ["--", "src/"],
    )
    assert _extract_first_positional(["--", "--weird", "src/"]) == (
        "--weird",
        ["--", "src/"],
    )


def test_main_findfiles(sample_repo: Path, capsys: pytest.CaptureFixture[str]):
    exit_code = main_findfiles([str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert ".config/settings.yaml" in captured.out

    help_code = main_findfiles(["--help"])
    assert help_code == 0

    with patch("sys.argv", ["findfiles", str(sample_repo)]):
        assert main_findfiles() == 0


def test_main_findfilemime(sample_repo: Path, capsys: pytest.CaptureFixture[str]):
    exit_code = main_findfilemime([str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert ".config/settings.yaml" in captured.out
    assert "yaml" in captured.out

    help_code = main_findfilemime(["--help"])
    assert help_code == 0


def test_main_findfilefmt(sample_repo: Path, capsys: pytest.CaptureFixture[str]):
    # Positional tag
    exit_code = main_findfilefmt(["python", str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "src/app.py" in captured.out
    assert ".config/settings.yaml" not in captured.out

    # Explicit flag
    exit_code = main_findfilefmt(["-t", "yaml", str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert ".config/settings.yaml" in captured.out

    # No arguments (lists all in current directory)
    with patch("sys.argv", ["findfilefmt"]):
        assert main_findfilefmt([]) == 0

    # sys.argv fallback
    with patch("sys.argv", ["findfilefmt", "python", str(sample_repo)]):
        assert main_findfilefmt() == 0

    help_code = main_findfilefmt(["--help"])
    assert help_code == 0


def test_main_findshebang(sample_repo: Path, capsys: pytest.CaptureFixture[str]):
    # Positional interpreter
    exit_code = main_findshebang(["bash", str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "scripts/runner.sh" in captured.out
    assert "scripts/mytool" not in captured.out

    # Explicit flag
    exit_code = main_findshebang(["--shebang", "python", str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "scripts/mytool" in captured.out

    # No positional interpreter
    exit_code = main_findshebang([str(sample_repo)])
    assert exit_code == 0

    # sys.argv fallback
    with patch("sys.argv", ["findshebang", "bash", str(sample_repo)]):
        assert main_findshebang() == 0

    help_code = main_findshebang(["--help"])
    assert help_code == 0


def test_main_findfmt0(sample_repo: Path, capsys: pytest.CaptureFixture[str]):
    exit_code = main_findfmt0([str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "\0" in captured.out
    assert ".config/settings.yaml\0" in captured.out

    help_code = main_findfmt0(["--help"])
    assert help_code == 0


def test_main_findsummary(sample_repo: Path, capsys: pytest.CaptureFixture[str]):
    exit_code = main_findsummary([str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "--- findfmt summary ---" in captured.err
    assert "Matched files:" in captured.err

    help_code = main_findsummary(["--help"])
    assert help_code == 0


def test_wrappers_error_exit_code():
    assert main_findfiles(["--nonexistent-flag"]) != 0
    assert main_findfilemime(["--nonexistent-flag"]) != 0
    assert main_findfilefmt(["--nonexistent-flag"]) != 0
    assert main_findshebang(["--nonexistent-flag"]) != 0
    assert main_findfmt0(["--nonexistent-flag"]) != 0
    assert main_findsummary(["--nonexistent-flag"]) != 0
