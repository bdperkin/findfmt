"""Tests for CI workflows and Dependabot configuration."""

import fnmatch
import tomllib
from pathlib import Path
from typing import Any

import yaml


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
    job = ci["jobs"]["dependency-smoke-matrix"]
    steps = job.get("steps", [])
    assert len(steps) >= 5, "Expected setup, env creation, install, test, and diagnostic steps"

    uv_step = next(s for s in steps if "astral-sh/setup-uv" in s.get("uses", ""))
    assert uv_step.get("with", {}).get("enable-cache") is True, "setup-uv must enable cache sharing"

    install_step = next(s for s in steps if "Install Dependencies" in s.get("name", ""))
    install_run = install_step.get("run", "")
    assert "--resolution ${{ matrix.resolution }}" in install_run
    assert "--prerelease ${{ matrix.prerelease }}" in install_run
    assert "--group test" in install_run

    test_step = next(s for s in steps if "Run Pytest" in s.get("name", ""))
    assert "pytest" in test_step.get("run", "")

    diag_step = next(s for s in steps if "Capture Dependency Tree" in s.get("name", ""))
    assert diag_step.get("if") == "failure()"
    assert "uv pip tree" in diag_step.get("run", "")


def test_pyproject_dependency_minimums() -> None:
    """Validate declared dependency minimums match verified working floors."""
    pyproject_path = _repo_root() / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    deps = data.get("project", {}).get("dependencies", [])
    dep_dict: dict[str, str] = {}
    for dep in deps:
        name = dep.split(";")[0].strip()
        for op in (">=", "=="):
            if op in name:
                pkg, ver = name.split(op, 1)
                dep_dict[pkg.strip()] = ver.strip()

    assert dep_dict.get("pyyaml") == "6.0.1", "pyyaml floor must be >=6.0.1 for Python 3.12+ builds"
    assert dep_dict.get("rich") == "13.8", "rich floor must be >=13.8 for tree guide support"
    assert dep_dict.get("typer") == "0.16", "typer floor must be >=0.16 for Click compatibility"

    test_deps = data.get("dependency-groups", {}).get("test", [])
    test_dep_names = {d.split(";")[0].split(">=")[0].split("==")[0].strip() for d in test_deps}
    assert "docutils" in test_dep_names, "docutils must be in test dependency group"
    assert "hatchling" in test_dep_names, "hatchling must be in test dependency group"


def test_ci_hermetic_git_ignore_step() -> None:
    """Validate that CI jobs populate ~/.config/git/ignore before running pytest."""
    ci = _load_ci_workflow()
    jobs = ci.get("jobs", {})

    # test-matrix
    tm_steps = jobs["test-matrix"]["steps"]
    tm_hermetic_idx = next(i for i, s in enumerate(tm_steps) if "Hermeticity" in s.get("name", ""))
    tm_pytest_idx = next(i for i, s in enumerate(tm_steps) if "Run Pytest" in s.get("name", ""))
    assert tm_hermetic_idx < tm_pytest_idx, "Hermeticity step must precede pytest in test-matrix"

    # dependency-smoke-matrix
    dsm_steps = jobs["dependency-smoke-matrix"]["steps"]
    dsm_hermetic_idx = next(
        i for i, s in enumerate(dsm_steps) if "Hermeticity" in s.get("name", "")
    )
    dsm_pytest_idx = next(i for i, s in enumerate(dsm_steps) if "Run Pytest" in s.get("name", ""))
    assert dsm_hermetic_idx < dsm_pytest_idx, (
        "Hermeticity step must precede pytest in dependency-smoke-matrix"
    )


def test_ci_uses_locked_sync() -> None:
    """Validate that every uv sync step across all workflow files includes --locked."""
    workflows_dir = _repo_root() / ".github" / "workflows"
    workflow_files = sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))
    assert len(workflow_files) > 0, "No workflow files found"

    sync_steps_found = 0
    for wf_path in workflow_files:
        with wf_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            continue

        jobs = data.get("jobs", {})
        for job_name, job_data in jobs.items():
            if not isinstance(job_data, dict):
                continue

            steps = job_data.get("steps", [])
            for step in steps:
                if not isinstance(step, dict):
                    continue

                run_cmd = step.get("run", "")
                for line in run_cmd.splitlines():
                    if "uv sync" in line:
                        sync_steps_found += 1
                        assert "--locked" in line, (
                            f"Step {step.get('name', 'unnamed')} in {wf_path.name}:{job_name} "
                            f"executes uv sync without --locked: {line}"
                        )

    assert sync_steps_found >= 5, f"Expected at least 5 uv sync steps, found {sync_steps_found}"


