"""Tests for the .github/workflows/auto-retry.yml watcher workflow (#624)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_auto_retry_workflow() -> dict[str, Any]:
    """Load and parse .github/workflows/auto-retry.yml."""
    wf_path = _repo_root() / ".github" / "workflows" / "auto-retry.yml"
    assert wf_path.is_file(), f"Missing auto-retry workflow at {wf_path}"
    data = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "Auto-retry workflow must be a YAML mapping"
    return data


def test_auto_retry_workflow_triggers_and_permissions() -> None:
    """Validate workflow_run trigger for CI completions and minimal permissions (#624)."""
    workflow = _load_auto_retry_workflow()
    assert workflow.get("name") == "Auto-Retry Timed Out Workflow"
    assert workflow.get("permissions") == {}

    triggers = workflow.get("on", workflow.get(True, {}))
    assert isinstance(triggers, dict)
    wf_run = triggers.get("workflow_run")
    assert isinstance(wf_run, dict)
    assert wf_run.get("workflows") == ["CI"]
    assert wf_run.get("types") == ["completed"]


def test_auto_retry_rerun_job_conditions_and_step() -> None:
    """Validate rerun job conditions, loop guard, actions: write, and gh run rerun (#624)."""
    workflow = _load_auto_retry_workflow()
    jobs = workflow.get("jobs", {})
    assert "rerun" in jobs
    job = jobs["rerun"]

    assert job.get("runs-on") == "ubuntu-latest"
    assert job.get("permissions") == {"actions": "write"}

    condition = str(job.get("if", ""))
    assert "github.event.workflow_run.conclusion == 'failure'" in condition
    assert "github.event.workflow_run.conclusion == 'cancelled'" in condition
    assert "github.event.workflow_run.run_attempt < 3" in condition

    steps = job.get("steps", [])
    assert len(steps) == 1
    step = steps[0]
    assert step.get("name") == "Re-run failed jobs"
    assert step.get("env") == {
        "GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
        "RUN_ID": "${{ github.event.workflow_run.id }}",
    }
    assert step.get("run") == 'gh run rerun "$RUN_ID" --failed'
