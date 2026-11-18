"""Unit tests for Release Drafter, PR title lint, and Conventional Commit automation (#632)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_yaml(rel_path: str) -> dict[str, Any]:
    """Load and parse a YAML mapping relative to repository root."""
    path = _repo_root() / rel_path
    assert path.is_file(), f"Missing YAML file at {path}"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), f"{rel_path} must parse to a YAML mapping"
    return data


def _defined_label_names() -> set[str]:
    """Return the set of label names declared in .github/labels.yml."""
    labels_path = _repo_root() / ".github" / "labels.yml"
    with labels_path.open(encoding="utf-8") as f:
        labels_data = yaml.safe_load(f)

    assert isinstance(labels_data, list)
    return {str(item.get("name")) for item in labels_data if isinstance(item, dict) and item.get("name")}


def test_release_drafter_template_and_categories() -> None:
    """Validate .github/release-drafter.yml categories, version-resolver, and labels (#632)."""
    cfg = _load_yaml(".github/release-drafter.yml")
    assert cfg.get("name-template") == "v$RESOLVED_VERSION"
    assert cfg.get("tag-template") == "v$RESOLVED_VERSION"
    assert "$TITLE" in str(cfg.get("change-template", ""))
    assert "$NUMBER" in str(cfg.get("change-template", ""))
    assert "$CHANGES" in str(cfg.get("template", ""))
    assert "$PREVIOUS_TAG...v$RESOLVED_VERSION" in str(cfg.get("template", ""))

    defined_labels = _defined_label_names()

    resolver = cfg.get("version-resolver")
    assert isinstance(resolver, dict)
    assert resolver.get("default") == "patch"
    assert resolver.get("major", {}).get("labels") == ["breaking change"]
    assert resolver.get("minor", {}).get("labels") == ["enhancement"]
    patch_labels = set(resolver.get("patch", {}).get("labels", []))
    assert {"bug", "documentation", "ci/cd", "dependencies", "type:chore"} <= patch_labels
    assert patch_labels <= defined_labels

    exclude_labels = set(cfg.get("exclude-labels", []))
    assert "release" in exclude_labels
    assert exclude_labels <= defined_labels

    categories = cfg.get("categories")
    assert isinstance(categories, list)
    by_title = {str(c.get("title")): set(c.get("labels", [])) for c in categories if isinstance(c, dict)}
    assert "Breaking Changes" in by_title
    assert "Features" in by_title
    assert "Bug Fixes" in by_title
    assert "CI/CD & Maintenance" in by_title
    assert "Dependencies" in by_title
    assert by_title["Features"] == {"enhancement"}
    assert by_title["Bug Fixes"] == {"bug"}
    assert "type:chore" in by_title["CI/CD & Maintenance"]
    assert "dependencies" in by_title["Dependencies"]

    for title, cat_labels in by_title.items():
        assert cat_labels <= defined_labels, f"Category {title!r} references undefined labels"


def test_release_drafter_workflow_security_and_triggers() -> None:
    """Validate .github/workflows/release-drafter.yml triggers, SHA pinning, and permissions (#632)."""
    wf = _load_yaml(".github/workflows/release-drafter.yml")
    triggers = wf.get("on", wf.get(True))
    assert isinstance(triggers, dict)
    assert triggers.get("push") == {"branches": ["main"]}
    assert "workflow_dispatch" in triggers
    assert "pull_request_target" not in triggers

    assert wf.get("permissions") == {}
    job = wf["jobs"]["update-release-draft"]
    assert job.get("timeout-minutes") == 5
    assert job.get("permissions") == {"contents": "write", "pull-requests": "read"}

    steps = job.get("steps", [])
    assert len(steps) == 1
    step = steps[0]
    uses = str(step.get("uses", ""))
    assert re.fullmatch(r"release-drafter/release-drafter@[0-9a-f]{40}", uses)
    assert step.get("with", {}).get("config-name") == "release-drafter.yml"


@pytest.mark.parametrize(
    ("pr_title", "expected_rc"),
    [
        ("feat(cli): add new output flag (#632)", 0),
        ("feat(api)!: make TraversalConfig keyword-only", 0),
        ("fix(traversal): handle nested gitignore rules", 0),
        ("chore(deps): update dependency typer to v0.29.0", 0),
        ("chore(release): prepare v1.3.3", 0),
        ("ci(mergify): configure automated PR queue (#630)", 0),
        ("sec(audit): harden terminal control-sequence sanitizer", 0),
        ("Update README.md", 1),
        ("feat:missing space after colon", 1),
        ("unknown(cli): invalid commit type", 1),
        ("", 1),
    ],
)
def test_pr_title_workflow_script_execution(pr_title: str, expected_rc: int) -> None:
    """Execute the exact Python validation snippet from .github/workflows/pr-title.yml (#632)."""
    wf = _load_yaml(".github/workflows/pr-title.yml")
    triggers = wf.get("on", wf.get(True))
    assert isinstance(triggers, dict)
    pr_trigger = triggers.get("pull_request", {})
    assert pr_trigger.get("branches") == ["main"]
    assert set(pr_trigger.get("types", [])) == {"opened", "edited", "synchronize", "reopened"}
    assert wf.get("permissions") == {}

    step = wf["jobs"]["validate-pr-title"]["steps"][0]
    assert step.get("env") == {"PR_TITLE": "${{ github.event.pull_request.title }}"}
    run_script = str(step.get("run", ""))
    assert "${{" not in run_script, "Untrusted PR title must not be interpolated directly in run:"

    # Extract embedded python script between <<'PY' and PY
    lines = run_script.strip().splitlines()
    assert lines[0].strip().startswith("python3 - <<'PY'")
    assert lines[-1].strip() == "PY"
    py_code = "\n".join(lines[1:-1])

    env = {**os.environ, "PR_TITLE": pr_title}
    proc = subprocess.run(
        [sys.executable, "-c", py_code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == expected_rc


def test_release_workflow_deletes_superseded_drafts() -> None:
    """Validate release.yml removes superseded draft releases before closing milestone (#632)."""
    release_wf = _load_yaml(".github/workflows/release.yml")
    rel_steps = release_wf["jobs"]["create-github-release"]["steps"]
    step_names = [s.get("name") for s in rel_steps]
    assert step_names.index("Create GitHub Release") < step_names.index("Delete Superseded Draft Releases")
    assert step_names.index("Delete Superseded Draft Releases") < step_names.index("Close Release Milestone")
