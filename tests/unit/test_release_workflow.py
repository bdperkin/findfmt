"""Tests for release workflow, version-sensitive checkouts, and tooling alignment."""

from __future__ import annotations

import gettext
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import yaml
from tools.sync_pre_commit_deps import sync_deps

import findfmt.i18n

RELEASE_TAG_EXPR = "${{ inputs.tag || github.ref_name }}"
RELEASE_REF_EXPR = "${{ inputs.tag || github.ref }}"


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_release_workflow() -> dict[str, Any]:
    """Load and parse .github/workflows/release.yml."""
    with (_repo_root() / ".github" / "workflows" / "release.yml").open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "Release workflow must be a YAML mapping"
    return data


def _step(job: dict[str, Any], uses: str) -> dict[str, Any]:
    """Return the single step in ``job`` that uses the given action."""
    steps = [s for s in job["steps"] if uses in str(s.get("uses", ""))]
    assert len(steps) == 1, f"expected exactly one {uses} step"
    return steps[0]


def test_release_checkout_uses_tag_input() -> None:
    """Validate every release checkout builds the requested tag, not the branch (#327)."""
    workflow = _load_release_workflow()
    assert workflow["env"]["RELEASE_TAG"] == RELEASE_TAG_EXPR
    checkouts = {
        name: _step(job, "actions/checkout")
        for name, job in workflow["jobs"].items()
        if any("actions/checkout" in str(s.get("uses", "")) for s in job["steps"])
    }
    assert set(checkouts) == {"verify-release", "build-distributions", "containerize"}
    for name, step in checkouts.items():
        assert step["with"].get("ref") == RELEASE_REF_EXPR, f"{name} must check out the tag"
        assert step["with"].get("fetch-depth") == 0, f"{name} needs full history for hatch-vcs"


def test_release_validates_tag_before_quality_gate() -> None:
    """Validate the release fails fast unless the checkout is the requested vX.Y.Z tag (#546)."""
    steps = _load_release_workflow()["jobs"]["verify-release"]["steps"]
    names = [s.get("name") for s in steps]
    check = steps[names.index("Verify Release Tag")]
    assert check.get("env", {}).get("GH_TOKEN") == "${{ github.token }}"
    assert 'tools/verify_release_version.py --tag "$RELEASE_TAG" --repo .' in check["run"]
    assert "git rev-parse" in check["run"], "the checked-out commit must be the tag's commit"
    # The publishing environments only deploy v*.*.* tags, so a dispatch must run on the tag (#495).
    assert 'test "$GITHUB_REF" = "refs/tags/${RELEASE_TAG}"' in check["run"]
    assert "repos/${GITHUB_REPOSITORY}/milestones?state=all" in check["run"]
    assert 'test -z "$open_issues" || test "$open_issues" -eq 0' in check["run"]
    assert names.index("Verify Release Tag") < names.index("Verify Complete Quality Suite")


def test_release_closes_matching_milestone() -> None:
    """Validate create-github-release idempotently closes the matching release milestone (#546)."""
    job = _load_release_workflow()["jobs"]["create-github-release"]
    assert job["permissions"] == {"contents": "write", "issues": "write"}
    names = [s.get("name") for s in job["steps"]]
    assert names.index("Create GitHub Release") < names.index("Close Release Milestone")
    close_step = job["steps"][names.index("Close Release Milestone")]
    assert close_step.get("env", {}).get("GH_TOKEN") == "${{ github.token }}"
    assert 'if [ "$state" = "closed" ]; then' in close_step["run"]
    assert (
        'gh api -X PATCH "repos/${GITHUB_REPOSITORY}/milestones/${milestone_num}" -f state=closed'
        in close_step["run"]
    )


def test_release_verifies_built_version_before_publishing() -> None:
    """Validate the built wheel and sdist versions are checked against the tag before upload."""
    steps = _load_release_workflow()["jobs"]["build-distributions"]["steps"]
    names = [s.get("name") for s in steps]
    check = steps[names.index("Verify Built Version Matches Release Tag")]
    assert 'tools/verify_release_version.py --tag "$RELEASE_TAG" --dist dist' in check["run"]
    assert names.index("Build Distributions via uv") < names.index(
        "Verify Built Version Matches Release Tag",
    )
    assert names.index("Verify Built Version Matches Release Tag") < names.index(
        "Upload Distribution Artifacts",
    )


def test_release_pypi_step_has_no_skip_existing() -> None:
    """Validate a duplicate production PyPI upload fails loudly instead of being skipped."""
    publish = _step(_load_release_workflow()["jobs"]["publish-pypi"], "pypa/gh-action-pypi-publish")
    assert not publish.get("with", {}).get("skip-existing", False)


