"""Tests for CI workflows, Mergify check parity, and Dependabot configuration."""

from __future__ import annotations

import fnmatch
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml
from tools import verify_quality
from tools.dep_matrix import load_supported_pythons

SHA40_RE = re.compile(r"^Swatinem/rust-cache@[0-9a-f]{40}$")
RUST_CI_WORKFLOW_JOBS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        ".github/workflows/ci.yml",
        (
            "quality-gate",
            "package-check",
            "packaging-smoke-test",
            "container-smoke-test",
            "dependency-smoke-matrix",
            "test-matrix",
        ),
    ),
    (
        ".github/workflows/perf-and-fuzz.yml",
        (
            "perf-tests",
            "rust-proptest-fuzz",
        ),
    ),
)


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_yaml_mapping(rel_path: Path) -> dict[str, Any]:
    """Load and parse a repository YAML mapping file."""
    full_path = _repo_root() / rel_path
    assert full_path.is_file(), f"Missing YAML file at {full_path}"
    with full_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), f"Expected YAML mapping in {full_path}"
    return data


def _load_dependabot_config() -> dict[str, Any]:
    """Load and parse .github/dependabot.yml."""
    return _load_yaml_mapping(Path(".github/dependabot.yml"))


def _load_ci_workflow() -> dict[str, Any]:
    """Load and parse .github/workflows/ci.yml."""
    return _load_yaml_mapping(Path(".github/workflows/ci.yml"))


def _get_gh_actions_groups() -> dict[str, Any]:
    """Return the groups dictionary for the github-actions ecosystem."""
    config = _load_dependabot_config()
    gh_actions = next(
        entry for entry in config["updates"] if entry.get("package-ecosystem") == "github-actions"
    )
    assert gh_actions.get("directory") == "/"
    groups = gh_actions.get("groups")
    assert isinstance(groups, dict), "github-actions entry must define dependency groups"
    return groups


def test_dependabot_config_structure_and_groups() -> None:
    """Validate Dependabot ecosystems and github-actions groups including rust-cache (#729)."""
    config = _load_dependabot_config()
    assert config.get("version") == 2
    updates = config.get("updates")
    assert isinstance(updates, list)
    ecosystems = {entry.get("package-ecosystem"): entry for entry in updates if isinstance(entry, dict)}
    assert {"github-actions", "pip"} <= set(ecosystems)

    pip_groups = ecosystems["pip"]["groups"]
    assert pip_groups["dev-dependencies"]["dependency-type"] == "development"
    assert pip_groups["production-dependencies"]["dependency-type"] == "production"

    groups = _get_gh_actions_groups()
    for group_name, sample_action in (
        ("codeql-action", "github/codeql-action/init"),
        ("actions", "actions/checkout"),
        ("docker", "docker/build-push-action"),
        ("clusterfuzzlite", "google/clusterfuzzlite/actions/build_fuzzers"),
        ("rust-cache", "Swatinem/rust-cache"),
    ):
        assert group_name in groups
        patterns = groups[group_name].get("patterns")
        assert isinstance(patterns, list)
        assert any(fnmatch.fnmatch(sample_action, pat) for pat in patterns)


def test_dependabot_covers_workflow_codeql_actions() -> None:
    """Assert all CodeQL action steps used across workflows match the group pattern."""
    codeql_patterns = _get_gh_actions_groups()["codeql-action"]["patterns"]
    workflow_files = list((_repo_root() / ".github" / "workflows").glob("*.yml"))
    assert workflow_files
    codeql_uses: set[str] = set()
    for wf in workflow_files:
        for line in wf.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("uses:") and "github/codeql-action" in stripped:
                action_ref = stripped.split("uses:")[1].strip().split("@")[0].split("#")[0].strip()
                codeql_uses.add(action_ref)

    assert codeql_uses
    for action in codeql_uses:
        assert any(fnmatch.fnmatch(action, pat) for pat in codeql_patterns)


