"""Unit tests for configuration file pre-scanning and path discovery precedence."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from findfmt.cli import (
    app,
    find_config_file,
    load_toml_config,
)
from findfmt.cli.file_config import (
    extract_config_args,
    reset_active_config,
)


@pytest.fixture(autouse=True)
def _cleanup_config_state():
    """Ensure active configuration state is clean before and after each test."""
    reset_active_config()
    yield
    reset_active_config()


# -----------------------------------------------------------------------------
# 1. extract_config_args tests
# -----------------------------------------------------------------------------


def test_extract_config_args_empty():
    cfg, no_cfg, show_cfg = extract_config_args([])
    assert cfg is None
    assert no_cfg is False
    assert show_cfg is False


def test_extract_config_args_flags():
    args = ["--no-config", "--show-config", "src"]
    cfg, no_cfg, show_cfg = extract_config_args(args)
    assert cfg is None
    assert no_cfg is True
    assert show_cfg is True


def test_extract_config_args_config_space():
    args = ["--config", "/path/to/cfg.toml", "-t", "python"]
    cfg, no_cfg, show_cfg = extract_config_args(args)
    assert cfg == "/path/to/cfg.toml"
    assert no_cfg is False
    assert show_cfg is False


def test_extract_config_args_config_equals():
    args = ["--config=/path/to/cfg.toml", "-t", "python"]
    cfg, no_cfg, show_cfg = extract_config_args(args)
    assert cfg == "/path/to/cfg.toml"
    assert no_cfg is False
    assert show_cfg is False


def test_extract_config_args_missing_value():
    args = ["--config"]
    cfg, no_cfg, show_cfg = extract_config_args(args)
    assert cfg is None
    assert no_cfg is False
    assert show_cfg is False


def test_extract_config_args_respects_double_dash():
    args = ["--", "--config", "/path/to/cfg.toml", "--no-config", "--show-config"]
    cfg, no_cfg, show_cfg = extract_config_args(args)
    assert cfg is None
    assert no_cfg is False
    assert show_cfg is False


# -----------------------------------------------------------------------------
# 2. find_config_file precedence tests
# -----------------------------------------------------------------------------


def test_find_config_file_no_config_flag():
    path, is_explicit = find_config_file(explicit_path="/some/path.toml", no_config=True)
    assert path is None
    assert is_explicit is False


def test_find_config_file_explicit_path():
    path, is_explicit = find_config_file(explicit_path="myconfig.toml")
    assert path == Path("myconfig.toml")
    assert is_explicit is True


def test_find_config_file_explicit_empty_string():
    path, is_explicit = find_config_file(explicit_path="")
    assert path is None
    assert is_explicit is False


def test_find_config_file_env_var(tmp_path: Path):
    cfg_file = tmp_path / "env_config.toml"
    cfg_file.write_text("format = 'json'\n")

    with patch.dict(os.environ, {"FINDFMT_CONFIG": str(cfg_file)}):
        path, is_explicit = find_config_file()
        assert path == cfg_file
        assert is_explicit is True


def test_find_config_file_env_var_empty_string():
    with patch.dict(os.environ, {"FINDFMT_CONFIG": ""}):
        path, is_explicit = find_config_file()
        assert path is None
        assert is_explicit is False


def test_find_config_file_explicit_overrides_env_var(tmp_path: Path):
    env_cfg = tmp_path / "env.toml"
    cli_cfg = tmp_path / "cli.toml"
    with patch.dict(os.environ, {"FINDFMT_CONFIG": str(env_cfg)}):
        path, is_explicit = find_config_file(explicit_path=cli_cfg)
        assert path == cli_cfg
        assert is_explicit is True


def test_find_config_file_xdg_env_var(tmp_path: Path):
    xdg_dir = tmp_path / "xdg"
    cfg_file = xdg_dir / "findfmt" / "config.toml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("format = 'table'\n")

    with (
        patch("platform.system", return_value="Linux"),
        patch.dict(os.environ, {"XDG_CONFIG_HOME": str(xdg_dir), "FINDFMT_CONFIG": ""}),
    ):
        path, is_explicit = find_config_file(no_config=False)
        assert path is None
        assert is_explicit is False

    with (
        patch("platform.system", return_value="Linux"),
        patch.dict(os.environ, {"XDG_CONFIG_HOME": str(xdg_dir)}),
    ):
        os.environ.pop("FINDFMT_CONFIG", None)
        path, is_explicit = find_config_file()
        assert path == cfg_file
        assert is_explicit is False


def test_find_config_file_windows_appdata(tmp_path: Path):
    appdata_dir = tmp_path / "AppData" / "Roaming"
    cfg_file = appdata_dir / "findfmt" / "config.toml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("format = 'json'\n")

    with (
        patch("platform.system", return_value="Windows"),
        patch.dict(os.environ, {"APPDATA": str(appdata_dir)}, clear=False),
    ):
        os.environ.pop("FINDFMT_CONFIG", None)
        path, is_explicit = find_config_file(cwd=tmp_path / "empty")
        assert path == cfg_file
        assert is_explicit is False


def test_find_config_file_windows_appdata_fallback(tmp_path: Path):
    home_dir = tmp_path / "home"
    cfg_file = home_dir / "AppData" / "Roaming" / "findfmt" / "config.toml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("format = 'json'\n")

    with (
        patch("platform.system", return_value="Windows"),
        patch("pathlib.Path.home", return_value=home_dir),
        patch.dict(os.environ, {}, clear=False),
    ):
        os.environ.pop("APPDATA", None)
        os.environ.pop("FINDFMT_CONFIG", None)
        path, is_explicit = find_config_file(cwd=tmp_path / "empty")
        assert path == cfg_file
        assert is_explicit is False


def test_find_config_file_posix_home_fallback(tmp_path: Path):
    home_dir = tmp_path / "home"
    cfg_file = home_dir / ".config" / "findfmt" / "config.toml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("format = 'json'\n")

    with (
        patch("platform.system", return_value="Linux"),
        patch("pathlib.Path.home", return_value=home_dir),
        patch.dict(os.environ, {}, clear=False),
    ):
        os.environ.pop("XDG_CONFIG_HOME", None)
        os.environ.pop("FINDFMT_CONFIG", None)
        path, is_explicit = find_config_file(cwd=tmp_path / "empty")
        assert path == cfg_file
        assert is_explicit is False


def test_find_config_file_pyproject_fallback(tmp_path: Path):
    work_dir = tmp_path / "project"
    work_dir.mkdir()
    pyproject = work_dir / "pyproject.toml"
    pyproject.write_text("[tool.findfmt]\nformat = 'json'\n")

    with (
        patch("platform.system", return_value="Linux"),
        patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path / "nonexistent")}, clear=False),
    ):
        os.environ.pop("FINDFMT_CONFIG", None)
        path, is_explicit = find_config_file(cwd=work_dir)
        assert path == pyproject
        assert is_explicit is False


def test_find_config_file_not_found(tmp_path: Path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with (
        patch("platform.system", return_value="Linux"),
        patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path / "nonexistent")}, clear=False),
    ):
        os.environ.pop("FINDFMT_CONFIG", None)
        path, is_explicit = find_config_file(cwd=empty_dir)
        assert path is None
        assert is_explicit is False


# -----------------------------------------------------------------------------
# 3. load_toml_config tests
# -----------------------------------------------------------------------------


def test_load_toml_config_missing_explicit(tmp_path: Path):
    nonexistent = tmp_path / "nonexistent.toml"
    with pytest.raises(typer.Exit) as exc:
        load_toml_config(nonexistent, is_explicit=True)

    assert exc.value.exit_code == 2


def test_load_toml_config_missing_implicit(tmp_path: Path):
    nonexistent = tmp_path / "nonexistent.toml"
    assert load_toml_config(nonexistent, is_explicit=False) == {}


def test_load_toml_config_invalid_syntax(tmp_path: Path):
    bad = tmp_path / "bad.toml"
    bad.write_text("invalid = = syntax\n")
    with pytest.raises(typer.Exit) as exc:
        load_toml_config(bad, is_explicit=True)

    assert exc.value.exit_code == 2


def test_load_toml_config_os_error(tmp_path: Path):
    bad = tmp_path / "unreadable.toml"
    bad.write_text("format = 'table'\n")

    with patch.object(Path, "open", side_effect=OSError("Permission denied")):
        with pytest.raises(typer.Exit) as exc:
            load_toml_config(bad, is_explicit=True)

        assert exc.value.exit_code == 2


def test_load_toml_config_pyproject_with_tool_section(tmp_path: Path):
    pyproj = tmp_path / "pyproject.toml"
    pyproj.write_text("[tool.findfmt]\nformat = 'table'\ntable_style = 'grid'\n")
    data = load_toml_config(pyproj, is_explicit=False)
    assert data == {"format": "table", "table_style": "grid"}


def test_load_toml_config_pyproject_without_tool_section(tmp_path: Path):
    pyproj = tmp_path / "pyproject.toml"
    pyproj.write_text("[project]\nname = 'test'\n")
    data = load_toml_config(pyproj, is_explicit=False)
    assert data == {}


def test_load_toml_config_pyproject_with_other_tool_only(tmp_path: Path):
    pyproj = tmp_path / "pyproject.toml"
    pyproj.write_text("[tool.black]\nline-length = 88\n")
    data = load_toml_config(pyproj, is_explicit=False)
    assert data == {}


def test_load_toml_config_standalone_top_level(tmp_path: Path):
    cfg = tmp_path / "findfmt.toml"
    cfg.write_text("format = 'table'\n")
    data = load_toml_config(cfg, is_explicit=True)
    assert data == {"format": "table"}


def test_load_toml_config_standalone_findfmt_table(tmp_path: Path):
    cfg = tmp_path / "findfmt.toml"
    cfg.write_text("[findfmt]\nformat = 'tree'\n")
    data = load_toml_config(cfg, is_explicit=True)
    assert data == {"format": "tree"}


def test_load_toml_config_standalone_tool_findfmt_table(tmp_path: Path):
    cfg = tmp_path / "findfmt.toml"
    cfg.write_text("[tool.findfmt]\nformat = 'json'\n")
    data = load_toml_config(cfg, is_explicit=True)
    assert data == {"format": "json"}


def test_env_var_overrides_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FINDFMT_MAX_DEPTH=1 beats config file, and loses to explicit CLI -L 3 (#456, #332)."""
    cfg = tmp_path / "config.toml"
    cfg.write_text("max_depth = 2\n", encoding="utf-8")

    root = tmp_path / "tree"
    (root / "d1" / "d2" / "d3").mkdir(parents=True)
    (root / "root.py").write_text("x = 0\n", encoding="utf-8")
    (root / "d1" / "lvl1.py").write_text("x = 1\n", encoding="utf-8")
    (root / "d1" / "d2" / "lvl2.py").write_text("x = 2\n", encoding="utf-8")
    (root / "d1" / "d2" / "d3" / "lvl3.py").write_text("x = 3\n", encoding="utf-8")

    monkeypatch.setenv("FINDFMT_MAX_DEPTH", "1")
    runner = CliRunner()

    # Env (max_depth=1) overrides config file (max_depth=2): only root.py matches at depth 1.
    res_env = runner.invoke(app, ["--config", str(cfg), str(root)])
    assert res_env.exit_code == 0
    assert "root.py" in res_env.stdout
    assert "lvl1.py" not in res_env.stdout
    assert "lvl2.py" not in res_env.stdout

    # Explicit CLI flag (-L 3) overrides env (max_depth=1): root.py, lvl1.py, lvl2.py match.
    res_cli = runner.invoke(app, ["--config", str(cfg), "-L", "3", str(root)])
    assert res_cli.exit_code == 0
    assert "root.py" in res_cli.stdout
    assert "lvl1.py" in res_cli.stdout
    assert "lvl2.py" in res_cli.stdout
    assert "lvl3.py" not in res_cli.stdout
