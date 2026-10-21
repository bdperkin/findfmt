"""Unit tests for configuration loading, formatting, and CLI integration."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from findfmt.cli import (
    app,
    format_config_dump,
    get_active_config_data,
    get_active_config_path,
    resolve_and_load_config,
)
from findfmt.cli.file_config import (
    _format_toml_value,
    reset_active_config,
)
from findfmt.diagnostics import get_diagnostics, show_config_callback
from findfmt.formatters import OutputFormat


@pytest.fixture(autouse=True)
def _cleanup_config_state():
    """Ensure active configuration state is clean before and after each test."""
    reset_active_config()
    yield
    reset_active_config()


# -----------------------------------------------------------------------------
# 1. resolve_and_load_config & state retrieval tests
# -----------------------------------------------------------------------------


def test_resolve_and_load_config_none():
    path, defaults = resolve_and_load_config(no_config=True)
    assert path is None
    assert defaults == {}
    assert get_active_config_path() is None
    assert get_active_config_data() == {}


def test_resolve_and_load_config_pyproject_without_section(tmp_path: Path):
    pyproj = tmp_path / "pyproject.toml"
    pyproj.write_text("[project]\nname = 'test'\n")
    path, defaults = resolve_and_load_config(cwd=tmp_path)
    assert path is None
    assert defaults == {}


def test_resolve_and_load_config_empty_standalone(tmp_path: Path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("# empty file\n")
    path, defaults = resolve_and_load_config(explicit_path=cfg)
    assert path == cfg
    assert defaults == {}
    assert get_active_config_path() == cfg
    assert get_active_config_data() == {}


def test_resolve_and_load_config_active_state(tmp_path: Path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("format = 'tree'\nhidden = true\n")
    path, defaults = resolve_and_load_config(explicit_path=cfg)
    assert path == cfg
    assert defaults["output_format"] == OutputFormat.TREE
    assert defaults["hidden"] is True
    assert get_active_config_path() == cfg
    assert get_active_config_data() == {"format": "tree", "hidden": True}


# -----------------------------------------------------------------------------
# 2. format_config_dump tests
# -----------------------------------------------------------------------------


def test_format_config_dump_none():
    out = format_config_dump(None, {})
    assert "Active configuration:" in out
    assert "using built-in defaults" in out


def test_format_config_dump_with_path_no_data(tmp_path: Path):
    out = format_config_dump(tmp_path / "c.toml", {})
    assert "Active configuration:" in out
    assert "using built-in defaults" in out


def test_format_config_dump_with_settings(tmp_path: Path):
    data = {
        "color": "always",
        "format": "table",
        "hidden": True,
        "max_depth": 3,
        "tags": ["python", "shell"],
    }
    out = format_config_dump(tmp_path / "config.toml", data)
    assert f"Active configuration: {tmp_path / 'config.toml'}" in out
    assert "[tool.findfmt]" in out
    assert 'color = "always"' in out
    assert 'format = "table"' in out
    assert "hidden = true" in out
    assert "max_depth = 3" in out
    assert 'tags = ["python", "shell"]' in out


def test_format_toml_value():
    val_true: bool = True
    val_false: bool = False
    assert _format_toml_value(val_true) == "true"
    assert _format_toml_value(val_false) == "false"
    assert _format_toml_value(42) == "42"
    assert _format_toml_value(3.14) == "3.14"
    assert _format_toml_value("hello") == '"hello"'
    assert _format_toml_value(["a", "b"]) == '["a", "b"]'
    assert _format_toml_value([1, 2]) == "[1, 2]"


# -----------------------------------------------------------------------------
# 3. End-to-End CLI Integration tests via CliRunner
# -----------------------------------------------------------------------------


def test_cli_show_config_no_file():
    runner = CliRunner()
    res = runner.invoke(app, ["--no-config", "--show-config"])
    assert res.exit_code == 0
    assert "Active configuration: (none)" in res.stdout


def test_cli_show_config_with_file(tmp_path: Path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("format = 'json'\nhidden = true\n")

    runner = CliRunner()
    res = runner.invoke(app, ["--config", str(cfg), "--show-config"])
    assert res.exit_code == 0
    assert f"Active configuration: {cfg}" in res.stdout
    assert 'format = "json"' in res.stdout
    assert "hidden = true" in res.stdout


def test_cli_config_precedence_and_override(tmp_path: Path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("format = 'table'\ntable_style = 'grid'\n")

    test_file = tmp_path / "main.py"
    test_file.write_text("print('hello')\n")

    runner = CliRunner()
    res_default = runner.invoke(app, ["--config", str(cfg), str(tmp_path)])
    assert res_default.exit_code == 0

    res_override = runner.invoke(app, ["--config", str(cfg), "-f", "json", str(tmp_path)])
    assert res_override.exit_code == 0
    assert '"path":' in res_override.stdout


def test_cli_no_config_suppression(tmp_path: Path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("format = 'json'\n")

    test_file = tmp_path / "main.py"
    test_file.write_text("print('hello')\n")

    runner = CliRunner()
    with patch.dict(os.environ, {"FINDFMT_CONFIG": str(cfg)}):
        res_with = runner.invoke(app, [str(tmp_path)])
        assert res_with.exit_code == 0
        assert '"path":' in res_with.stdout

        res_suppressed = runner.invoke(app, ["--no-config", str(tmp_path)])
        assert res_suppressed.exit_code == 0
        assert '"path":' not in res_suppressed.stdout


def test_cli_diagnostics_shows_active_config(tmp_path: Path):
    cfg = tmp_path / "diag_config.toml"
    cfg.write_text("format = 'json'\n")

    runner = CliRunner()
    res = runner.invoke(app, ["--config", str(cfg), "--diagnostics"])
    assert res.exit_code == 0
    assert f"Configuration: {cfg}" in res.stdout


def test_cli_diagnostics_shows_none_when_no_config():
    runner = CliRunner()
    res = runner.invoke(app, ["--no-config", "--diagnostics"])
    assert res.exit_code == 0
    assert "Configuration: none" in res.stdout


def test_cli_missing_explicit_config_error(tmp_path: Path):
    nonexistent = tmp_path / "custom.toml"
    runner = CliRunner()
    res = runner.invoke(app, ["--config", str(nonexistent)])
    assert res.exit_code == 2
    assert f"Error: Configuration file '{nonexistent}' not found." in res.stderr


def test_cli_invalid_toml_error(tmp_path: Path):
    bad = tmp_path / "bad.toml"
    bad.write_text("invalid = = =")

    runner = CliRunner()
    res = runner.invoke(app, ["--config", str(bad)])
    assert res.exit_code == 2
    assert "Error: Invalid TOML in configuration file" in res.stderr


def test_cli_unknown_key_error(tmp_path: Path):
    bad = tmp_path / "unknown.toml"
    bad.write_text("unknown_setting = 123\n")

    runner = CliRunner()
    res = runner.invoke(app, ["--config", str(bad)])
    assert res.exit_code == 2
    assert "Error: Unknown configuration key 'unknown_setting'" in res.stderr


def test_show_config_callback_direct():
    show_config_callback(value=False)

    with pytest.raises(typer.Exit) as exc:
        show_config_callback(ctx=True)

    assert exc.value.exit_code == 0

    cmd = typer.main.get_command(app)
    ctx = typer.Context(cmd)
    ctx.meta["findfmt_config_path"] = Path("/test.toml")
    ctx.meta["findfmt_config_data"] = {"format": "table"}

    with pytest.raises(typer.Exit) as exc2:
        show_config_callback(ctx=ctx, value=True)

    assert exc2.value.exit_code == 0


def test_cli_help_displays_despite_missing_config():
    runner = CliRunner()
    res = runner.invoke(app, ["--config", "/nonexistent/config.toml", "--help"])
    assert res.exit_code == 0
    assert "Usage:" in res.stdout


def test_cli_help_all_displays_despite_invalid_config(tmp_path: Path):
    bad = tmp_path / "bad.toml"
    bad.write_text("invalid syntax = = =")
    runner = CliRunner()
    res = runner.invoke(app, ["--config", str(bad), "--help-all"])
    assert res.exit_code == 0
    assert "Comprehensive CLI Reference" in res.stdout


def test_get_diagnostics_with_context_meta_config():
    p = Path("/custom/meta_config.toml")
    cmd = typer.main.get_command(app)
    ctx = typer.Context(cmd)
    ctx.meta["findfmt_config_path"] = p

    diag = get_diagnostics(ctx=ctx)
    assert f"Configuration: {p}" in diag


def test_cli_config_file_csv_safe(tmp_path: Path):
    cfg = tmp_path / "findfmt.toml"
    cfg.write_text("csv_safe = true\nformat = 'csv'\n", encoding="utf-8")
    (tmp_path / "=evil.csv").write_text("payload", encoding="utf-8")

    runner = CliRunner()
    res = runner.invoke(app, ["--config", str(cfg), str(tmp_path)])
    assert res.exit_code == 0
    assert "'=evil.csv" in res.stdout


def test_cli_config_file_exit_status(tmp_path: Path):
    cfg = tmp_path / "findfmt.toml"
    cfg.write_text("exit_status = true\n", encoding="utf-8")
    runner = CliRunner()
    res = runner.invoke(app, ["--config", str(cfg), str(tmp_path), "-t", "nonexistent-tag"])
    assert res.exit_code == 1
