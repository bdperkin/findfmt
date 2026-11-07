"""Tests for zizmor CI/CD security static analysis configuration (#468)."""

import re
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _step(job: dict[str, Any], uses: str) -> dict[str, Any]:
    """Return the single step in ``job`` that uses the given action."""
    steps = [s for s in job["steps"] if uses in str(s.get("uses", ""))]
    assert len(steps) == 1, f"expected exactly one {uses} step"
    return steps[0]


def test_dependabot_cooldown_configured() -> None:
    """Validate that Dependabot ecosystems configure a default cooldown (#468)."""
    config_path = _repo_root() / ".github" / "dependabot.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for entry in config["updates"]:
        cooldown = entry.get("cooldown")
        assert isinstance(cooldown, dict), (
            f"Ecosystem {entry.get('package-ecosystem')} must configure cooldown"
        )
        assert cooldown.get("default-days", 0) >= 7


def test_pre_commit_includes_zizmor_hook() -> None:
    """Validate that .pre-commit-config.yaml configures a pinned zizmor hook (#468)."""
    pre_commit_path = _repo_root() / ".pre-commit-config.yaml"
    data = yaml.safe_load(pre_commit_path.read_text(encoding="utf-8"))
    repos = data.get("repos", [])
    zizmor_repo = next(
        (r for r in repos if r.get("repo") == "https://github.com/zizmorcore/zizmor-pre-commit"),
        None,
    )
    assert zizmor_repo is not None, (
        "zizmor-pre-commit must be configured in .pre-commit-config.yaml"
    )
    rev = str(zizmor_repo.get("rev", ""))
    assert rev.startswith("v"), "zizmor-pre-commit must have a pinned vX.Y.Z rev"
    assert len(rev) > 1, "zizmor-pre-commit rev must not be empty"
    hook_ids = [h.get("id") for h in zizmor_repo.get("hooks", [])]
    assert "zizmor" in hook_ids


def test_zizmor_workflow_configuration() -> None:
    """Validate dedicated .github/workflows/zizmor.yml security workflow (#468)."""
    wf_path = _repo_root() / ".github" / "workflows" / "zizmor.yml"
    assert wf_path.is_file(), f"Missing zizmor workflow at {wf_path}"
    data = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)

    assert data.get("permissions") == {}, "Top-level permissions must be empty ({})"
    triggers = data.get("on", data.get(True, {}))
    assert "push" in triggers
    assert "pull_request" in triggers
    assert "workflow_dispatch" in triggers
    for event in ("push", "pull_request"):
        assert triggers[event].get("branches") == ["main"]
        paths = triggers[event].get("paths", [])
        assert ".github/**" in paths
        assert ".pre-commit-config.yaml" in paths

    jobs = data.get("jobs", {})
    assert "zizmor" in jobs
    job = jobs["zizmor"]
    assert job.get("runs-on") == "ubuntu-latest"
    assert job.get("permissions") == {
        "security-events": "write",
        "contents": "read",
        "actions": "read",
    }

    checkout = _step(job, "actions/checkout")
    assert checkout.get("with", {}).get("persist-credentials") is False

    zizmor_step = _step(job, "zizmorcore/zizmor-action")
    uses = str(zizmor_step.get("uses", ""))
    assert re.fullmatch(r"zizmorcore/zizmor-action@[0-9a-f]{40}", uses), (
        f"zizmor-action must be pinned to a 40-char commit SHA, got {uses}"
    )


def test_all_workflow_checkouts_disable_persist_credentials() -> None:
    """Validate every actions/checkout step sets persist-credentials: false (#468)."""
    workflows_dir = _repo_root() / ".github" / "workflows"
    workflow_files = sorted(workflows_dir.glob("*.yml"))
    assert workflow_files, "Expected workflow files in .github/workflows"

    checkout_count = 0
    for wf_path in workflow_files:
        data = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
        for job_name, job_data in data.get("jobs", {}).items():
            for step in job_data.get("steps", []):
                if "actions/checkout" in str(step.get("uses", "")):
                    checkout_count += 1
                    assert step.get("with", {}).get("persist-credentials") is False, (
                        f"{wf_path.name}:{job_name} checkout must set persist-credentials: false"
                    )

    assert checkout_count >= 15


def test_zizmor_suppressions_include_justification() -> None:
    """Validate every inline zizmor ignore comment includes a justification reason (#468)."""
    repo = _repo_root()
    targets = [
        repo / ".pre-commit-config.yaml",
        repo / ".github" / "dependabot.yml",
        *sorted((repo / ".github" / "workflows").glob("*.yml")),
    ]
    ignore_pattern = re.compile(r"#\s*zizmor:\s*ignore\[[^\]]+\](.*)$")
    found_ignores = 0
    for path in targets:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = ignore_pattern.search(line)
            if match is not None:
                found_ignores += 1
                suffix = match.group(1).strip()
                assert suffix.startswith("--"), (
                    f"{path.name}:{lineno} zizmor suppression missing '-- <reason>' comment"
                )
                assert len(suffix[2:].strip()) > 0, (
                    f"{path.name}:{lineno} zizmor suppression reason must not be empty"
                )

    assert found_ignores >= 3


def test_contributing_docs_mention_zizmor() -> None:
    """Validate contributor docs describe running zizmor and the suppression policy (#468)."""
    text = (_repo_root() / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "zizmor" in text
    assert "zizmor: ignore[" in text
