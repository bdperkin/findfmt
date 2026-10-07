"""Unit tests for command wrappers, option consumption, and specialized entry points."""

from __future__ import annotations

import runpy
from pathlib import Path
from unittest.mock import patch

import pytest

from findfmt.entrypoints import (
    _consume_option,
    _extract_first_positional,
    _has_option,
    main,
    main_findfilefmt,
    main_findfilemime,
    main_findfiles,
    main_findfmt0,
    main_findshebang,
    main_findsummary,
)


def test_has_option():
    assert _has_option(["-t", "python"], {"-t", "--type", "--tag"})
    assert _has_option(["--tag=python"], {"-t", "--type", "--tag"})
    assert not _has_option(["--shebang", "bash"], {"-t", "--type", "--tag"})


def test_consume_option():
    assert _consume_option("-t", "python") == 2
    assert _consume_option("-t", None) == 1
    assert _consume_option("--hidden", "python") == 1
    assert _consume_option("-t=python", "src/") == 1
    assert _consume_option("-f", "json") == 2
    assert _consume_option("--format", "yaml") == 2
    assert _consume_option("--format=json", None) == 1


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


def test_cli_main_wrapper(sample_repo: Path):
    assert main([str(sample_repo), "-t", "python"]) == 0
    assert main(["--nonexistent-flag-xyz"]) != 0


def test_main_module():
    with patch("sys.argv", ["findfmt", "--version"]):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("findfmt.__main__", run_name="__main__")

        assert exc_info.value.code == 0


def test_main_findfiles(sample_repo: Path, capsys: pytest.CaptureFixture[str]):
    exit_code = main_findfiles([str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    normalized = captured.out.replace("\\", "/")
    assert ".config/settings.yaml" in normalized

    help_code = main_findfiles(["--help"])
    assert help_code == 0

    with patch("sys.argv", ["findfiles", str(sample_repo)]):
        assert main_findfiles() == 0


def test_main_findfilemime(sample_repo: Path, capsys: pytest.CaptureFixture[str]):
    exit_code = main_findfilemime([str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    normalized = captured.out.replace("\\", "/")
    assert ".config/settings.yaml" in normalized
    assert "yaml" in normalized

    help_code = main_findfilemime(["--help"])
    assert help_code == 0


def test_main_findfilefmt(sample_repo: Path, capsys: pytest.CaptureFixture[str]):
    # Positional tag
    exit_code = main_findfilefmt(["python", str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    normalized = captured.out.replace("\\", "/")
    assert "src/app.py" in normalized
    assert ".config/settings.yaml" not in normalized

    # Explicit flag
    exit_code = main_findfilefmt(["-t", "yaml", str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    normalized = captured.out.replace("\\", "/")
    assert ".config/settings.yaml" in normalized

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
    normalized = captured.out.replace("\\", "/")
    assert "scripts/runner.sh" in normalized
    assert "scripts/mytool" not in normalized

    # Explicit flag
    exit_code = main_findshebang(["--shebang", "python", str(sample_repo)])
    assert exit_code == 0
    captured = capsys.readouterr()
    normalized = captured.out.replace("\\", "/")
    assert "scripts/mytool" in normalized

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
    normalized = captured.out.replace("\\", "/")
    assert ".config/settings.yaml\0" in normalized

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


def test_wrapper_default_overrides(sample_repo: Path, capsys: pytest.CaptureFixture[str]):
    assert main_findfiles(["--no-hidden", str(sample_repo)]) == 0
    captured = capsys.readouterr()
    assert ".config/settings.yaml" not in captured.out

    assert main_findsummary(["--no-summary", str(sample_repo)]) == 0
    captured = capsys.readouterr()
    assert "--- findfmt summary ---" not in captured.err

    assert main_findfmt0(["--no-print0", str(sample_repo)]) == 0
    captured = capsys.readouterr()
    assert "\0" not in captured.out

    assert main_findfilemime(["--no-list-tags", str(sample_repo)]) == 0
    captured = capsys.readouterr()
    assert "[" not in captured.out
