"""Unit tests for Rust lint configuration and tools/verify_quality.py Cargo integration (#588)."""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path
from unittest.mock import patch

from tools import verify_quality
from tools.quality_steps import CARGO_MANIFEST, QUALITY_STEPS, prepare_step_execution


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def test_cargo_toml_rust_and_clippy_lints() -> None:
    """Verify strict [lints.rust] and [lints.clippy] tables in findfmt_rs/Cargo.toml (#588)."""
    cargo_toml = _repo_root() / CARGO_MANIFEST
    assert cargo_toml.is_file()
    with cargo_toml.open("rb") as f:
        data = tomllib.load(f)

    lints = data["lints"]
    assert lints["rust"] == {
        "unsafe_code": "deny",
        "missing_docs": "warn",
    }
    clippy = lints["clippy"]
    assert clippy["all"] == {"level": "warn", "priority": -1}
    assert clippy["pedantic"] == {"level": "warn", "priority": -1}
    assert clippy["unwrap_used"] == "deny"
    assert clippy["expect_used"] == "deny"
    assert clippy["dbg_macro"] == "deny"


def test_rustfmt_toml_configuration() -> None:
    """Verify findfmt_rs/rustfmt.toml sets edition 2024 and max_width 100 (#588)."""
    rustfmt_toml = _repo_root() / "findfmt_rs" / "rustfmt.toml"
    assert rustfmt_toml.is_file()
    with rustfmt_toml.open("rb") as f:
        data = tomllib.load(f)

    assert data == {
        "edition": "2024",
        "max_width": 100,
    }


def test_quality_steps_include_cargo_fmt_check_and_clippy_alongside_ruff_and_ty() -> None:
    """Verify QUALITY_STEPS runs cargo fmt, cargo check, and cargo clippy right after ruff and ty (#588)."""
    names = [name for name, _ in QUALITY_STEPS]
    cmds = dict(QUALITY_STEPS)

    assert names[:7] == [
        "Ruff Linter",
        "Ruff Formatter",
        "Ty Type Checker",
        "Cargo Formatter",
        "Cargo Check",
        "Cargo Clippy (Extension)",
        "Cargo Clippy (All Targets)",
    ]
    assert cmds["Cargo Formatter"] == (
        "cargo",
        "fmt",
        "--manifest-path",
        "findfmt_rs/Cargo.toml",
        "--check",
    )
    assert cmds["Cargo Check"] == (
        "cargo",
        "check",
        "--manifest-path",
        "findfmt_rs/Cargo.toml",
        "--locked",
    )
    assert cmds["Cargo Clippy (Extension)"] == (
        "cargo",
        "clippy",
        "--manifest-path",
        "findfmt_rs/Cargo.toml",
        "--locked",
        "--lib",
        "--",
        "-D",
        "warnings",
    )
    assert cmds["Cargo Clippy (All Targets)"] == (
        "cargo",
        "clippy",
        "--manifest-path",
        "findfmt_rs/Cargo.toml",
        "--locked",
        "--no-default-features",
        "--all-targets",
        "--",
        "-D",
        "warnings",
    )


def test_prepare_step_execution_resolves_rustup_cargo_path(tmp_path: Path) -> None:
    """Verify prepare_step_execution prepends ~/.cargo/bin for cargo commands only."""
    py_argv, py_env = prepare_step_execution(("uv", "run", "ruff", "check"), home_dir=tmp_path)
    assert py_argv == ["uv", "run", "ruff", "check"]
    assert py_env is None

    empty_argv, empty_env = prepare_step_execution((), home_dir=tmp_path)
    assert empty_argv == []
    assert empty_env is None

    # No ~/.cargo/bin directory and no cargo on PATH -> falls back cleanly to "cargo"
    with patch("tools.quality_steps.shutil.which", return_value=None) as mock_which_missing:
        no_bin_argv, no_bin_env = prepare_step_execution(
            ("cargo", "fmt", "--check"),
            home_dir=tmp_path,
            base_env={"PATH": "/usr/bin"},
        )

    assert no_bin_argv == ["cargo", "fmt", "--check"]
    assert no_bin_env == {"PATH": "/usr/bin"}
    mock_which_missing.assert_called_once_with("cargo", path="/usr/bin")

    # ~/.cargo/bin present -> prepended ahead of /usr/bin and deduplicated
    cargo_bin = tmp_path / ".cargo" / "bin"
    cargo_bin.mkdir(parents=True)
    fake_cargo = str(cargo_bin / "cargo")
    initial_path = os.pathsep.join(["/usr/bin", str(cargo_bin)])
    with patch("tools.quality_steps.shutil.which", return_value=fake_cargo) as mock_which:
        resolved_argv, resolved_env = prepare_step_execution(
            ("cargo", "clippy"),
            home_dir=tmp_path,
            base_env={"PATH": initial_path},
        )

    expected_path = os.pathsep.join([str(cargo_bin), "/usr/bin"])
    assert resolved_env == {"PATH": expected_path}
    assert resolved_argv == [fake_cargo, "clippy"]
    mock_which.assert_called_once_with("cargo", path=expected_path)

    # Already first in PATH -> preserved unchanged
    with patch("tools.quality_steps.shutil.which", return_value=fake_cargo) as mock_which_unchanged:
        _, unchanged_env = prepare_step_execution(
            ("cargo", "check"),
            home_dir=tmp_path,
            base_env={"PATH": expected_path},
        )

    assert unchanged_env == {"PATH": expected_path}
    mock_which_unchanged.assert_called_once_with("cargo", path=expected_path)


def test_run_quality_suite_executes_all_python_and_rust_steps() -> None:
    """Verify run_quality_suite dispatches every configured Python and Rust check in order."""
    with patch("tools.verify_quality.run_step", return_value=True) as mock_step:
        assert verify_quality.run_quality_suite() == 0

    assert [call.args for call in mock_step.call_args_list] == list(QUALITY_STEPS)

    ok_proc = subprocess.CompletedProcess(args=["cmd"], returncode=0)
    with patch("tools.verify_quality.subprocess.run", return_value=ok_proc) as mock_run:
        assert verify_quality.run_quality_suite() == 0

    assert mock_run.call_count == len(QUALITY_STEPS)