def test_ci_dependency_smoke_matrix_structure_and_steps() -> None:
    """Validate dependency smoke matrix job configuration and steps in CI workflow."""
    ci = _load_ci_workflow()
    job = ci["jobs"]["dependency-smoke-matrix"]
    assert job.get("runs-on") == "ubuntu-latest"
    assert job.get("needs") == "quality-gate"
    assert job["strategy"]["fail-fast"] is False
    includes = job["strategy"]["matrix"]["include"]
    combinations = {(inc.get("resolution"), inc.get("prerelease")) for inc in includes}
    assert combinations == {("lowest-direct", "disallow"), ("highest", "allow")}

    steps = job["steps"]
    uv_step = next(s for s in steps if "astral-sh/setup-uv" in s.get("uses", ""))
    assert uv_step.get("with", {}).get("enable-cache") is True
    py_step = next(s for s in steps if "actions/setup-python" in s.get("uses", ""))
    assert str(py_step.get("with", {}).get("python-version")) == "3.11"
    install_run = next(s for s in steps if "Install Dependencies" in s.get("name", "")).get("run", "")
    assert "--resolution ${{ matrix.resolution }}" in install_run
    assert "--prerelease ${{ matrix.prerelease }}" in install_run
    diag_step = next(s for s in steps if "Capture Dependency Tree" in s.get("name", ""))
    assert diag_step.get("if") == "failure()"


def test_ci_hermetic_git_ignore_step() -> None:
    """Validate that CI jobs populate ~/.config/git/ignore before running pytest."""
    jobs = _load_ci_workflow()["jobs"]
    for job_name in ("test-matrix", "dependency-smoke-matrix"):
        steps = jobs[job_name]["steps"]
        hermetic_idx = next(i for i, s in enumerate(steps) if "Hermeticity" in s.get("name", ""))
        pytest_idx = next(i for i, s in enumerate(steps) if "Run Pytest" in s.get("name", ""))
        assert hermetic_idx < pytest_idx


def test_perf_marker_and_ci_job() -> None:
    """Validate perf marker registration, default deselection, and dedicated CI job (#345)."""
    with (_repo_root() / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)

    pytest_opts = data["tool"]["pytest"]["ini_options"]
    assert any(m.startswith("perf:") for m in pytest_opts.get("markers", []))
    assert "not perf" in pytest_opts.get("addopts", "")
    perf_wf = _load_yaml_mapping(Path(".github/workflows/perf-and-fuzz.yml"))
    perf_steps = perf_wf["jobs"]["perf-tests"]["steps"]
    assert any("pytest -m perf" in str(s.get("run", "")) for s in perf_steps)


def test_local_runner_covers_supported_pythons(capsys: pytest.CaptureFixture[str]) -> None:
    """Validate local runner Python version list matches classifiers and CI smoke step (#349)."""
    pyproject_path = _repo_root() / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    prefix = "Programming Language :: Python :: "
    classifier_versions = {
        c.removeprefix(prefix)
        for c in data["project"]["classifiers"]
        if isinstance(c, str) and c.startswith(prefix + "3.") and c.removeprefix(prefix)[2:].isdigit()
    }
    assert set(load_supported_pythons(pyproject_path)) == classifier_versions
    assert verify_quality.main(["--list"], repo_root=_repo_root()) == 0
    listed_versions = set(re.findall(r"py(3\.\d+)\s+\(python=3\.\d+\)", capsys.readouterr().out))
    assert listed_versions == classifier_versions

    qg_runs = [str(s.get("run", "")) for s in _load_ci_workflow()["jobs"]["quality-gate"]["steps"]]
    assert "uv run python tools/verify_quality.py --list" in qg_runs
    assert "uv run python tools/verify_quality.py" in qg_runs
    assert "uv run ruff check" not in qg_runs


def test_ci_fail_fast_policy_across_gating_and_diagnostic_matrices() -> None:
    """Validate gating OS/Python matrices fail fast while diagnostic matrices do not (#689)."""
    ci_jobs = _load_ci_workflow()["jobs"]
    assert ci_jobs["packaging-smoke-test"]["strategy"]["fail-fast"] is True
    assert ci_jobs["test-matrix"]["strategy"]["fail-fast"] is True
    assert ci_jobs["dependency-smoke-matrix"]["strategy"]["fail-fast"] is False

    pytest_step = next(s for s in ci_jobs["test-matrix"]["steps"] if "Run Pytest" in s.get("name", ""))
    assert pytest_step.get("continue-on-error") == "${{ matrix.experimental || false }}"

    dep_wf = _load_yaml_mapping(Path(".github/workflows/dependency-matrix.yml"))
    assert dep_wf["jobs"]["dependency-matrix"]["strategy"]["fail-fast"] is False
    cflite_wf = _load_yaml_mapping(Path(".github/workflows/cflite.yml"))
    assert cflite_wf["jobs"]["fuzzing"]["strategy"]["fail-fast"] is False