def test_version_sensitive_checkouts_fetch_full_history() -> None:
    """Validate that version-sensitive workflows configure fetch-depth: 0 on actions/checkout."""
    workflows_dir = _repo_root() / ".github" / "workflows"

    version_sensitive_jobs = [
        (workflows_dir / "ci.yml", "packaging-smoke-test"),
        (workflows_dir / "docs.yml", "build"),
        (workflows_dir / "release.yml", "build-distributions"),
        (workflows_dir / "release.yml", "verify-release"),
    ]

    for wf_path, job_name in version_sensitive_jobs:
        assert wf_path.is_file(), f"Missing workflow file: {wf_path}"
        with wf_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        job = data.get("jobs", {}).get(job_name)
        assert job is not None, f"Job {job_name} not found in {wf_path.name}"

        steps = job.get("steps", [])
        checkout_step = next(
            (s for s in steps if "actions/checkout" in s.get("uses", "")),
            None,
        )
        assert checkout_step is not None, f"Checkout step missing in {wf_path.name}:{job_name}"

        with_cfg = checkout_step.get("with", {})
        assert with_cfg.get("fetch-depth") == 0, (
            f"Job {job_name} in {wf_path.name} must set fetch-depth: 0 for actions/checkout, "
            f"got {with_cfg.get('fetch-depth')}"
        )


MINIMUM_PYTHON = (3, 11)


def _load_pyproject() -> dict[str, Any]:
    """Load and parse pyproject.toml."""
    with (_repo_root() / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)


def _minor_version(version: str) -> tuple[int, int]:
    """Parse a ``3.X`` or ``3.X-dev`` version string into a ``(major, minor)`` tuple."""
    major, minor = version.split("-", 1)[0].split(".")[:2]
    return int(major), int(minor)


def test_requires_python_minimum_is_3_11() -> None:
    """Validate the declared minimum Python version is 3.11 (Python 3.10 is EOL)."""
    assert _load_pyproject()["project"]["requires-python"] == ">=3.11"


def test_no_python_classifiers_below_minimum() -> None:
    """Validate no ``Programming Language :: Python :: 3.X`` classifier is below the minimum."""
    prefix = "Programming Language :: Python :: 3."
    classifiers = _load_pyproject()["project"]["classifiers"]
    versions = [c.removeprefix("Programming Language :: Python :: ") for c in classifiers]
    below = [
        v
        for c, v in zip(classifiers, versions, strict=True)
        if c.startswith(prefix) and v[2:].isdigit() and _minor_version(v) < MINIMUM_PYTHON
    ]
    assert not below, f"Classifiers below Python {MINIMUM_PYTHON}: {below}"


def test_ci_matrix_excludes_eol_python() -> None:
    """Validate the CI test matrix runs no Python version below the minimum."""
    matrix = _load_ci_workflow()["jobs"]["test-matrix"]["strategy"]["matrix"]
    versions = [str(v) for v in matrix["python-version"]]
    versions += [str(e["python-version"]) for e in matrix.get("include", [])]
    assert versions, "test-matrix must define python-version entries"
    below = [v for v in versions if _minor_version(v) < MINIMUM_PYTHON]
    assert not below, f"CI matrix includes Python versions below {MINIMUM_PYTHON}: {below}"


def test_tomli_not_a_dependency() -> None:
    """Validate tomli is not declared anywhere now that tomllib is always available."""
    data = _load_pyproject()

    def _names(specs: list[Any]) -> set[str]:
        return {
            s.split(";")[0].split(">=")[0].split("==")[0].strip().lower()
            for s in specs
            if isinstance(s, str)
        }

    assert "tomli" not in _names(data["project"]["dependencies"])
    for group, specs in data.get("dependency-groups", {}).items():
        assert "tomli" not in _names(specs), f"tomli found in dependency group {group!r}"

    ignores = data["tool"]["deptry"].get("per_rule_ignores", {})
    for rule, packages in ignores.items():
        assert "tomli" not in packages, f"tomli found in deptry {rule} ignores"


def test_ruff_target_matches_requires_python() -> None:
    """Validate ruff's target version matches the minimum supported Python."""
    assert _load_pyproject()["tool"]["ruff"]["target-version"] == "py311"