def test_release_container_semver_tags_use_release_tag() -> None:
    """Validate container semver tags come from the release tag (not only ``latest``)."""
    meta = _step(_load_release_workflow()["jobs"]["containerize"], "docker/metadata-action")
    semver = [line for line in meta["with"]["tags"].splitlines() if "type=semver" in line]
    assert len(semver) == 2
    for line in semver:
        assert "value=${{ env.RELEASE_TAG }}" in line, line


def test_release_oidc_is_confined_to_tag_publish_jobs() -> None:
    """Validate which release jobs can mint OIDC tokens (#495, #328).

    The two PyPI publish jobs each run in their tag-scoped environment. The container job needs a
    token only to sign its provenance attestation, and never runs a PyPI publish step.
    """
    workflow = _load_release_workflow()
    triggers = workflow.get("on", workflow.get(True))  # PyYAML loads a bare `on:` key as True
    assert triggers["push"] == {"tags": ["v*.*.*"]}
    assert workflow["permissions"] == {"contents": "read"}
    minting = {
        name: job.get("environment", {}).get("name")
        for name, job in workflow["jobs"].items()
        if job.get("permissions", {}).get("id-token") == "write"
    }
    assert minting == {"publish-testpypi": "testpypi", "publish-pypi": "pypi", "containerize": None}
    container_steps = workflow["jobs"]["containerize"]["steps"]
    assert not any("gh-action-pypi-publish" in str(s.get("uses")) for s in container_steps)
    assert "publish-pypi" in workflow["jobs"]["containerize"]["needs"]
    needs = workflow["jobs"]["publish-pypi"]["needs"]
    assert "publish-testpypi" in needs, "TestPyPI must be published before production PyPI"


def test_release_notes_come_from_the_changelog() -> None:
    """Validate the GitHub Release uses the curated CHANGELOG.md section, checked early (#498)."""
    jobs = _load_release_workflow()["jobs"]
    verify = next(
        s for s in jobs["verify-release"]["steps"] if s.get("name") == "Verify Release Tag"
    )
    assert 'tools/release_notes.py --tag "$RELEASE_TAG"' in verify["run"]
    build = jobs["build-distributions"]
    notes = next(s for s in build["steps"] if s.get("id") == "notes")
    assert 'python tools/release_notes.py --tag "$RELEASE_TAG"' in notes["run"]
    assert build["outputs"]["release_body"] == "${{ steps.notes.outputs.content }}"
    assert not any("git-cliff" in str(s.get("uses")) for s in build["steps"])
    release = _step(jobs["create-github-release"], "softprops/action-gh-release")
    assert release["with"]["body"] == "${{ needs.build-distributions.outputs.release_body }}"


def test_version_sensitive_checkouts_fetch_full_history() -> None:
    """Validate that version-sensitive workflows configure fetch-depth: 0 on actions/checkout."""
    workflows_dir = _repo_root() / ".github" / "workflows"
    version_sensitive_jobs = [
        (workflows_dir / "ci.yml", "package-check"),
        (workflows_dir / "ci.yml", "packaging-smoke-test"),
        (workflows_dir / "ci.yml", "container-smoke-test"),
        (workflows_dir / "docs.yml", "build"),
        (workflows_dir / "release.yml", "build-distributions"),
        (workflows_dir / "release.yml", "verify-release"),
    ]
    for wf_path, job_name in version_sensitive_jobs:
        assert wf_path.is_file(), f"Missing workflow file: {wf_path}"
        data = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
        job = data.get("jobs", {}).get(job_name)
        assert job is not None, f"Job {job_name} not found in {wf_path.name}"
        checkout_step = next(
            (s for s in job.get("steps", []) if "actions/checkout" in s.get("uses", "")),
            None,
        )
        assert checkout_step is not None, f"Checkout step missing in {wf_path.name}:{job_name}"
        assert checkout_step.get("with", {}).get("fetch-depth") == 0


def test_test_group_is_sufficient() -> None:
    """Validate that [dependency-groups].test includes all required test packages (#359)."""
    with (_repo_root() / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)

    test_deps = data.get("dependency-groups", {}).get("test", [])
    names = {
        str(d).split(";")[0].split(">=")[0].split("==")[0].strip()
        for d in test_deps
        if isinstance(d, str)
    }
    assert {"docutils", "hatchling", "pytest", "pytest-cov", "pytest-mock"} <= names


