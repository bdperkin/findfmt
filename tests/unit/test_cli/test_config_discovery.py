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


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ([], (None, False, False)),
        (["--no-config", "--show-config", "src"], (None, True, True)),
        (["--config", "/path/to/cfg.toml", "-t", "python"], ("/path/to/cfg.toml", False, False)),
        (["--config=/path/to/cfg.toml", "-t", "python"], ("/path/to/cfg.toml", False, False)),
        (["--config"], (None, False, False)),
        (
            ["--", "--config", "/path/to/cfg.toml", "--no-config", "--show-config"],
            (None, False, False),
        ),
    ],
)
def test_extract_config_args(args: list[str], expected: tuple[str | None, bool, bool]) -> None:
    assert extract_config_args(args) == expected


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


@pytest.mark.parametrize(
    ("filename", "content", "expected"),
    [
        (
            "pyproject.toml",
            "[tool.findfmt]\nformat = 'table'\ntable_style = 'grid'\n",
            {"format": "table", "table_style": "grid"},
        ),
        ("pyproject.toml", "[project]\nname = 'test'\n", {}),
        ("pyproject.toml", "[tool.black]\nline-length = 88\n", {}),
        ("findfmt.toml", "format = 'table'\n", {"format": "table"}),
        ("findfmt.toml", "[findfmt]\nformat = 'tree'\n", {"format": "tree"}),
        ("findfmt.toml", "[tool.findfmt]\nformat = 'json'\n", {"format": "json"}),
    ],
)
def test_load_toml_config_sections(
    tmp_path: Path,
    filename: str,
    content: str,
    expected: dict[str, str],
) -> None:
    cfg = tmp_path / filename
    cfg.write_text(content, encoding="utf-8")
    assert load_toml_config(cfg, is_explicit=filename != "pyproject.toml") == expected


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


@pytest.mark.parametrize(
    ("layers", "expected_marker"),
    [
        (("csv", None, None, None), "path,relative_path,tags,mime_type"),
        (("csv", "tsv", None, None), "path\trelative_path\ttags\tmime_type"),
        (("csv", None, "json", None), '"path":'),
        ((None, "tsv", "json", None), '"path":'),
        (("csv", "tsv", "json", None), '"path":'),
        (("csv", "tsv", "json", "yaml"), "path:"),
        (("csv", "tsv", None, "yaml"), "path:"),
    ],
)
def test_precedence_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    layers: tuple[str | None, str | None, str | None, str | None],
    expected_marker: str,
) -> None:
    """Verify full configuration precedence: user < project < env < CLI (#455, #332)."""
    user_fmt, proj_fmt, env_fmt, cli_fmt = layers
    xdg_dir = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))
    monkeypatch.setenv("APPDATA", str(xdg_dir))
    monkeypatch.delenv("FINDFMT_CONFIG", raising=False)
    monkeypatch.delenv("FINDFMT_FORMAT", raising=False)

    if user_fmt is not None:
        user_cfg = xdg_dir / "findfmt" / "config.toml"
        user_cfg.parent.mkdir(parents=True)
        user_cfg.write_text(f'format = "{user_fmt}"\n', encoding="utf-8")

    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "sample.py").write_text("x = 1\n", encoding="utf-8")
    if proj_fmt is not None:
        (repo / "pyproject.toml").write_text(
            f'[tool.findfmt]\nformat = "{proj_fmt}"\n',
            encoding="utf-8",
        )

    if env_fmt is not None:
        monkeypatch.setenv("FINDFMT_FORMAT", env_fmt)

    monkeypatch.chdir(repo)
    cli_args: list[str] = ["-f", cli_fmt] if cli_fmt is not None else []
    res = CliRunner().invoke(app, [*cli_args, str(repo)])
    assert res.exit_code == 0
    assert expected_marker in res.stdout


def test_user_and_project_configs_merge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User config (hidden=true) and project config (max_depth=1) merge (#455, #332)."""
    xdg_dir = tmp_path / "xdg"
    user_cfg = xdg_dir / "findfmt" / "config.toml"
    user_cfg.parent.mkdir(parents=True)
    user_cfg.write_text('hidden = true\nformat = "csv"\n', encoding="utf-8")

    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "sub").mkdir()
    (repo / ".secret.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "sub" / "deep.py").write_text("x = 2\n", encoding="utf-8")
    proj_cfg = repo / ".findfmt.toml"
    proj_cfg.write_text('max_depth = 1\nformat = "json"\n', encoding="utf-8")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))
    monkeypatch.setenv("APPDATA", str(xdg_dir))
    monkeypatch.delenv("FINDFMT_CONFIG", raising=False)
    monkeypatch.chdir(repo)

    runner = CliRunner()
    res_show = runner.invoke(app, ["--show-config"])
    assert res_show.exit_code == 0
    assert f"Active configuration: {proj_cfg}" in res_show.stdout
    assert "hidden = true" in res_show.stdout
    assert "max_depth = 1" in res_show.stdout
    assert 'format = "json"' in res_show.stdout

    res_run = runner.invoke(app, [str(repo)])
    assert res_run.exit_code == 0
    assert ".secret.py" in res_run.stdout
    assert "deep.py" not in res_run.stdout


def test_pyproject_found_by_walking_up_to_vcs_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Walk up from repo/pkg/sub to repo/pyproject.toml, stopping at VCS root (#455, #332)."""
    outer = tmp_path / "outer"
    outer.mkdir()
    (outer / "pyproject.toml").write_text('[tool.findfmt]\nformat = "csv"\n', encoding="utf-8")

    repo = outer / "repo"
    (repo / ".git").mkdir(parents=True)
    repo_pyproject = repo / "pyproject.toml"
    repo_pyproject.write_text('[tool.findfmt]\nformat = "json"\n', encoding="utf-8")

    sub = repo / "pkg" / "sub"
    sub.mkdir(parents=True)
    # Subpackage pyproject.toml without [tool.findfmt] is skipped during upward walk.
    (repo / "pkg" / "pyproject.toml").write_text('[project]\nname = "pkg"\n', encoding="utf-8")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty_xdg"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "empty_xdg"))
    monkeypatch.delenv("FINDFMT_CONFIG", raising=False)
    monkeypatch.chdir(sub)

    runner = CliRunner()
    res = runner.invoke(app, ["--show-config"])
    assert res.exit_code == 0
    assert f"Active configuration: {repo_pyproject}" in res.stdout
    assert 'format = "json"' in res.stdout

    # Removing repo/pyproject.toml must NOT walk past repo/.git into outer/pyproject.toml.
    repo_pyproject.unlink()
    res_stopped = runner.invoke(app, ["--show-config"])
    assert res_stopped.exit_code == 0
    assert "Active configuration: (none)" in res_stopped.stdout

    # Invalid pyproject.toml discovered via upward walk triggers TOML syntax error (exit 2).
    repo_pyproject.write_text("invalid = = =\n", encoding="utf-8")
    res_bad = runner.invoke(app, ["--show-config"])
    assert res_bad.exit_code == 2
