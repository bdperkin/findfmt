"""Tests for .github/workflows/auto-retry.yml timeout and fail-fast retry guards (#624, #689)."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import coverage
import pytest
import yaml

RunOutcome = tuple[subprocess.CompletedProcess[str], list[list[str]]]


@dataclass(frozen=True)
class FakeAutoRetrySetup:
    """Synthetic GitHub Actions REST state for testing auto-retry.yml."""

    job_pages: list[Any]
    workflow_runs: list[dict[str, Any]]
    run_id: str = "500"
    workflow_id: str = "10"
    head_branch: str = "feat/demo"
    head_repo_id: str = "111"
    run_event: str = "pull_request"
    fail_rc: int = 0


@dataclass(frozen=True)
class AutoRetrySuiteResult:
    """Executed scenario outcomes and child branch-coverage paths for auto-retry.yml."""

    runs: dict[str, RunOutcome]
    cov_data: Path
    workflow_py: Path


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


def _extract_auto_retry_python_script() -> str:
    """Extract the embedded Python script from .github/workflows/auto-retry.yml."""
    wf = _load_auto_retry_workflow()
    step = wf["jobs"]["rerun"]["steps"][0]
    run_script = str(step.get("run", ""))
    assert "${{" not in run_script, "Untrusted inputs must not be interpolated directly in run:"
    lines = run_script.strip().splitlines()
    assert lines[0].strip().startswith("python3 - <<'PY'")
    assert lines[-1].strip() == "PY"
    return "\n".join(lines[1:-1])


def _run_auto_retry_script(
    case_dir: Path,
    setup: FakeAutoRetrySetup,
    *,
    workflow_py: Path,
    cov_data: Path,
) -> RunOutcome:
    """Execute auto-retry.yml logic cross-platform under branch coverage."""
    case_dir.mkdir(parents=True, exist_ok=True)
    state_file = case_dir / "gh_state.json"
    log_file = case_dir / "gh_reruns.jsonl"
    harness_py = case_dir / "harness.py"

    state_file.write_text(
        json.dumps(
            {
                "job_pages": setup.job_pages,
                "workflow_runs": setup.workflow_runs,
                "fail_rc": setup.fail_rc,
            },
        ),
        encoding="utf-8",
    )
    harness_py.write_text(
        f"""import coverage, json, pathlib, runpy, subprocess

state = json.loads(pathlib.Path({str(state_file)!r}).read_text(encoding="utf-8"))
log_path = pathlib.Path({str(log_file)!r})


def _fake_run(cmd, *, capture_output=False, text=False, check=False):
    assert cmd[0] == "gh", f"Unexpected command: {{cmd}}"
    assert capture_output is True and text is True and check is False
    if state["fail_rc"]:
        return subprocess.CompletedProcess(cmd, state["fail_rc"], stdout="", stderr="gh: HTTP 503")
    if cmd[1:3] == ["run", "rerun"]:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(cmd) + "\\n")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    endpoint = cmd[-1]
    if "/workflows/" in endpoint:
        payload = {{"workflow_runs": state["workflow_runs"]}}
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")
    return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(state["job_pages"]), stderr="")


subprocess.run = _fake_run
cov = coverage.Coverage(
    data_file={str(cov_data)!r},
    data_suffix=True,
    branch=True,
    config_file=False,
    include=[{str(workflow_py)!r}],
)
cov.start()
try:
    runpy.run_path({str(workflow_py)!r}, run_name="__main__")
finally:
    cov.stop()
    cov.save()
