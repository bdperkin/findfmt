"""Unit tests for stale issue and PR lifecycle automation in .github/workflows/stale.yml (#634)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

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


def test_stale_workflow_security_and_triggers() -> None:
    """Validate .github/workflows/stale.yml triggers, least-privilege permissions, and SHA pinning (#634)."""
    wf = _load_yaml(".github/workflows/stale.yml")
    triggers = wf.get("on", wf.get(True))
    assert isinstance(triggers, dict)
    assert triggers.get("schedule") == [{"cron": "0 0 * * *"}]
    assert "workflow_dispatch" in triggers
    assert wf.get("permissions") == {}
    assert wf.get("concurrency") == {"group": "stale-lifecycle", "cancel-in-progress": False}

    job = wf["jobs"]["stale"]
    assert job.get("runs-on") == "ubuntu-latest"
    assert job.get("timeout-minutes") == 5
    assert job.get("permissions") == {
        "actions": "write",
        "issues": "write",
        "pull-requests": "write",
    }

    steps = job.get("steps", [])
    assert len(steps) == 1
    uses = str(steps[0].get("uses", ""))
    assert re.fullmatch(r"actions/stale@[0-9a-f]{40}", uses)


def test_stale_thresholds_messages_and_label_taxonomy() -> None:
    """Validate 30d/7d thresholds, polite messages, roadmap exemptions, and label taxonomy (#634)."""
    wf = _load_yaml(".github/workflows/stale.yml")
    inputs = wf["jobs"]["stale"]["steps"][0]["with"]
    assert isinstance(inputs, dict)

    assert inputs.get("days-before-stale") == 30
    assert inputs.get("days-before-issue-stale") == 30
    assert inputs.get("days-before-pr-stale") == 30
    assert inputs.get("days-before-close") == 7
    assert inputs.get("days-before-issue-close") == 7
    assert inputs.get("days-before-pr-close") == 7

    assert inputs.get("stale-issue-label") == "status:stale"
    assert inputs.get("stale-pr-label") == "status:stale"
    assert inputs.get("close-issue-reason") == "not_planned"
    assert inputs.get("remove-stale-when-updated") is True
    assert inputs.get("exempt-all-milestones") is True
    assert inputs.get("exempt-all-assignees") is True
    assert inputs.get("exempt-draft-pr") is True

    for msg_key in ("stale-issue-message", "stale-pr-message"):
        msg = str(inputs.get(msg_key, ""))
        assert "30 days" in msg
        assert "7 days" in msg

    for close_key in ("close-issue-message", "close-pr-message"):
        close_msg = str(inputs.get(close_key, ""))
        assert "7 days" in close_msg

    defined_labels = _defined_label_names()
    assert "status:stale" in defined_labels

    exempt_issue_labels = {
        s.strip() for s in str(inputs.get("exempt-issue-labels", "")).split(",") if s.strip()
    }
    exempt_pr_labels = {s.strip() for s in str(inputs.get("exempt-pr-labels", "")).split(",") if s.strip()}
    assert {
        "security",
        "epic",
        "subtask",
        "status:blocked",
        "good first issue",
        "help wanted",
    } <= exempt_issue_labels
    assert {
        "wip",
        "status:blocked",
        "status:in-review",
        "status:ready-to-merge",
        "automerge",
        "security",
    } <= exempt_pr_labels
    assert exempt_issue_labels <= defined_labels, (
        f"Undefined issue exempt labels: {exempt_issue_labels - defined_labels}"
    )
    assert exempt_pr_labels <= defined_labels, (
        f"Undefined PR exempt labels: {exempt_pr_labels - defined_labels}"
    )
