"""Accessibility, terminal color, sanitization, and localized diagnostic parity tests (#589)."""

from __future__ import annotations

import errno
import importlib
import io
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

import pytest
from typer.testing import CliRunner

from findfmt import _fallback
from findfmt.cli import app
from findfmt.cli.diagnostics import (
    emit_cli_error,
    emit_traversal_error,
    format_traversal_error,
    get_diagnostics,
    sanitize_diagnostic_text,
)
from findfmt.cli.terminal import get_console, is_color_enabled
from findfmt.exceptions import (
    TraversalError,
    make_invalid_pattern_error,
    make_negative_bound_error,
    make_overflow_bound_error,
)
from findfmt.i18n import override_locale, reset_locale
from findfmt.models import TraversalConfig
from findfmt.traversal.patterns import compile_pattern_spec

if TYPE_CHECKING:
    import types
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _restore_default_locale() -> Iterator[None]:
    """Reset process-wide gettext state after CLI --locale invocations."""
    yield
    reset_locale()


class _MockTtyStream(io.StringIO):
    """In-memory stream reporting interactive TTY capability."""

    @override
    def isatty(self) -> bool:
        """Report interactive TTY state."""
        return True


def _load_rust_ext() -> types.ModuleType:
    """Import compiled findfmt._rust_ext or skip when built without Rust extensions."""
    try:
        return importlib.import_module("findfmt._rust_ext")
    except ModuleNotFoundError:
        pytest.skip("findfmt._rust_ext is not compiled in this environment")


def test_color_precedence_no_color_force_color_and_term_dumb() -> None:
    """Verify NO_COLOR, FORCE_COLOR, CLICOLOR_FORCE, CLICOLOR, and TERM=dumb precedence (#589)."""
    tty = _MockTtyStream()
    pipe = io.StringIO()

    assert is_color_enabled(tty, env={"TERM": "dumb"}) is False
    assert is_color_enabled(tty, env={"TERM": "  DUMB  "}) is False
    assert is_color_enabled(tty, env={"TERM": "xterm-256color"}) is True

    assert is_color_enabled(pipe, env={"FORCE_COLOR": "1"}) is True
    assert is_color_enabled(tty, env={"FORCE_COLOR": "1", "TERM": "dumb"}) is True
    assert is_color_enabled(tty, env={"FORCE_COLOR": "0"}) is False
    assert is_color_enabled(tty, env={"FORCE_COLOR": ""}) is True

    assert is_color_enabled(pipe, env={"NO_COLOR": "1", "FORCE_COLOR": "1"}) is False
    assert is_color_enabled(tty, env={"NO_COLOR": "1", "TERM": "xterm-256color"}) is False
    assert is_color_enabled(pipe, force_color=True, env={"NO_COLOR": "1", "TERM": "dumb"}) is True
    assert is_color_enabled(tty, force_color=False, env={"FORCE_COLOR": "1"}) is False

    dumb_off = get_console(tty, env={"TERM": "dumb"})
    assert dumb_off.no_color is True

    dumb_forced = get_console(tty, env={"TERM": "dumb", "FORCE_COLOR": "1"})
    assert dumb_forced.no_color is False
    assert dumb_forced.color_system == "standard"

    unknown_forced = get_console(tty, env={"TERM": "unknown", "FORCE_COLOR": "1", "CLICOLOR": "0"})
    assert unknown_forced.no_color is False
    assert unknown_forced.color_system == "standard"