def _expand_test_matrix_cells(ci_jobs: dict[str, Any]) -> tuple[list[tuple[str, str, bool]], int]:
    """Expand effective (os, python_version, experimental) cells and count total macOS jobs."""
    matrix = ci_jobs["test-matrix"]["strategy"]["matrix"]
    excluded = {(str(e["os"]), str(e["python-version"])) for e in matrix.get("exclude", [])}
    cells = [
        (str(os_name), str(py_ver), False)
        for os_name in matrix["os"]
        for py_ver in matrix["python-version"]
        if (str(os_name), str(py_ver)) not in excluded
    ]
    cells.extend(
        (str(inc["os"]), str(inc["python-version"]), bool(inc.get("experimental", False)))
        for inc in matrix.get("include", [])
    )

    pkg_matrix = ci_jobs["packaging-smoke-test"]["strategy"]["matrix"]
    pkg_macos = sum(1 for os_name in pkg_matrix["os"] if os_name == "macos-latest") * len(
        pkg_matrix["python-version"],
    )
    test_macos = sum(1 for os_name, _, _ in cells if os_name == "macos-latest")
    return cells, pkg_macos + test_macos


def test_ci_test_matrix_trimmed_and_aligned_with_mergify() -> None:
    """Verify macOS/Windows run Python 3.11+3.15, macOS cap <= 4, and .mergify.yml parity (#729)."""
    ci_jobs = _load_ci_workflow()["jobs"]
    cells, total_macos_jobs = _expand_test_matrix_cells(ci_jobs)
    assert total_macos_jobs <= 4

    gating_cells = {(os_name, py_ver) for os_name, py_ver, exp in cells if not exp}
    expected_gating = {
        ("ubuntu-latest", "3.11"),
        ("ubuntu-latest", "3.12"),
        ("ubuntu-latest", "3.13"),
        ("ubuntu-latest", "3.14"),
        ("ubuntu-latest", "3.15"),
        ("macos-latest", "3.11"),
        ("macos-latest", "3.15"),
        ("windows-latest", "3.11"),
        ("windows-latest", "3.15"),
    }
    assert gating_cells == expected_gating
    assert ("ubuntu-latest", "3.16-dev", True) in cells

    expected_checks = {f"Test ({os_name} - Python {py_ver})" for os_name, py_ver in expected_gating}
    mergify = _load_yaml_mapping(Path(".mergify.yml"))
    rule = mergify["queue_rules"][0]
    for cond_key in ("queue_conditions", "merge_conditions"):
        actual_test_checks = {
            cond.removeprefix("check-success = ")
            for cond in rule[cond_key]
            if isinstance(cond, str) and cond.startswith("check-success = Test (")
        }
        assert actual_test_checks == expected_checks


def test_ci_rust_cache_pinned_by_sha_across_rust_jobs() -> None:
    """Verify every Rust-compiling CI job uses SHA-pinned Swatinem/rust-cache (#729)."""
    ci_lines = (_repo_root() / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8").splitlines()
    assert len(ci_lines) <= 350
    for wf_rel_path, job_names in RUST_CI_WORKFLOW_JOBS:
        wf_jobs = _load_yaml_mapping(Path(wf_rel_path))["jobs"]
        for job_name in job_names:
            steps = wf_jobs[job_name]["steps"]
            checkout_idx = next(
                i for i, s in enumerate(steps) if "actions/checkout@" in str(s.get("uses", ""))
            )
            cache_indices = [
                i for i, s in enumerate(steps) if "Swatinem/rust-cache@" in str(s.get("uses", ""))
            ]
            assert len(cache_indices) == 1, f"Expected Swatinem/rust-cache step in {wf_rel_path}:{job_name}"
            cache_idx = cache_indices[0]
            assert checkout_idx < cache_idx
            first_run_idx = next(
                i
                for i, s in enumerate(steps)
                if i > checkout_idx and ("uv " in str(s.get("run", "")) or "cargo " in str(s.get("run", "")))
            )
            assert cache_idx < first_run_idx
            step = steps[cache_idx]
            assert SHA40_RE.match(str(step["uses"]))
            workspaces = str(step.get("with", {}).get("workspaces", "")).splitlines()
            assert "findfmt_rs" in workspaces
            if job_name == "rust-proptest-fuzz":
                assert "findfmt_rs/fuzz" in workspaces
            elif job_name == "test-matrix":
                assert step.get("if") == "${{ steps.setup-python.outcome == 'success' }}"
                assert step.get("continue-on-error") == "${{ matrix.experimental || false }}"
