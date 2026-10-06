import runpy
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

import pytest

from findfmt.cli import get_version, main, parse_tag_arguments


def test_get_version():
    ver = get_version()
    assert isinstance(ver, str)
    assert len(ver) > 0


def test_get_version_package_not_found():
    with patch("findfmt.cli.version", side_effect=PackageNotFoundError):
        assert get_version() == "0.1.0.dev0"


def test_parse_tag_arguments():
    assert parse_tag_arguments(None) == frozenset()
    assert parse_tag_arguments([]) == frozenset()
    tags = parse_tag_arguments(["Python, shell ", "json,"])
    assert tags == frozenset(["python", "shell", "json"])


def test_cli_known_tags(capsys):
    exit_code = main(["--known-tags"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "python\n" in captured.out
    assert "text\n" in captured.out


def test_cli_tag_filter(sample_repo: Path, capsys):
    exit_code = main([str(sample_repo), "-t", "python"])
    assert exit_code == 0
    captured = capsys.readouterr()
    lines = [line.strip() for line in captured.out.strip().split("\n") if line.strip()]
    assert any("app.py" in line for line in lines)
    assert any("nested.py" in line for line in lines)
    assert any("mytool" in line for line in lines)
    assert not any("runner.sh" in line for line in lines)


def test_cli_exclude_tags(sample_repo: Path, capsys):
    exit_code = main([str(sample_repo), "-t", "python", "-e", "executable"])
    assert exit_code == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    # 'mytool' is executable, so it should be excluded
    assert any("app.py" in line for line in lines)
    assert not any("mytool" in line for line in lines)


def test_cli_all_tags(sample_repo: Path, capsys):
    exit_code = main([str(sample_repo), "-t", "python,executable", "--all-tags"])
    assert exit_code == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    # Only 'mytool' is both python and executable
    assert any("mytool" in line for line in lines)
    assert not any("app.py" in line for line in lines)


def test_cli_shebang_filter(sample_repo: Path, capsys):
    exit_code = main([str(sample_repo), "--shebang", "bash"])
    assert exit_code == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    assert any("runner.sh" in line for line in lines)
    assert not any("mytool" in line for line in lines)


def test_cli_no_ignore(sample_repo: Path, capsys):
    exit_code = main([str(sample_repo), "--no-ignore"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "debug.log" in captured.out


def test_cli_hidden(sample_repo: Path, capsys):
    exit_code = main([str(sample_repo), "--hidden"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "settings.yaml" in captured.out


def test_cli_print0(sample_repo: Path, capsys):
    exit_code = main([str(sample_repo), "-t", "python", "-0"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "\0" in captured.out
    assert "\n" not in captured.out


def test_cli_list_tags(sample_repo: Path, capsys):
    exit_code = main([str(sample_repo), "-t", "python", "-l"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "[" in captured.out
    assert "python" in captured.out


def test_cli_summary(sample_repo: Path, capsys):
    exit_code = main([str(sample_repo), "-s"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "--- findfmt summary ---" in captured.err
    assert "Matched files:" in captured.err


def test_cli_absolute(sample_repo: Path, capsys):
    exit_code = main([str(sample_repo), "-t", "python", "--absolute"])
    assert exit_code == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    for line in lines:
        if line.strip():
            assert Path(line).is_absolute()


def test_cli_summary_no_matches(tmp_path: Path, capsys):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    exit_code = main([str(empty_dir), "-t", "nonexistent_tag", "-s"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Matched files: 0" in captured.err
    assert "Top tags:" not in captured.err


def test_main_module():
    with patch("sys.argv", ["findfmt", "--version"]):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("findfmt.__main__", run_name="__main__")
        assert exc_info.value.code == 0