@pytest.mark.parametrize(
    "env_case",
    [
        {"NO_COLOR": "1"},
        {"FORCE_COLOR": "1"},
        {"FORCE_COLOR": "0"},
        {"TERM": "dumb"},
        {"TERM": "dumb", "FORCE_COLOR": "1"},
    ],
)
def test_cli_color_and_summary_backend_parity(
    tmp_path: Path,
    env_case: dict[str, str],
) -> None:
    """Verify CLI output and stderr summary match across _rust_ext and _fallback (#589)."""
    _load_rust_ext()
    (tmp_path / "alpha.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("# Title\n", encoding="utf-8")
    runner = CliRunner()

    for fmt_args in (
        ["-f", "text"],
        ["-f", "table"],
        ["-f", "tree", "--summary"],
        ["-f", "table", "--color"],
        ["-f", "table", "--no-color"],
    ):
        rs_res = runner.invoke(
            app,
            [str(tmp_path), "--no-pager", *fmt_args],
            env={**env_case, "FINDFMT_NO_EXTENSIONS": "0"},
        )
        py_res = runner.invoke(
            app,
            [str(tmp_path), "--no-pager", *fmt_args],
            env={**env_case, "FINDFMT_NO_EXTENSIONS": "1"},
        )
        assert rs_res.exit_code == py_res.exit_code == 0
        assert rs_res.stdout == py_res.stdout
        assert rs_res.stderr == py_res.stderr
        if ("NO_COLOR" in env_case or env_case == {"TERM": "dumb"}) and "--color" not in fmt_args:
            assert "\x1b[" not in rs_res.stdout
            assert "\x1b[" not in rs_res.stderr


def test_sanitize_and_format_traversal_error_branches(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ANSI, C0/C1, BiDi, surrogate masking, and all OSError fallback branches (#589)."""
    assert sanitize_diagnostic_text("clean/path.py") == "clean/path.py"
    dirty = "\x1b[31mred\x1b[0m_\u202eevil\nline_\udcff"
    sanitized = sanitize_diagnostic_text(dirty)
    assert "\x1b" not in sanitized
    assert "\u202e" not in sanitized
    assert "\n" not in sanitized
    assert sanitized == "red_?evil?line_?"

    with override_locale("de"):
        e_unknown = OSError()
        assert "<unbekannt>" in format_traversal_error(e_unknown)
        assert "E/A-Fehler" in format_traversal_error(e_unknown)

        e_errno = OSError()
        e_errno.errno = errno.ENOENT
        assert format_traversal_error(e_errno).startswith("findfmt: '<unbekannt>'")

        e_bad_errno = OSError()
        e_bad_errno.errno = 1 << 40
        assert "E/A-Fehler" in format_traversal_error(e_bad_errno)

        e_arg_only = OSError("custom\x1b[32m_detail")
        formatted_arg = format_traversal_error(e_arg_only)
        assert "custom_detail" in formatted_arg
        assert "\x1b" not in formatted_arg

        emit_traversal_error(FileNotFoundError(errno.ENOENT, "msg\u202e", "bad\x1b[1mpath"))
        emit_cli_error("bad\u202e_cli\x1b[0m")
        err_out = capsys.readouterr().err
        assert "\x1b" not in err_out
        assert "\u202e" not in err_out
        assert "Fehler: bad?_cli" in err_out

    dirty_cfg = tmp_path / "\x1b[31mcfg\u202e.toml"
    clean_cfg = tmp_path / "cfg?.toml"
    monkeypatch.setattr(
        "findfmt.cli.file_config.get_active_config_path",
        lambda: dirty_cfg,
    )
    diag = get_diagnostics()
    assert "\x1b" not in diag
    assert "\u202e" not in diag
    assert f"Configuration: {clean_cfg}" in diag


@pytest.mark.parametrize(
    ("loc", "expected_fragment"),
    [
        ("en", "findfmt: cannot open"),
        ("de", "kann nicht geöffnet werden"),
        ("es", "no se puede abrir"),
        ("fr", "impossible d'ouvrir"),
        ("ja", "を開けません"),
    ],
)
def test_localized_sanitized_missing_root_parity_across_backends(
    tmp_path: Path,
    loc: str,
    expected_fragment: str,
) -> None:
    """Verify localized, BiDi/ANSI-sanitized missing-root diagnostics match across backends."""
    _load_rust_ext()
    runner = CliRunner()
    tricky_target = str(tmp_path / "missing_\u202e_dir")
    if sys.platform != "win32":
        tricky_target = str(tmp_path / "missing_\x1b[31m_\u202e_dir")

    rs_res = runner.invoke(
        app,
        ["--locale", loc, tricky_target],
        env={"FINDFMT_NO_EXTENSIONS": "0", "NO_COLOR": "1"},
    )
    py_res = runner.invoke(
        app,
        ["--locale", loc, tricky_target],
        env={"FINDFMT_NO_EXTENSIONS": "1", "NO_COLOR": "1"},
    )
    assert rs_res.exit_code == py_res.exit_code == 1
    assert rs_res.stderr == py_res.stderr
    assert expected_fragment in rs_res.stderr
    assert "\x1b" not in rs_res.stderr
    assert "\u202e" not in rs_res.stderr


def test_localized_bound_overflow_and_pattern_errors_parity(tmp_path: Path) -> None:
    """Verify negative bounds, usize overflow, and invalid globs localize identically (#589)."""
    rust_ext = _load_rust_ext()
    (tmp_path / "sample.py").write_text("x = 1\n", encoding="utf-8")

    with override_locale("fr"):
        assert "positif ou nul" in str(make_negative_bound_error("max_depth", -1))
        assert "plateforme" in str(make_overflow_bound_error("max_depth"))
        dirty_pat_err = str(make_invalid_pattern_error("bad\x1b[31m_\u202e\\"))
        assert "Motif glob" in dirty_pat_err
        assert "\x1b" not in dirty_pat_err
        assert "\u202e" not in dirty_pat_err

        with pytest.raises(ValueError, match="positif ou nul"):
            TraversalConfig(root_paths=(tmp_path,), max_depth=-2)

        bad_depth_cfg = TraversalConfig(root_paths=(tmp_path,))
        object.__setattr__(bad_depth_cfg, "max_depth", -2)
        bad_limit_cfg = TraversalConfig(root_paths=(tmp_path,))
        object.__setattr__(bad_limit_cfg, "file_limit", -3)
        for bad_cfg in (bad_depth_cfg, bad_limit_cfg):
            with pytest.raises(TraversalError) as rs_exc:
                list(rust_ext.find_files_rs(bad_cfg))

            with pytest.raises(TraversalError) as py_exc:
                list(_fallback.find_files(bad_cfg))

            assert str(rs_exc.value) == str(py_exc.value)
            assert "positif ou nul" in str(rs_exc.value)

        huge_cfg = TraversalConfig(root_paths=(tmp_path,), max_depth=1 << 100)
        with pytest.raises(OverflowError) as over_exc:
            list(rust_ext.find_files_rs(huge_cfg))

        assert "plateforme" in str(over_exc.value)

    with override_locale("ja"):
        for pat_tuple in (("bad\\",), ("bad\\|*.py",), ("*.py|bad\\",)):
            with pytest.raises((TraversalError, ValueError)) as rs_pat_exc:
                list(
                    rust_ext.find_files_rs(
                        TraversalConfig(root_paths=(tmp_path,), include_patterns=pat_tuple),
                    ),
                )

            with pytest.raises((TraversalError, ValueError)) as py_pat_exc:
                compile_pattern_spec(pat_tuple)

            assert isinstance(rs_pat_exc.value, TraversalError)
            assert isinstance(rs_pat_exc.value, ValueError)
            assert str(rs_pat_exc.value) == str(py_pat_exc.value)
            assert "無効な glob パターンです: 'bad\\'" in str(rs_pat_exc.value)

    runner = CliRunner()
    rs_cli = runner.invoke(
        app,
        ["--locale", "de", "-P", "bad\u202e\\", str(tmp_path)],
        env={"FINDFMT_NO_EXTENSIONS": "0"},
    )
    py_cli = runner.invoke(
        app,
        ["--locale", "de", "-P", "bad\u202e\\", str(tmp_path)],
        env={"FINDFMT_NO_EXTENSIONS": "1"},
    )
    assert rs_cli.exit_code == py_cli.exit_code == 2
    assert rs_cli.stderr == py_cli.stderr
    assert "Fehler: Ungültiges Glob-Muster" in rs_cli.stderr
    assert "\u202e" not in rs_cli.stderr
