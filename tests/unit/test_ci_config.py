"""Tests for CI workflows and Dependabot configuration."""

import fnmatch
import tomllib
from pathlib import Path
from typing import Any

import yaml
from tools.dep_matrix import FULL_MATRIX


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_dependabot_config() -> dict[str, Any]:
    """Load and parse .github/dependabot.yml."""
    config_path = _repo_root() / ".github" / "dependabot.yml"
    assert config_path.is_file(), f"Missing dependabot configuration at {config_path}"
    with config_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "Dependabot config must be a YAML mapping"
    return data


def _get_gh_actions_groups() -> dict[str, Any]:
    """Return the groups dictionary for the github-actions ecosystem."""
    config = _load_dependabot_config()
    updates = config["updates"]
    gh_actions = next(
        entry for entry in updates if entry.get("package-ecosystem") == "github-actions"
    )
    assert gh_actions.get("directory") == "/"
    groups = gh_actions.get("groups")
    assert isinstance(groups, dict), "github-actions entry must define dependency groups"
    return groups


def test_dependabot_config_structure() -> None:
    """Validate root structure and required package ecosystems."""
    config = _load_dependabot_config()
    assert config.get("version") == 2
    updates = config.get("updates")
    assert isinstance(updates, list)

    ecosystems = {
        entry.get("package-ecosystem"): entry for entry in updates if isinstance(entry, dict)
    }
    assert "github-actions" in ecosystems
    assert "pip" in ecosystems


def test_dependabot_codeql_action_group() -> None:
    """Validate CodeQL Action dependency group and patterns."""
    groups = _get_gh_actions_groups()
    assert "codeql-action" in groups
    patterns = groups["codeql-action"].get("patterns")
    assert isinstance(patterns, list)
    assert any(fnmatch.fnmatch("github/codeql-action/init", pat) for pat in patterns)
    assert any(fnmatch.fnmatch("github/codeql-action/analyze", pat) for pat in patterns)
    assert any(fnmatch.fnmatch("github/codeql-action/upload-sarif", pat) for pat in patterns)


def test_dependabot_actions_group() -> None:
    """Validate official actions dependency group and patterns."""
    groups = _get_gh_actions_groups()
    assert "actions" in groups
    patterns = groups["actions"].get("patterns")
    assert isinstance(patterns, list)
    assert any(fnmatch.fnmatch("actions/checkout", pat) for pat in patterns)
    assert any(fnmatch.fnmatch("actions/setup-python", pat) for pat in patterns)


def test_dependabot_docker_and_fuzz_groups() -> None:
    """Validate docker and clusterfuzzlite dependency groups and patterns."""
    groups = _get_gh_actions_groups()
    assert "docker" in groups
    docker_patterns = groups["docker"].get("patterns")
    assert isinstance(docker_patterns, list)
    assert any(fnmatch.fnmatch("docker/build-push-action", pat) for pat in docker_patterns)
    assert "clusterfuzzlite" in groups
    fuzz_patterns = groups["clusterfuzzlite"].get("patterns")
    assert isinstance(fuzz_patterns, list)
    assert any(
        fnmatch.fnmatch("google/clusterfuzzlite/actions/build_fuzzers", pat)
        for pat in fuzz_patterns
    )


