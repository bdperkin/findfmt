"""Tests for .github/workflows/dependency-matrix.yml (#429, #689)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from tools.dep_matrix import FULL_MATRIX


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


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
    assert set(inputs["resolution"]["options"]) == {
        "matrix-default",
        "highest",
        "lowest",
        "lowest-direct",
    }
    assert set(inputs["prerelease"]["options"]) == {
        "matrix-default",
        "disallow",
        "allow",
        "if-necessary",
        "explicit",
        "if-necessary-or-explicit",
    }
    assert set(inputs["fork_strategy"]["options"]) == {
        "matrix-default",
        "fewest",
        "requires-python",
    }


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
    summary_step = next(s for s in steps if "Record Matrix Cell Result Summary" in s.get("name", ""))
    assert summary_step.get("if") == "always()"
    assert "GITHUB_STEP_SUMMARY" in summary_step.get("run", "")

    diag_step = next(s for s in steps if "Capture Dependency Tree on Failure" in s.get("name", ""))
    assert diag_step.get("if") == "failure()"
    assert "uv pip tree" in diag_step.get("run", "")
    assert "GITHUB_STEP_SUMMARY" in diag_step.get("run", "")
