"""Unit tests for the FINDFMT_* environment-variable configuration layer (#456)."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from findfmt.cli import app, load_env_config, resolve_and_load_config
from findfmt.cli.env_config import merge_raw_config
from findfmt.cli.file_config import get_active_config_data, reset_active_config
from findfmt.formatters import OutputFormat


@pytest.fixture(autouse=True)
def _cleanup_config_state():
    """Ensure active configuration state is clean before and after each test."""
    reset_active_config()
    yield
    reset_active_config()


def test_load_env_config_empty() -> None:
    """Return empty dictionaries when no FINDFMT_* variables are present."""
    raw, converted = load_env_config({"PATH": "/usr/bin", "HOME": "/tmp"})
    assert raw == {}
    assert converted == {}


def test_load_env_config_ignores_reserved_and_blank_values() -> None:
    """Ignore FINDFMT_CONFIG, FINDFMT_CONTAINER_TESTS, and empty recognized values."""
    env = {
        "FINDFMT_CONFIG": "/tmp/config.toml",
        "FINDFMT_CONTAINER_TESTS": "1",
        "FINDFMT_MAX_DEPTH": "",
        "FINDFMT_TAGS": "   ",
    }
    raw, converted = load_env_config(env)
    assert raw == {}
    assert converted == {}


def test_load_env_config_all_types() -> None:
    """Coerce and validate booleans, ints, comma/TOML lists, formats, tri-states, and paths."""
    env = {
        "FINDFMT_FORMAT": "table",
        "FINDFMT_COLOR": "always",
        "FINDFMT_PAGER": "never",
        "FINDFMT_HIDDEN": "true",
        "FINDFMT_IGNORE": "0",
        "FINDFMT_MAX_DEPTH": "3",
        "FINDFMT_FILE_LIMIT": "0",
        "FINDFMT_TAGS": "python, shell",
        "FINDFMT_EXCLUDE_TAGS": '["markdown", "json"]',
        "FINDFMT_SORT": "size",
        "FINDFMT_GITIGNORE_FILE": "/tmp/custom.gitignore",
    }
    raw, converted = load_env_config(env)
    assert raw["format"] == "table"
    assert raw["hidden"] is True
    assert raw["ignore"] is False
    assert raw["max_depth"] == 3
    assert raw["file_limit"] == 0
    assert raw["tags"] == ["python", "shell"]
    assert raw["exclude_tags"] == ["markdown", "json"]

    assert converted["output_format"] == OutputFormat.TABLE
    assert converted["color"] is True
    assert converted["pager"] is False
    assert converted["hidden"] is True
    assert converted["no_ignore"] is True
    assert converted["max_depth"] == 3
    assert converted["file_limit"] == 0
    assert converted["tags"] == ["python", "shell"]
    assert converted["exclude_tags"] == ["markdown", "json"]
    assert converted["sort"] == "size"
    assert converted["gitignore_file"] == Path("/tmp/custom.gitignore")


@pytest.mark.parametrize(
    ("bad_env", "expected_fragment"),
    [
        ({"FINDFMT_UNKNOWN_KEY": "1"}, "Unknown configuration key 'FINDFMT_UNKNOWN_KEY'"),
        ({"FINDFMT_HIDDEN": "maybe"}, "Invalid value for 'FINDFMT_HIDDEN' in 'environment'"),
        ({"FINDFMT_MAX_DEPTH": "abc"}, "Invalid value for 'FINDFMT_MAX_DEPTH' in 'environment'"),
        ({"FINDFMT_MAX_DEPTH": "-2"}, "Invalid value for 'FINDFMT_MAX_DEPTH' in 'environment'"),
        ({"FINDFMT_TAGS": "[unclosed"}, "Invalid value for 'FINDFMT_TAGS' in 'environment'"),
        ({"FINDFMT_TAGS": "[1, 2]"}, "Invalid value for 'FINDFMT_TAGS' in 'environment'"),
        ({"FINDFMT_FORMAT": "bogus"}, "Invalid value for 'FINDFMT_FORMAT' in 'environment'"),
        ({"FINDFMT_COLOR": "bogus"}, "Invalid value for 'FINDFMT_COLOR' in 'environment'"),
    ],
)
def test_load_env_config_validation_errors(
    bad_env: dict[str, str],
    expected_fragment: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit with code 2 and a clear error message when FINDFMT_* values are invalid."""
    with pytest.raises(typer.Exit) as exc:
        load_env_config(bad_env)

    assert exc.value.exit_code == 2
    assert expected_fragment in capsys.readouterr().err


def test_merge_raw_config_replaces_aliases() -> None:
    """Verify merge_raw_config replaces alias keys targeting the same canonical parameter."""
    base = {
        "format": "table",
        "ignore": True,
        "tags": ["rust"],
        "max_depth": 5,
    }
    assert merge_raw_config(base, {}) == base

    override = {
        "output_format": "json",
        "no_ignore": True,
        "tag": ["python"],
        "max_depth": 2,
    }
    merged = merge_raw_config(base, override)
    assert "format" not in merged
    assert "ignore" not in merged
    assert "tags" not in merged
    assert merged == {
        "output_format": "json",
        "no_ignore": True,
        "tag": ["python"],
        "max_depth": 2,
    }


def test_resolve_and_load_config_merges_file_and_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify FINDFMT_* environment variables override file settings while preserving others."""
    cfg = tmp_path / "config.toml"
    cfg.write_text("format = 'table'\nhidden = false\nmax_depth = 5\n", encoding="utf-8")

    monkeypatch.setenv("FINDFMT_HIDDEN", "true")
    monkeypatch.setenv("FINDFMT_MAX_DEPTH", "1")

    path, defaults = resolve_and_load_config(explicit_path=cfg)
    assert path == cfg
    assert defaults["output_format"] == OutputFormat.TABLE
    assert defaults["hidden"] is True
    assert defaults["max_depth"] == 1
    assert get_active_config_data() == {
        "format": "table",
        "hidden": True,
        "max_depth": 1,
    }


def test_cli_no_config_still_applies_env_vars_and_shows_in_show_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify --no-config suppresses TOML files while keeping FINDFMT_* overrides active."""
    cfg = tmp_path / "config.toml"
    cfg.write_text("format = 'table'\nmax_depth = 5\n", encoding="utf-8")
    monkeypatch.setenv("FINDFMT_CONFIG", str(cfg))
    monkeypatch.setenv("FINDFMT_FORMAT", "json")
    monkeypatch.setenv("FINDFMT_MAX_DEPTH", "2")

    runner = CliRunner()
    res = runner.invoke(app, ["--no-config", "--show-config"])
    assert res.exit_code == 0
    assert "Active configuration: (none)" in res.stdout
    assert "[tool.findfmt]" in res.stdout
    assert 'format = "json"' in res.stdout
    assert "max_depth = 2" in res.stdout
