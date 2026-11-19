"""Schema, trigger, and permission tests for .github/workflows/auto-retry.yml (#624, #689)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_auto_retry_workflow() -> dict[str, Any]:
    """Load and parse .github/workflows/auto-retry.yml."""
    wf_path = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "auto-retry.yml"
    assert wf_path.is_file(), f"Missing auto-retry workflow at {wf_path}"
    data = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "Auto-retry workflow must be a YAML mapping"
    return data


def test_auto_retry_workflow_triggers_and_permissions() -> None:
    """Validate workflow_run trigger, minimal permissions, zero checkout, and loop guard (#624, #689)."""
    workflow = load_auto_retry_workflow()
    assert workflow.get("name") == "Auto-Retry Timed Out Workflow"
    assert workflow.get("permissions") == {}

    triggers = workflow.get("on", workflow.get(True, {}))
    assert isinstance(triggers, dict)
    wf_run = triggers.get("workflow_run")
    assert isinstance(wf_run, dict)
    assert wf_run.get("workflows") == ["CI"]
    assert wf_run.get("types") == ["completed"]

    job = workflow["jobs"]["rerun"]
    assert job.get("runs-on") == "ubuntu-latest"
    assert job.get("timeout-minutes") == 5
    assert job.get("permissions") == {"actions": "write", "checks": "read"}

    condition = str(job.get("if", ""))
    assert "github.event.workflow_run.conclusion == 'failure'" in condition
    assert "github.event.workflow_run.conclusion == 'cancelled'" in condition
    assert "github.event.workflow_run.run_attempt < 3" in condition

    steps = job.get("steps", [])
    assert len(steps) == 1
    assert "uses" not in steps[0], "auto-retry.yml must never check out repository code"
    step_env = steps[0].get("env", {})
    assert step_env.get("HEAD_REPO_ID") == "${{ github.event.workflow_run.head_repository.id }}"