def _collect_workflow_codeql_actions() -> set[str]:
    """Scan all workflow files and collect github/codeql-action references."""
    repo = _repo_root()
    workflow_files = list((repo / ".github" / "workflows").glob("*.yml"))
    assert workflow_files, "No workflow files found in .github/workflows"
    codeql_uses: set[str] = set()
    for wf in workflow_files:
        with wf.open(encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("uses:") and "github/codeql-action" in stripped:
                    action_ref = (
                        stripped.split("uses:")[1].strip().split("@")[0].split("#")[0].strip()
                    )
                    codeql_uses.add(action_ref)

    return codeql_uses


def test_dependabot_covers_workflow_codeql_actions() -> None:
    """Assert all CodeQL action steps used across workflows match the group pattern."""
    groups = _get_gh_actions_groups()
    codeql_patterns = groups["codeql-action"]["patterns"]
    codeql_uses = _collect_workflow_codeql_actions()
    assert codeql_uses, "Expected at least one github/codeql-action step in workflows"
    for action in codeql_uses:
        assert any(fnmatch.fnmatch(action, pat) for pat in codeql_patterns), (
            f"Action {action} is not matched by codeql-action group patterns {codeql_patterns}"
        )


def test_dependabot_pip_groups() -> None:
    """Validate pip ecosystem groups for development and production dependencies."""
    config = _load_dependabot_config()
    updates = config["updates"]
    pip_entry = next(entry for entry in updates if entry.get("package-ecosystem") == "pip")
    assert pip_entry.get("directory") == "/"
    groups = pip_entry.get("groups")
    assert isinstance(groups, dict), "pip entry must define dependency groups"
    assert "dev-dependencies" in groups
    assert groups["dev-dependencies"].get("dependency-type") == "development"
    assert "production-dependencies" in groups
    assert groups["production-dependencies"].get("dependency-type") == "production"


def _load_ci_workflow() -> dict[str, Any]:
    """Load and parse .github/workflows/ci.yml."""
    ci_path = _repo_root() / ".github" / "workflows" / "ci.yml"
    assert ci_path.is_file(), f"Missing CI workflow at {ci_path}"
    with ci_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "CI workflow must be a YAML mapping"
    return data


def test_ci_dependency_smoke_matrix_structure() -> None:
    """Validate dependency smoke matrix job configuration in CI workflow."""
    ci = _load_ci_workflow()
    jobs = ci.get("jobs", {})
    assert "dependency-smoke-matrix" in jobs, "dependency-smoke-matrix job must be present in CI"
    job = jobs["dependency-smoke-matrix"]
    assert job.get("runs-on") == "ubuntu-latest"
    assert job.get("needs") == "quality-gate"
    strategy = job.get("strategy", {})
    assert strategy.get("fail-fast") is False
    matrix = strategy.get("matrix", {})
    includes = matrix.get("include", [])
    assert len(includes) == 2, "Smoke matrix should define exactly two curated combinations"
    combinations = {(inc.get("resolution"), inc.get("prerelease")) for inc in includes}
    expected = {("lowest-direct", "disallow"), ("highest", "allow")}
    assert combinations == expected, f"Expected {expected}, got {combinations}"


def test_ci_dependency_smoke_matrix_steps() -> None:
    """Validate dependency smoke matrix steps, cache usage, and diagnostics."""
    ci = _load_ci_workflow()
    steps = ci["jobs"]["dependency-smoke-matrix"].get("steps", [])
    assert len(steps) >= 5, "Expected setup, env creation, install, test, and diagnostic steps"
    uv_step = next(s for s in steps if "astral-sh/setup-uv" in s.get("uses", ""))
    assert uv_step.get("with", {}).get("enable-cache") is True, "setup-uv must enable cache sharing"
    py_step = next(s for s in steps if "actions/setup-python" in s.get("uses", ""))
    assert str(py_step.get("with", {}).get("python-version")) == "3.11"
    venv_step = next(s for s in steps if "Create Clean Virtual Environment" in s.get("name", ""))
    assert "--python 3.11" in venv_step.get("run", "")
    install_run = next(s for s in steps if "Install Dependencies" in s.get("name", "")).get(
        "run",
        "",
    )
    assert "--resolution ${{ matrix.resolution }}" in install_run
    assert "--prerelease ${{ matrix.prerelease }}" in install_run
    assert "--group test" in install_run
    test_step = next(s for s in steps if "Run Pytest" in s.get("name", ""))
    assert "pytest" in test_step.get("run", "")
    diag_step = next(s for s in steps if "Capture Dependency Tree" in s.get("name", ""))
    assert diag_step.get("if") == "failure()"
    assert "uv pip tree" in diag_step.get("run", "")


def test_ci_hermetic_git_ignore_step() -> None:
    """Validate that CI jobs populate ~/.config/git/ignore before running pytest."""
    jobs = _load_ci_workflow().get("jobs", {})
    for job_name in ("test-matrix", "dependency-smoke-matrix"):
        steps = jobs[job_name]["steps"]
        hermetic_idx = next(i for i, s in enumerate(steps) if "Hermeticity" in s.get("name", ""))
        pytest_idx = next(i for i, s in enumerate(steps) if "Run Pytest" in s.get("name", ""))
        assert hermetic_idx < pytest_idx, f"Hermeticity step must precede pytest in {job_name}"


def _load_dependency_matrix_workflow() -> dict[str, Any]:
    """Load and parse .github/workflows/dependency-matrix.yml."""
    wf_path = _repo_root() / ".github" / "workflows" / "dependency-matrix.yml"
    assert wf_path.is_file(), f"Missing dependency matrix workflow at {wf_path}"
    with wf_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "Dependency matrix workflow must be a YAML mapping"
    return data


def test_dependency_matrix_workflow_triggers_and_permissions() -> None:
    """Validate nightly schedule, workflow_dispatch inputs, and permissions (#429)."""
    workflow = _load_dependency_matrix_workflow()
    assert workflow.get("permissions") == {"contents": "read"}
    triggers = workflow.get("on", workflow.get(True, {}))
    assert isinstance(triggers, dict)
    schedule = triggers.get("schedule", [])
    assert isinstance(schedule, list)
    assert len(schedule) >= 1
    assert "cron" in schedule[0]

    dispatch = triggers.get("workflow_dispatch", {})
    assert isinstance(dispatch, dict)
    inputs = dispatch.get("inputs", {})
    assert {"resolution", "prerelease", "fork_strategy"} <= set(inputs.keys())
    assert set(inputs["resolution"]["options"]) == {"", "highest", "lowest", "lowest-direct"}
    assert set(inputs["prerelease"]["options"]) == {
        "",
        "disallow",
        "allow",
        "if-necessary",
        "explicit",
        "if-necessary-or-explicit",
    }
    assert set(inputs["fork_strategy"]["options"]) == {"", "fewest", "requires-python"}


def test_dependency_matrix_workflow_pruned_cells_and_steps() -> None:
    """Validate pruned M1-M6 matrix cells, fail-fast: false, and step summaries (#429)."""
    workflow = _load_dependency_matrix_workflow()
    jobs = workflow.get("jobs", {})
    assert "dependency-matrix" in jobs
    job = jobs["dependency-matrix"]
    assert "matrix." not in str(job.get("if", ""))
    assert job.get("runs-on") == "ubuntu-latest"
    strategy = job.get("strategy", {})
    assert strategy.get("fail-fast") is False

    includes = strategy.get("matrix", {}).get("include", [])
    assert len(includes) == 6
    actual_cells = [
        (
            inc.get("cell"),
            inc.get("resolution"),
            inc.get("prerelease"),
            inc.get("fork-strategy"),
        )
        for inc in includes
    ]
    expected_cells = [(c.cell_id, c.resolution, c.prerelease, c.fork_strategy) for c in FULL_MATRIX]
    assert actual_cells == expected_cells

    steps = job.get("steps", [])
    summary_step = next(
        s for s in steps if "Record Matrix Cell Result Summary" in s.get("name", "")
    )
    assert summary_step.get("if") == "always()"
    assert "GITHUB_STEP_SUMMARY" in summary_step.get("run", "")

    diag_step = next(s for s in steps if "Capture Dependency Tree on Failure" in s.get("name", ""))
    assert diag_step.get("if") == "failure()"
    assert "uv pip tree" in diag_step.get("run", "")
    assert "GITHUB_STEP_SUMMARY" in diag_step.get("run", "")


def test_perf_marker_and_ci_job() -> None:
    """Validate perf marker registration, default deselection, and dedicated CI job (#345)."""
    pyproject_path = _repo_root() / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    pytest_opts = data["tool"]["pytest"]["ini_options"]
    markers = pytest_opts.get("markers", [])
    assert any(m.startswith("perf:") for m in markers), "perf marker must be registered"
    addopts = pytest_opts.get("addopts", "")
    assert "not perf" in addopts, "default addopts must deselect perf marker"

    ci = _load_ci_workflow()
    jobs = ci.get("jobs", {})
    assert "perf-tests" in jobs, "CI workflow must define a dedicated perf-tests job"
    perf_steps = jobs["perf-tests"]["steps"]
    assert any("pytest -m perf" in str(s.get("run", "")) for s in perf_steps)