""",
        encoding="utf-8",
    )

    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("COV_CORE_")}
    env = {
        **clean_env,
        "GH_TOKEN": "test-token",
        "GH_REPO": "bdperkin/findfmt",
        "RUN_ID": setup.run_id,
        "WORKFLOW_ID": setup.workflow_id,
        "HEAD_BRANCH": setup.head_branch,
        "HEAD_REPO_ID": setup.head_repo_id,
        "RUN_EVENT": setup.run_event,
    }
    proc = subprocess.run(
        [sys.executable, str(harness_py)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    reruns: list[list[str]] = (
        [
            [str(p) for p in json.loads(line)]
            for line in log_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if log_file.is_file()
        else []
    )
    return proc, reruns


def _scenario_definitions() -> dict[str, FakeAutoRetrySetup]:
    """Build synthetic scenarios exercising timeout retries, fail-fast skips, and superseded runs."""
    return {
        "queue_timeout_rerun": FakeAutoRetrySetup(
            workflow_runs=[{"id": 500}, {"id": 499}],
            job_pages=[
                None,
                {
                    "jobs": [
                        None,
                        {"conclusion": "success", "steps": [{"conclusion": "success"}]},
                        {"conclusion": "cancelled", "steps": []},
                    ],
                },
            ],
        ),
        "step_timeout_detached_branch": FakeAutoRetrySetup(
            head_branch="",
            workflow_runs=[],
            job_pages=[
                {
                    "jobs": [
                        {"conclusion": "failure", "steps": [{"conclusion": "cancelled"}]},
                        {"conclusion": "cancelled", "steps": []},
                    ],
                },
            ],
        ),
        "deterministic_failure_with_fail_fast_cancels": FakeAutoRetrySetup(
            workflow_runs=[{"id": 500}],
            job_pages=[
                {
                    "jobs": [
                        {
                            "conclusion": "failure",
                            "steps": [{"conclusion": "success"}, {"conclusion": "failure"}],
                        },
                        {"conclusion": "cancelled", "steps": []},
                    ],
                },
            ],
        ),
        "startup_failure_skip": FakeAutoRetrySetup(
            workflow_runs=[{"id": 500, "head_repository": {"id": 111}}],
            job_pages=[{"jobs": [{"conclusion": "startup_failure", "steps": []}]}],
        ),
        "superseded_run_skip": FakeAutoRetrySetup(
            workflow_runs=[
                {"id": 501, "head_repository": {"id": 111}},
                {"id": 500, "head_repository": {"id": 111}},
            ],
            job_pages=[{"jobs": [{"conclusion": "cancelled", "steps": []}]}],
        ),
        "cross_fork_same_branch_rerun": FakeAutoRetrySetup(
            workflow_runs=[
                {"id": 502, "head_repository": {"id": 999}},
                {"id": 501, "head_repository": None},
                {"id": 500, "head_repository": {"id": 111}},
            ],
            job_pages=[{"jobs": [{"conclusion": "timed_out", "steps": []}]}],
        ),
        "gh_error": FakeAutoRetrySetup(workflow_runs=[], job_pages=[], fail_rc=7),
    }


@pytest.fixture(scope="module")
def auto_retry_suite(tmp_path_factory: pytest.TempPathFactory) -> AutoRetrySuiteResult:
    """Execute all auto-retry.yml scenarios once and record child branch coverage."""
    suite_dir = tmp_path_factory.mktemp("auto_retry_suite").resolve()
    workflow_py = suite_dir / "auto_retry_script.py"
    cov_data = suite_dir / ".coverage"
    workflow_py.write_text(_extract_auto_retry_python_script(), encoding="utf-8")

    runs = {
        name: _run_auto_retry_script(
            suite_dir / name,
            setup,
            workflow_py=workflow_py,
            cov_data=cov_data,
        )
        for name, setup in _scenario_definitions().items()
    }
    return AutoRetrySuiteResult(runs=runs, cov_data=cov_data, workflow_py=workflow_py)


def test_auto_retry_workflow_triggers_and_permissions() -> None:
    """Validate workflow_run trigger, minimal permissions, zero checkout, and loop guard (#624, #689)."""
    workflow = _load_auto_retry_workflow()
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
    assert job.get("permissions") == {"actions": "write"}

    condition = str(job.get("if", ""))
    assert "github.event.workflow_run.conclusion == 'failure'" in condition
    assert "github.event.workflow_run.conclusion == 'cancelled'" in condition
    assert "github.event.workflow_run.run_attempt < 3" in condition

    steps = job.get("steps", [])
    assert len(steps) == 1
    assert "uses" not in steps[0], "auto-retry.yml must never check out repository code"
    step_env = steps[0].get("env", {})
    assert step_env.get("HEAD_REPO_ID") == "${{ github.event.workflow_run.head_repository.id }}"


def test_auto_retry_reruns_timeouts_and_skips_deterministic_or_superseded_runs(
    auto_retry_suite: AutoRetrySuiteResult,
) -> None:
    """Verify timeouts rerun while fail-fast step failures and superseded runs do not (#689)."""
    expected_cmd = ["gh", "run", "rerun", "500", "--failed", "--repo", "bdperkin/findfmt"]

    proc_q, reruns_q = auto_retry_suite.runs["queue_timeout_rerun"]
    assert proc_q.returncode == 0
    assert reruns_q == [expected_cmd]

    proc_step_to, reruns_step_to = auto_retry_suite.runs["step_timeout_detached_branch"]
    assert proc_step_to.returncode == 0
    assert reruns_step_to == [expected_cmd]

    proc_det, reruns_det = auto_retry_suite.runs["deterministic_failure_with_fail_fast_cancels"]
    assert proc_det.returncode == 0
    assert reruns_det == []

    proc_start, reruns_start = auto_retry_suite.runs["startup_failure_skip"]
    assert proc_start.returncode == 0
    assert reruns_start == []

    proc_sup, reruns_sup = auto_retry_suite.runs["superseded_run_skip"]
    assert proc_sup.returncode == 0
    assert reruns_sup == []

    proc_fork, reruns_fork = auto_retry_suite.runs["cross_fork_same_branch_rerun"]
    assert proc_fork.returncode == 0
    assert reruns_fork == [expected_cmd]

    proc_err, reruns_err = auto_retry_suite.runs["gh_error"]
    assert proc_err.returncode == 7
    assert "gh: HTTP 503" in proc_err.stderr
    assert reruns_err == []


def test_auto_retry_embedded_script_100_percent_branch_coverage(
    auto_retry_suite: AutoRetrySuiteResult,
) -> None:
    """Enforce 100% statement and branch coverage on the embedded auto-retry.yml script (#689)."""
    cov = coverage.Coverage(
        data_file=str(auto_retry_suite.cov_data),
        branch=True,
        config_file=False,
        include=[str(auto_retry_suite.workflow_py)],
    )
    cov.combine()
    report_buf = io.StringIO()
    total = cov.report(file=report_buf, show_missing=True)
    assert total == 100.0, report_buf.getvalue()
