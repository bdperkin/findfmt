"""Tests for dual Python/Rust Codecov configuration, CI test-matrix, and tools/rust_coverage.py (#590)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import yaml
from tools.rust_coverage import (
    DEFAULT_IGNORE_REGEX,
    build_base_env,
    collect_rust_coverage,
    main,
    parse_llvm_cov_env,
    verify_lcov_line_coverage,
)

if TYPE_CHECKING:
    import pytest


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_yaml(rel_path: str) -> dict[str, Any]:
    """Load a YAML configuration file from the repository root."""
    path = _repo_root() / rel_path
    assert path.is_file(), f"Missing expected file {path}"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict)
    return data


def test_codecov_yml_enforces_100_percent_python_and_rust_coverage() -> None:
    """Verify codecov.yml tracks findfmt_rs, defines rust flag, and enforces 100% targets (#590)."""
    cfg = _load_yaml("codecov.yml")

    status = cfg["coverage"]["status"]
    for proj_key in ("default", "python", "rust"):
        assert status["project"][proj_key]["target"] == "100%"
        assert status["project"][proj_key]["threshold"] == "0%"

    assert status["project"]["python"]["paths"] == ["src/findfmt"]
    assert status["project"]["rust"]["paths"] == ["findfmt_rs/src"]
    assert status["patch"]["default"]["target"] == "100%"
    assert status["patch"]["default"]["threshold"] == "0%"

    components = {c["component_id"]: c for c in cfg["component_management"]["individual_components"]}
    assert "findfmt_rs" in components
    assert components["findfmt_rs"]["paths"] == ["findfmt_rs/src/**"]

    flags = cfg["flags"]
    assert flags["unittests"]["paths"] == ["src/findfmt"]
    assert flags["rust"]["paths"] == ["findfmt_rs/src"]
    assert flags["rust"]["carryforward"] is True

    ignore_patterns = set(cfg["ignore"])
    assert {
        "findfmt_rs/fuzz/**/*",
        "findfmt_rs/tests/**/*",
        "findfmt_rs/src/*_tests.rs",
    } <= ignore_patterns
    assert not any("fuzz_entrypoints" in pat for pat in ignore_patterns)


def test_ci_test_matrix_integrates_cross_os_dual_python_and_rust_coverage() -> None:
    """Verify test-matrix runs dual Python + Rust 100% coverage across Ubuntu, macOS, and Windows (#590)."""
    ci_cfg = _load_yaml(".github/workflows/ci.yml")
    assert "rust-coverage" not in ci_cfg["jobs"]

    job = ci_cfg["jobs"]["test-matrix"]
    os_expr = str(job["strategy"]["matrix"]["os"])
    for os_name in ("ubuntu-latest", "macos-latest", "windows-latest"):
        assert os_name in os_expr

    steps = job["steps"]
    install_llvm = next(s for s in steps if s.get("name") == "Install llvm-tools-preview")
    assert "rustup component add llvm-tools-preview" in str(install_llvm["run"])
    assert install_llvm["if"] == "${{ steps.setup-python.outcome == 'success' }}"
    assert install_llvm["continue-on-error"] == "${{ matrix.experimental || false }}"

    install_cov = next(s for s in steps if s.get("name") == "Install cargo-llvm-cov")
    assert re.fullmatch(r"taiki-e/install-action@[0-9a-f]{40}", str(install_cov["uses"]))
    assert install_cov["with"]["tool"] == "cargo-llvm-cov"
    assert install_cov["if"] == "${{ steps.setup-python.outcome == 'success' }}"
    assert install_cov["continue-on-error"] == "${{ matrix.experimental || false }}"

    collect_step = next(s for s in steps if "tools/rust_coverage.py" in str(s.get("run", "")))
    assert collect_step["run"] == "uv run python tools/rust_coverage.py --pytest-cov"
    assert collect_step["if"] == "${{ steps.setup-python.outcome == 'success' }}"

    py_upload = next(s for s in steps if s.get("name") == "Upload Coverage to Codecov")
    assert py_upload["with"]["files"] == "./coverage.xml"
    assert py_upload["with"]["flags"] == "unittests"

    rs_upload = next(s for s in steps if s.get("name") == "Upload Rust Coverage to Codecov")
    assert re.fullmatch(r"codecov/codecov-action@[0-9a-f]{40}", str(rs_upload["uses"]))
    assert rs_upload["with"]["files"] == "./rust-lcov.info"
    assert rs_upload["with"]["flags"] == "rust"
    assert rs_upload["if"] == "${{ !matrix.experimental }}"


def test_default_ignore_regex_keeps_fuzz_entrypoints_and_skips_tests() -> None:
    """Verify DEFAULT_IGNORE_REGEX excludes tests/fuzz/inline _tests.rs while keeping fuzz_entrypoints.rs."""
    pattern = re.compile(DEFAULT_IGNORE_REGEX)
    assert pattern.search("findfmt_rs/tests/proptest_classifier.rs")
    assert pattern.search("findfmt_rs/fuzz/fuzz_targets/fuzz_shebang_header.rs")
    assert pattern.search("findfmt_rs/src/classifier_tests.rs")
    assert pattern.search(r"findfmt_rs\src\tags_tests.rs")

    assert not pattern.search("findfmt_rs/src/fuzz_entrypoints.rs")
    assert not pattern.search("findfmt_rs/src/lib.rs")
    assert not pattern.search("findfmt_rs/src/walker.rs")


def test_parse_llvm_cov_env_and_build_base_env(tmp_path: Path) -> None:
    """Verify parse_llvm_cov_env handles Windows/POSIX formats and build_base_env sets PyO3 paths."""
    sample = r"""
    # comment line
    set LLVM_PROFILE_FILE=C:\Users\runneradmin\findfmt_rs\target\findfmt-%p-%16m.profraw
    export RUSTFLAGS='-C instrument-coverage'
    CARGO_LLVM_COV=1
    """
    parsed = parse_llvm_cov_env(sample)
    assert parsed == {
        "LLVM_PROFILE_FILE": r"C:\Users\runneradmin\findfmt_rs\target\findfmt-%p-%16m.profraw",
        "RUSTFLAGS": "-C instrument-coverage",
        "CARGO_LLVM_COV": "1",
    }

    cargo_bin = tmp_path / ".cargo" / "bin"
    cargo_bin.mkdir(parents=True)
    env = build_base_env(
        home_dir=tmp_path,
        raw_env={"PATH": "/usr/bin", "FINDFMT_NO_EXTENSIONS": "1"},
    )
    assert "FINDFMT_NO_EXTENSIONS" not in env
    assert "PYO3_PYTHON" in env
    assert env["PATH"].startswith(str(cargo_bin))


def test_collect_rust_coverage_pipeline_and_failure_modes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify collect_rust_coverage orchestrates commands, --pytest-cov, and LCOV line thresholds."""
    lcov_out = tmp_path / "rust-lcov.info"
    lcov_out.write_text(
        "TN:\nSF:findfmt_rs/src/lib.rs\nDA:10,4\nDA:11,2\nLF:5\nLH:3\nend_of_record\n",
        encoding="utf-8",
    )
    recorded_cmds: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded_cmds.append(list(cmd))
        if "show-env" in cmd:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout="set CARGO_LLVM_COV=1\n",
                stderr="",
            )

        assert kwargs.get("env") is not None
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    with patch("tools.rust_coverage.subprocess.run", side_effect=fake_run):
        assert main(["--output-path", str(lcov_out), "--pytest-cov"]) == 0

    assert len(recorded_cmds) == 7
    pytest_cmd = next(c for c in recorded_cmds if "pytest" in c)
    assert "--no-cov" not in pytest_cmd
    normalized = lcov_out.read_text(encoding="utf-8")
    assert "LF:2\nLH:2\nend_of_record" in normalized

    recorded_cmds.clear()
    with patch("tools.rust_coverage.subprocess.run", side_effect=fake_run):
        assert main(["--output-path", str(lcov_out)]) == 0

    pytest_nocov = next(c for c in recorded_cmds if "pytest" in c)
    assert "--no-cov" in pytest_nocov

    recorded_cmds.clear()
    with patch("tools.rust_coverage.subprocess.run", side_effect=fake_run):
        assert collect_rust_coverage(output_path=str(lcov_out), pytest_mode="skip") == 0

    assert len(recorded_cmds) == 5
    assert not any("maturin" in c for c in recorded_cmds)

    assert verify_lcov_line_coverage(tmp_path / "missing.info", 100.0) == 1
    partial_lcov = tmp_path / "partial.info"
    partial_lcov.write_text(
        "SF:findfmt_rs/src/walker.rs\nDA:1,3\nDA:2,0\nLF:2\nLH:1\nend_of_record\n",
        encoding="utf-8",
    )
    assert verify_lcov_line_coverage(partial_lcov, 100.0) == 1
    assert "walker.rs: 2" in capsys.readouterr().err

    with patch(
        "tools.rust_coverage.subprocess.run",
        return_value=subprocess.CompletedProcess(["cargo"], 2, stdout="", stderr="llvm-cov missing\n"),
    ):
        assert collect_rust_coverage(output_path=str(lcov_out)) == 2

    assert "llvm-cov missing" in capsys.readouterr().err

    step_calls = 0

    def fail_on_clean(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal step_calls
        step_calls += 1
        rc = 0 if step_calls == 1 else 3
        return subprocess.CompletedProcess(cmd, rc, stdout="set CARGO_LLVM_COV=1\n", stderr="")

    with patch("tools.rust_coverage.subprocess.run", side_effect=fail_on_clean):
        assert collect_rust_coverage(output_path=str(lcov_out)) == 3
