"""Unit tests for configuration schema validation and value conversion rules."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from findfmt.cli.config_schema import (
    _convert_bool_val,
    _convert_format_val,
    _convert_int_val,
    _convert_str_list,
    _convert_str_val,
    _convert_tri_state,
    _extract_tool_section,
    validate_and_convert_config,
)
from findfmt.formatters import OutputFormat


def test_convert_format_val_success(tmp_path: Path):
    p = tmp_path / "c.toml"
    assert _convert_format_val("format", "table", p) == OutputFormat.TABLE
    assert _convert_format_val("format", "TREE", p) == OutputFormat.TREE
    assert _convert_format_val("format", "json", p) == OutputFormat.JSON
    assert _convert_format_val("format", "markdown", p) == OutputFormat.MARKDOWN


def test_convert_format_val_invalid_str(tmp_path: Path):
    p = tmp_path / "c.toml"
    with pytest.raises(typer.Exit) as exc:
        _convert_format_val("format", "invalid_mode", p)

    assert exc.value.exit_code == 2


def test_convert_format_val_non_str(tmp_path: Path):
    p = tmp_path / "c.toml"
    with pytest.raises(typer.Exit) as exc:
        _convert_format_val("format", 123, p)

    assert exc.value.exit_code == 2


def test_convert_tri_state(tmp_path: Path):
    p = tmp_path / "c.toml"
    val_true: bool = True
    val_false: bool = False
    assert _convert_tri_state("color", val_true, p) is True
    assert _convert_tri_state("color", val_false, p) is False
    assert _convert_tri_state("color", None, p) is None
    assert _convert_tri_state("color", "always", p) is True
    assert _convert_tri_state("color", "ALWAYS", p) is True
    assert _convert_tri_state("color", "true", p) is True
    assert _convert_tri_state("color", "yes", p) is True
    assert _convert_tri_state("color", "on", p) is True
    assert _convert_tri_state("color", "1", p) is True
    assert _convert_tri_state("color", "never", p) is False
    assert _convert_tri_state("color", "false", p) is False
    assert _convert_tri_state("color", "no", p) is False
    assert _convert_tri_state("color", "off", p) is False
    assert _convert_tri_state("color", "0", p) is False
    assert _convert_tri_state("color", "auto", p) is None

    with pytest.raises(typer.Exit) as exc:
        _convert_tri_state("color", "invalid", p)

    assert exc.value.exit_code == 2

    with pytest.raises(typer.Exit) as exc_non_str:
        _convert_tri_state("color", 12345, p)

    assert exc_non_str.value.exit_code == 2


def test_convert_bool_val(tmp_path: Path):
    p = tmp_path / "c.toml"
    val_true: bool = True
    val_false: bool = False
    assert _convert_bool_val("hidden", val_true, p, invert=False) is True
    assert _convert_bool_val("hidden", val_false, p, invert=False) is False
    assert _convert_bool_val("ignore", val_true, p, invert=True) is False
    assert _convert_bool_val("ignore", val_false, p, invert=True) is True

    with pytest.raises(typer.Exit) as exc:
        _convert_bool_val("hidden", "true", p, invert=False)

    assert exc.value.exit_code == 2


def test_convert_str_list(tmp_path: Path):
    p = tmp_path / "c.toml"
    assert _convert_str_list("tags", "python", p) == ["python"]
    assert _convert_str_list("tags", ["python", "shell"], p) == ["python", "shell"]

    with pytest.raises(typer.Exit) as exc:
        _convert_str_list("tags", 123, p)

    assert exc.value.exit_code == 2

    with pytest.raises(typer.Exit) as exc2:
        _convert_str_list("tags", ["python", 123], p)

    assert exc2.value.exit_code == 2


def test_convert_int_val(tmp_path: Path):
    p = tmp_path / "c.toml"
    assert _convert_int_val("max_depth", 5, p) == 5
    assert _convert_int_val("max_depth", 0, p) == 0

    with pytest.raises(typer.Exit) as exc:
        _convert_int_val("max_depth", -1, p)

    assert exc.value.exit_code == 2

    bool_val: bool = True
    with pytest.raises(typer.Exit) as exc2:
        _convert_int_val("max_depth", bool_val, p)

    assert exc2.value.exit_code == 2

    with pytest.raises(typer.Exit) as exc3:
        _convert_int_val("max_depth", "five", p)

    assert exc3.value.exit_code == 2


def test_convert_str_val(tmp_path: Path):
    p = tmp_path / "c.toml"
    assert _convert_str_val("table_style", "rounded", p) == "rounded"

    with pytest.raises(typer.Exit) as exc:
        _convert_str_val("table_style", 123, p)

    assert exc.value.exit_code == 2


def test_validate_and_convert_config_full(tmp_path: Path):
    p = tmp_path / "config.toml"
    raw = {
        "format": "table",
        "table_style": "rounded",
        "color": "always",
        "pager": "never",
        "hidden": True,
        "ignore": False,
        "tags": ["python"],
        "exclude-tags": ["test"],
        "max_depth": 3,
        "file_limit": 100,
        "sort": "size",
        "reverse": True,
        "gitignore_file": "/tmp/custom.gitignore",
    }
    converted = validate_and_convert_config(raw, p)
    assert converted["output_format"] == OutputFormat.TABLE
    assert converted["table_style"] == "rounded"
    assert converted["color"] is True
    assert converted["pager"] is False
    assert converted["hidden"] is True
    assert converted["no_ignore"] is True
    assert converted["tags"] == ["python"]
    assert converted["exclude_tags"] == ["test"]
    assert converted["max_depth"] == 3
    assert converted["file_limit"] == 100
    assert converted["sort"] == "size"
    assert converted["reverse"] is True
    assert converted["gitignore_file"] == Path("/tmp/custom.gitignore")


def test_validate_and_convert_config_unknown_key(tmp_path: Path):
    p = tmp_path / "config.toml"
    with pytest.raises(typer.Exit) as exc:
        validate_and_convert_config({"unknown_option": True}, p)

    assert exc.value.exit_code == 2


def test_extract_tool_section_standalone_no_findfmt(tmp_path: Path):
    p = tmp_path / "custom.toml"
    assert _extract_tool_section({"other": 123}, p) == {"other": 123}
    assert _extract_tool_section({"tool": {"other": 123}}, p) == {"tool": {"other": 123}}