def test_session_fixture_does_not_write_to_src(compile_locale_catalogs_for_tests: Path) -> None:
    """Validate session locale fixture compiles .mo catalogs to tmp_path, not src/ (#359)."""
    src_locale_dir = _repo_root() / "src" / "findfmt" / "locale"
    assert not compile_locale_catalogs_for_tests.resolve().is_relative_to(src_locale_dir.resolve())
    assert compile_locale_catalogs_for_tests == findfmt.i18n.DEFAULT_LOCALE_DIR
    assert gettext.bindtextdomain(findfmt.i18n.DEFAULT_DOMAIN) == str(
        compile_locale_catalogs_for_tests,
    )
    assert len(list(compile_locale_catalogs_for_tests.glob("*/LC_MESSAGES/findfmt.mo"))) >= 5
    assert list(src_locale_dir.glob("*/LC_MESSAGES/*.mo")) == []
    if shutil.which("git") is not None:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--ignored", "src/findfmt/locale"],
            cwd=_repo_root(),
            capture_output=True,
            text=True,
            check=False,
        )
        assert ".mo" not in proc.stdout


def test_ruff_versions_aligned() -> None:
    """Validate ruff, ty, and all shared lint tool revs in pre-commit match uv.lock (#360)."""
    repo = _repo_root()
    with (repo / "uv.lock").open("rb") as f:
        lock_data = tomllib.load(f)

    locked = {
        pkg["name"].lower(): pkg["version"]
        for pkg in lock_data.get("package", [])
        if "name" in pkg and "version" in pkg
    }
    pre_commit = yaml.safe_load((repo / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    revs = {str(r.get("repo", "")): str(r.get("rev", "")) for r in pre_commit.get("repos", [])}
    assert revs["https://github.com/astral-sh/ruff-pre-commit"] == f"v{locked['ruff']}"
    assert revs["https://github.com/astral-sh/ty-pre-commit"] == f"v{locked['ty']}"
    assert sync_deps(repo) == 0


def test_ci_uses_locked_sync() -> None:
    """Validate that every uv sync step across all workflow files includes --locked."""
    workflows_dir = _repo_root() / ".github" / "workflows"
    workflow_files = sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))
    assert len(workflow_files) > 0, "No workflow files found"

    sync_steps_found = 0
    for wf_path in workflow_files:
        data = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
        for job_name, job_data in (data.get("jobs", {}) if isinstance(data, dict) else {}).items():
            steps = job_data.get("steps", []) if isinstance(job_data, dict) else []
            for step in (s for s in steps if isinstance(s, dict)):
                for line in str(step.get("run", "")).splitlines():
                    if "uv sync" in line:
                        sync_steps_found += 1
                        assert "--locked" in line, f"{wf_path.name}:{job_name} missing --locked"

    assert sync_steps_found >= 5, f"Expected at least 5 uv sync steps, found {sync_steps_found}"


def test_dependency_matrix_adr_specification() -> None:
    """Validate dependency resolution matrix ADR and CONTRIBUTING docs (#426, #430)."""
    repo = _repo_root()
    adr_path = repo / "docs" / "source" / "quality" / "dependency_matrix.md"
    index_path = repo / "docs" / "source" / "quality" / "index.md"
    contrib_path = repo / "CONTRIBUTING.md"
    assert adr_path.is_file(), f"Missing ADR document at {adr_path}"

    index_text = index_path.read_text(encoding="utf-8")
    assert "dependency_matrix" in index_text

    adr_text = adr_path.read_text(encoding="utf-8")
    contrib_text = contrib_path.read_text(encoding="utf-8")
    for cell_id in ("**M1**", "**M2**", "**M3**", "**M4**", "**M5**", "**M6**"):
        assert cell_id in adr_text, f"Expected pruned cell {cell_id} in {adr_path}"

    for token in ("tools/verify_quality.py", "--smoke", "--full", "--resolution", "uv pip tree"):
        assert token in adr_text
        assert token in contrib_text

    assert "dependency_matrix.md" in contrib_text


def test_pyproject_dependency_minimums() -> None:
    """Validate declared dependency minimums match verified working floors."""
    with (_repo_root() / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)

    dep_dict: dict[str, str] = {}
    for dep in data.get("project", {}).get("dependencies", []):
        name = dep.split(";")[0].strip()
        for op in (">=", "=="):
            if op in name:
                pkg, ver = name.split(op, 1)
                dep_dict[pkg.strip()] = ver.strip()

    assert dep_dict == {
        "identify": "2.6",
        "pathspec": "1.0.1",
        "pyyaml": "6.0.1",
        "rich": "13.8",
        "typer": "0.16",
        "typing-extensions": "4.4",
    }
    build_reqs = data.get("build-system", {}).get("requires", [])
    assert "typing-extensions>=4.4; python_version<'3.12'" in build_reqs
    test_deps = data.get("dependency-groups", {}).get("test", [])
    test_dep_names = {d.split(";")[0].split(">=")[0].split("==")[0].strip() for d in test_deps}
    assert {"docutils", "hatchling"} <= test_dep_names
