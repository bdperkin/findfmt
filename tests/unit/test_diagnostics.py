"""Unit tests for system diagnostics, version retrieval, and help reference."""

from __future__ import annotations

import subprocess
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from findfmt.cli import (
    app,
    diagnostics_callback,
    get_diagnostics,
    get_git_version,
    get_help_all,
    get_version,
    help_all_callback,
    version_callback,
)
from findfmt.diagnostics import _is_verbose_requested


def test_get_version():
    ver = get_version()
    assert isinstance(ver, str)
    assert len(ver) > 0


def test_get_version_package_not_found():
    with patch("findfmt.diagnostics.version", side_effect=PackageNotFoundError):
        assert get_version() == "0.3.0.dev0"


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

    with patch("findfmt.diagnostics.version", side_effect=PackageNotFoundError):
        diag_no_identify = get_diagnostics()
        assert "identify: not installed" in diag_no_identify

    with patch("findfmt.diagnostics.get_git_version", return_value=None):
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
        patch("findfmt.diagnostics._is_verbose_requested", return_value=True),
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
