"""Python version support policy: supported range, CI coverage, and container image."""

import re
import tomllib
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_ci_workflow() -> dict[str, Any]:
    """Load and parse .github/workflows/ci.yml."""
    with (_repo_root() / ".github" / "workflows" / "ci.yml").open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "CI workflow must be a YAML mapping"
    return data


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


NON_GATING_EXPR = "${{ matrix.experimental || false }}"
NEXT_PYTHON_DEV = "3.16-dev"


def _test_matrix_job() -> dict[str, Any]:
    """Return the ``test-matrix`` job from ci.yml."""
    return _load_ci_workflow()["jobs"]["test-matrix"]


def _classifier_versions() -> list[str]:
    """Return the ``3.X`` versions advertised by ``Programming Language :: Python`` classifiers."""
    prefix = "Programming Language :: Python :: "
    return [
        c.removeprefix(prefix)
        for c in _load_pyproject()["project"]["classifiers"]
        if c.startswith(prefix + "3.") and c.removeprefix(prefix)[2:].isdigit()
    ]


def test_classifiers_match_required_ci_matrix() -> None:
    """Validate every advertised Python version runs in CI as a gating, non-experimental job."""
    job = _test_matrix_job()
    matrix = job["strategy"]["matrix"]
    experimental = {
        str(e["python-version"]) for e in matrix.get("include", []) if e.get("experimental")
    }
    gating = {str(v) for v in matrix["python-version"]} - experimental

    assert "continue-on-error" not in job, "test-matrix must not set job-level continue-on-error"
    for step in job["steps"]:
        if "continue-on-error" in step:
            assert step["continue-on-error"] == NON_GATING_EXPR, (
                f"Step {step.get('name')!r} may only continue on error for experimental entries"
            )

    missing = [v for v in _classifier_versions() if v not in gating]
    assert not missing, f"Advertised Python versions without a gating CI job: {missing}"


def test_next_python_ci_job_is_non_gating() -> None:
    """Validate the next Python release runs as a non-gating preview job and is not advertised."""
    job = _test_matrix_job()
    previews = [
        e
        for e in job["strategy"]["matrix"].get("include", [])
        if str(e.get("python-version")) == NEXT_PYTHON_DEV
    ]
    assert len(previews) == 1, f"test-matrix must include exactly one {NEXT_PYTHON_DEV} entry"
    assert previews[0].get("experimental") is True, f"{NEXT_PYTHON_DEV} must be experimental"
    assert "3.16" not in _classifier_versions(), "Python 3.16 must not be advertised yet"

    steps = {step.get("name"): step for step in job["steps"]}
    setup = steps["Set up Python"]
    assert setup.get("continue-on-error") == NON_GATING_EXPR
    assert setup["with"].get("allow-prereleases") == NON_GATING_EXPR, (
        "Pre-release interpreters must only be allowed for experimental entries"
    )
    uploads = [s for name, s in steps.items() if name and "Codecov" in name]
    assert uploads, "test-matrix must upload coverage to Codecov"
    for upload in uploads:
        assert "!matrix.experimental" in str(upload.get("if", "")), (
            f"Step {upload.get('name')!r} must skip Codecov uploads for experimental entries"
        )


def test_test_matrix_never_falls_back_to_system_python() -> None:
    """Validate matrix jobs test the interpreter setup-python installed, never the runner's default.

    When an experimental interpreter (e.g. ``3.16-dev``) has no runner build yet, setup-python fails
    under ``continue-on-error``; without these guards uv silently tests the system Python instead.
    """
    steps = {step.get("name"): step for step in _test_matrix_job()["steps"]}
    assert steps["Set up Python"].get("id") == "setup-python"

    install = steps["Install Dependencies"]
    assert (
        install.get("env", {}).get("UV_PYTHON") == "${{ steps.setup-python.outputs.python-path }}"
    )

    succeeded = "${{ steps.setup-python.outcome == 'success' }}"
    for name in (
        "Install Dependencies",
        "Populate Global Gitignore to Verify Hermeticity",
        "Run Pytest with 100% Coverage Enforcement",
    ):
        assert steps[name].get("if") == succeeded, f"Step {name!r} must require a successful setup"

    reporters = [
        s for s in steps.values() if s.get("if") == "${{ steps.setup-python.outcome != 'success' }}"
    ]
    assert len(reporters) == 1, "test-matrix must report when the requested Python is unavailable"
    assert "::warning" in reporters[0]["run"]


MAXIMUM_PYTHON = "3.15"
# Jobs that run on a single interpreter: they track the supported maximum. The dependency smoke
# matrix is excluded on purpose; it verifies dependency floors and is owned by #325.
SINGLE_VERSION_JOBS = {
    "ci.yml": ("quality-gate", "packaging-smoke-test"),
    "docs.yml": ("build",),
    "release.yml": ("verify-release", "build-distributions"),
}


def test_python_classifier_maximum_is_3_15() -> None:
    """Validate the highest advertised Python classifier is 3.15 and 3.16 is not advertised."""
    versions = _classifier_versions()
    assert max(versions, key=_minor_version) == MAXIMUM_PYTHON
    assert "3.16" not in versions


def test_pyproject_fmt_max_supported_python_matches_classifiers() -> None:
    """Validate pyproject-fmt's --max-supported-python equals the highest classifier."""
    config = yaml.safe_load((_repo_root() / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hooks = [h for repo in config["repos"] for h in repo["hooks"] if h["id"] == "pyproject-fmt"]
    assert len(hooks) == 1, "expected exactly one pyproject-fmt hook"
    args = hooks[0]["args"]
    max_supported = args[args.index("--max-supported-python") + 1]
    assert max_supported == max(_classifier_versions(), key=_minor_version)


def test_single_version_jobs_use_max_supported_python() -> None:
    """Validate single-interpreter CI jobs run on the highest supported Python."""
    for workflow, job_ids in SINGLE_VERSION_JOBS.items():
        with (_repo_root() / ".github" / "workflows" / workflow).open(encoding="utf-8") as f:
            jobs = yaml.safe_load(f)["jobs"]

        for job_id in job_ids:
            versions = [
                str(step["with"]["python-version"])
                for step in jobs[job_id]["steps"]
                if "actions/setup-python" in str(step.get("uses", ""))
            ]
            assert versions == [MAXIMUM_PYTHON], f"{workflow}:{job_id} runs Python {versions}"


def test_dockerfile_stages_share_python_and_debian_release() -> None:
    """Validate both Dockerfile stages are digest-pinned to one supported Python and Debian release.

    The builder installs into /usr/local and the runtime copies it verbatim, so the interpreter and
    the Debian release (glibc) must match across stages.
    """
    text = (_repo_root() / "Dockerfile").read_text(encoding="utf-8")
    builder = re.search(
        r"^FROM ghcr\.io/astral-sh/uv:python(3\.\d+)-(\w+)-slim@sha256:[0-9a-f]{64} AS builder$",
        text,
        re.MULTILINE,
    )
    runtime = re.search(
        r"^FROM python:(3\.\d+)-slim-(\w+)@sha256:[0-9a-f]{64} AS runtime$",
        text,
        re.MULTILINE,
    )
    assert builder, "builder stage must be a digest-pinned ghcr.io/astral-sh/uv:pythonX.Y image"
    assert runtime, "runtime stage must be a digest-pinned python:X.Y-slim image"
    assert builder.groups() == runtime.groups(), (
        f"builder {builder.groups()} and runtime {runtime.groups()} must match"
    )
    assert builder.group(1) in _classifier_versions(), "container Python must be supported"
