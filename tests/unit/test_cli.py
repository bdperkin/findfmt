import runpy
import subprocess
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from findfmt.cli import (
    _consume_option,
    _extract_first_positional,
    _has_option,
    _is_verbose_requested,
    app,
    diagnostics_callback,
    get_diagnostics,
    get_git_version,
    get_help_all,
    get_version,
    help_all_callback,
    main,
    main_findfilefmt,
    main_findfilemime,
    main_findfiles,
    main_findfmt0,
    main_findshebang,
    main_findsummary,
    parse_tag_arguments,
    version_callback,
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


def test_get_git_version():
    with patch("shutil.which", return_value=None):
        assert get_git_version() is None

    with (
        patch("shutil.which", return_value="/usr/bin/git"),
        patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, "git version 2.50.0\n", ""),
        ),
    ):
        assert get_git_version() == "git version 2.50.0"

    with (
        patch("shutil.which", return_value="/usr/bin/git"),
        patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess([], 1, "", "error"),
        ),
    ):
        assert get_git_version() is None

    with (
        patch("shutil.which", return_value="/usr/bin/git"),
        patch("subprocess.run", side_effect=OSError("command failed")),
    ):
        assert get_git_version() is None


def test_get_diagnostics():
    diag = get_diagnostics()
    assert "findfmt " in diag
    assert "Python: " in diag
    assert "identify: " in diag
    assert "Git: " in diag

    with patch("findfmt.cli.version", side_effect=PackageNotFoundError):
        diag_no_identify = get_diagnostics()
        assert "identify: not installed" in diag_no_identify

    with patch("findfmt.cli.get_git_version", return_value=None):
        diag_no_git = get_diagnostics()
        assert "Git: not found" in diag_no_git


def test_is_verbose_requested():
    class DummyContext:
        def __init__(self, params=None, obj=None):
            self.params = params or {}
            self.obj = obj

    ctx_verbose = DummyContext(params={"verbose": True})
    assert _is_verbose_requested(ctx_verbose) is True

    ctx_diag = DummyContext(params={"diagnostics": True})
    assert _is_verbose_requested(ctx_diag) is True

    ctx_obj_verbose = DummyContext(obj={"argv": ["--verbose"]})
    assert _is_verbose_requested(ctx_obj_verbose) is True

    ctx_obj_diag = DummyContext(obj={"argv": ["--diagnostics"]})
    assert _is_verbose_requested(ctx_obj_diag) is True

    ctx_obj_other = DummyContext(obj={"argv": ["findfmt", "src/"]})
    with patch("sys.argv", ["findfmt"]):
        assert _is_verbose_requested(ctx_obj_other) is False

    with patch("sys.argv", ["findfmt"]):
        assert _is_verbose_requested(DummyContext()) is False

    with patch("sys.argv", ["findfmt", "--verbose"]):
        assert _is_verbose_requested(None) is True

    with patch("sys.argv", ["findfmt", "--diagnostics"]):
        assert _is_verbose_requested(None) is True

    with patch("sys.argv", ["findfmt"]):
        assert _is_verbose_requested(None) is False


def test_version_callback_direct():
    with pytest.raises(typer.Exit) as exc:
        version_callback(ctx=True)

    assert exc.value.exit_code == 0

    version_callback(value=False)

    with (
        patch("findfmt.cli._is_verbose_requested", return_value=True),
        pytest.raises(typer.Exit) as exc,
    ):
        version_callback(value=True)

    assert exc.value.exit_code == 0


def test_diagnostics_callback():
    diagnostics_callback(value=False)
    with pytest.raises(typer.Exit) as exc:
        diagnostics_callback(value=True)

    assert exc.value.exit_code == 0


def test_help_all_callback_and_text():
    help_text = get_help_all()
    assert "findfmt " in help_text
    assert "Comprehensive CLI Reference" in help_text
    assert "Tag Filtering:" in help_text
    assert "Traversal Controls:" in help_text
    assert "Output Formatting:" in help_text
    assert "Command Wrappers:" in help_text
    assert "POSIX Double-Dash (--)" in help_text
    assert "Environment Variables:" in help_text
    assert "Exit Codes:" in help_text
    assert "Workflow Examples:" in help_text

    help_all_callback(value=False)
    with pytest.raises(typer.Exit) as exc:
        help_all_callback(value=True)

    assert exc.value.exit_code == 0


def test_cli_version_options():
    runner = CliRunner()
    res_cap_v = runner.invoke(app, ["-V"])
    assert res_cap_v.exit_code == 0
    assert "findfmt " in res_cap_v.stdout

    res_verb = runner.invoke(app, ["--version", "--verbose"])
    assert res_verb.exit_code == 0
    assert "Python: " in res_verb.stdout

    res_cap_verb = runner.invoke(app, ["-V", "--verbose"])
    assert res_cap_verb.exit_code == 0
    assert "Python: " in res_cap_verb.stdout

    res_diag = runner.invoke(app, ["--diagnostics"])
    assert res_diag.exit_code == 0
    assert "Python: " in res_diag.stdout


def test_cli_help_all():
    runner = CliRunner()
    res = runner.invoke(app, ["--help-all"])
    assert res.exit_code == 0
    assert "findfmt " in res.stdout
    assert "Comprehensive CLI Reference" in res.stdout
    assert "Command Wrappers:" in res.stdout
    assert "POSIX Double-Dash" in res.stdout


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
