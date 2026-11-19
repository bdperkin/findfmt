"""Unit tests for first-issue and first-PR greeting logic in .github/workflows/welcome.yml (#635)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class FakeWelcomeSetup:
    """Synthetic GitHub REST API state for testing welcome-first-interaction."""

    history_pages: list[list[dict[str, Any]]]
    comment_pages: list[list[dict[str, Any]]]
    event_name: str = "pull_request_target"
    item_number: str = "635"
    author: str = "alice-dev"
    fail_rc: int = 0


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


def _extract_welcome_python_script() -> str:
    """Extract the embedded Python script from welcome-first-interaction in welcome.yml."""
    wf = _load_yaml(".github/workflows/welcome.yml")
    step = wf["jobs"]["welcome-first-interaction"]["steps"][0]
    run_script = str(step.get("run", ""))
    assert "${{" not in run_script, "Untrusted inputs must not be interpolated directly in run:"
    lines = run_script.strip().splitlines()
    assert lines[0].strip().startswith("python3 - <<'PY'")
    assert lines[-1].strip() == "PY"
    return "\n".join(lines[1:-1])


def _run_welcome_script(
    tmp_path: Path,
    setup: FakeWelcomeSetup,
) -> tuple[subprocess.CompletedProcess[str], list[dict[str, Any]]]:
    """Execute welcome-first-interaction cross-platform with an intercepted gh runner."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    state_file = tmp_path / "gh_state.json"
    log_file = tmp_path / "gh_mutations.jsonl"
    workflow_py = tmp_path / "workflow_script.py"
    harness_py = tmp_path / "harness.py"

    state_file.write_text(
        json.dumps(
            {
                "history": setup.history_pages,
                "comments": setup.comment_pages,
                "fail_rc": setup.fail_rc,
            },
        ),
        encoding="utf-8",
    )
    workflow_py.write_text(_extract_welcome_python_script(), encoding="utf-8")
    harness_py.write_text(
        f"""import json, pathlib, runpy, subprocess

state = json.loads(pathlib.Path({str(state_file)!r}).read_text(encoding="utf-8"))
log_path = pathlib.Path({str(log_file)!r})


def _fake_run(cmd, *, input=None, capture_output=False, text=False, check=False):
    assert cmd[:2] == ["gh", "api"], f"Unexpected command: {{cmd}}"
    assert capture_output is True and text is True and check is False
    if state["fail_rc"]:
        return subprocess.CompletedProcess(cmd, state["fail_rc"], stdout="", stderr="gh: HTTP 502")
    rest = cmd[2:]
    if "-X" in rest:
        idx = rest.index("-X")
        method = rest[idx + 1]
        target = [a for a in rest if "/" in a][0]
        body = json.loads(input) if input is not None else None
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({{"method": method, "endpoint": target, "body": body}}) + "\\n")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    endpoint = [a for a in rest if "/" in a][0]
    if "creator=" in endpoint:
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(state["history"]), stderr="")
    return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(state["comments"]), stderr="")


subprocess.run = _fake_run
runpy.run_path({str(workflow_py)!r}, run_name="__main__")
""",
        encoding="utf-8",
    )

    env = {
        **os.environ,
        "GH_TOKEN": "test-token",
        "REPO": "bdperkin/findfmt",
        "EVENT_NAME": setup.event_name,
        "ITEM_NUMBER": setup.item_number,
        "AUTHOR": setup.author,
    }
    proc = subprocess.run(
        [sys.executable, str(harness_py)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    mutations = (
        [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        if log_file.is_file()
        else []
    )
    return proc, mutations


def test_welcome_workflow_security_triggers_and_links() -> None:
    """Validate .github/workflows/welcome.yml triggers, bot guards, zero-checkout, and doc links (#635)."""
    wf = _load_yaml(".github/workflows/welcome.yml")
    triggers = wf.get("on", wf.get(True))
    assert isinstance(triggers, dict)
    assert triggers.get("issues") == {"types": ["opened"]}
    assert triggers.get("pull_request_target") == {"types": ["opened", "closed"]}
    assert wf.get("permissions") == {}

    welcome_job = wf["jobs"]["welcome-first-interaction"]
    assert welcome_job.get("timeout-minutes") == 5
    assert welcome_job.get("permissions") == {"issues": "write", "pull-requests": "write"}
    assert "github.event.sender.type != 'Bot'" in str(welcome_job.get("if", ""))
    for step in welcome_job.get("steps", []):
        assert "uses" not in step, "welcome-first-interaction must not check out untrusted PR code"

    celebrate_job = wf["jobs"]["celebrate-first-merged-pr"]
    assert celebrate_job.get("timeout-minutes") == 5
    assert celebrate_job.get("permissions") == {"contents": "read", "pull-requests": "write"}
    celebrate_if = str(celebrate_job.get("if", ""))
    assert "github.event.pull_request.merged == true" in celebrate_if
    assert "github.event.pull_request.user.type != 'Bot'" in celebrate_if
    for step in celebrate_job.get("steps", []):
        assert "uses" not in step, "celebrate-first-merged-pr must not check out untrusted PR code"

    for doc_file in ("CONTRIBUTING.md", "SUPPORT.md", "CODE_OF_CONDUCT.md"):
        assert (_repo_root() / doc_file).is_file()


def test_welcome_greets_first_issue_and_first_pr_independently(tmp_path: Path) -> None:
    """Verify event-specific history checks greet genuine first issues and first PRs (#635)."""
    proc_issue, mut_issue = _run_welcome_script(
        tmp_path / "first_issue",
        FakeWelcomeSetup(
            event_name="issues",
            item_number="700",
            history_pages=[[{"number": 650, "pull_request": {}}, {"number": 700}]],
            comment_pages=[[]],
        ),
    )
    assert proc_issue.returncode == 0
    assert len(mut_issue) == 1
    issue_body = mut_issue[0]["body"]["body"]
    assert "thank you for opening your first issue" in issue_body
    assert "CONTRIBUTING.md" in issue_body
    assert "issues/new/choose" in issue_body
    assert "SUPPORT.md" in issue_body
    assert "CODE_OF_CONDUCT.md" in issue_body

    proc_pr, mut_pr = _run_welcome_script(
        tmp_path / "first_pr",
        FakeWelcomeSetup(
            event_name="pull_request_target",
            item_number="701",
            history_pages=[[{"number": 600}, {"number": 701, "pull_request": {}}]],
            comment_pages=[[]],
        ),
    )
    assert proc_pr.returncode == 0
    assert len(mut_pr) == 1
    pr_body = mut_pr[0]["body"]["body"]
    assert "thank you for opening your first pull request" in pr_body
    assert "Conventional Commits" in pr_body


def test_welcome_skips_repeat_pr_author_without_issues_and_handles_errors(tmp_path: Path) -> None:
    """Verify repeat PR authors with zero issues are skipped and duplicates/errors do not post (#635)."""
    proc_repeat_pr, mut_repeat_pr = _run_welcome_script(
        tmp_path / "repeat_pr_no_issues",
        FakeWelcomeSetup(
            event_name="pull_request_target",
            item_number="702",
            history_pages=[[{"number": 650, "pull_request": {}}, {"number": 702, "pull_request": {}}]],
            comment_pages=[[]],
        ),
    )
    assert proc_repeat_pr.returncode == 0
    assert mut_repeat_pr == []

    proc_repeat_issue, mut_repeat_issue = _run_welcome_script(
        tmp_path / "repeat_issue",
        FakeWelcomeSetup(
            event_name="issues",
            item_number="703",
            history_pages=[[{"number": 600}, {"number": 703}]],
            comment_pages=[[]],
        ),
    )
    assert proc_repeat_issue.returncode == 0
    assert mut_repeat_issue == []

    proc_dup, mut_dup = _run_welcome_script(
        tmp_path / "dup",
        FakeWelcomeSetup(
            event_name="pull_request_target",
            item_number="704",
            history_pages=[[{"number": 704, "pull_request": {}}]],
            comment_pages=[
                [
                    {
                        "id": 5,
                        "user": {"login": "github-actions[bot]"},
                        "body": "<!-- findfmt-first-pr-welcome -->",
                    },
                ],
            ],
        ),
    )
    assert proc_dup.returncode == 0
    assert mut_dup == []

    proc_bad, _ = _run_welcome_script(
        tmp_path / "bad",
        FakeWelcomeSetup(history_pages=[], comment_pages=[], author="invalid author!"),
    )
    assert proc_bad.returncode == 1
    assert "Invalid AUTHOR" in proc_bad.stderr

    proc_err, _ = _run_welcome_script(
        tmp_path / "err",
        FakeWelcomeSetup(history_pages=[], comment_pages=[], fail_rc=6),
    )
    assert proc_err.returncode == 6
    assert "gh: HTTP 502" in proc_err.stderr
