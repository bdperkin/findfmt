"""Unit tests for contributor onboarding automation in .github/workflows/welcome.yml (#635)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class FakeMergeSetup:
    """Synthetic GitHub GraphQL and REST state for testing celebrate-first-merged-pr."""

    gql_pages: list[dict[str, Any]]
    comment_pages: list[list[dict[str, Any]]]
    pr_author: str = "alice-dev"
    pr_number: str = "635"
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


def _extract_celebrate_python_script() -> str:
    """Extract the embedded Python script from celebrate-first-merged-pr in welcome.yml."""
    wf = _load_yaml(".github/workflows/welcome.yml")
    step = wf["jobs"]["celebrate-first-merged-pr"]["steps"][0]
    run_script = str(step.get("run", ""))
    assert "${{" not in run_script, "Untrusted inputs must not be interpolated directly in run:"
    lines = run_script.strip().splitlines()
    assert lines[0].strip().startswith("python3 - <<'PY'")
    assert lines[-1].strip() == "PY"
    return "\n".join(lines[1:-1])


def _run_celebrate_script(
    tmp_path: Path,
    setup: FakeMergeSetup,
) -> tuple[subprocess.CompletedProcess[str], list[dict[str, Any]]]:
    """Execute celebrate-first-merged-pr cross-platform with an intercepted gh runner."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    state_file = tmp_path / "gh_state.json"
    log_file = tmp_path / "gh_mutations.jsonl"
    workflow_py = tmp_path / "workflow_script.py"
    harness_py = tmp_path / "harness.py"

    state_file.write_text(
        json.dumps(
            {
                "gql_pages": setup.gql_pages,
                "gql_idx": 0,
                "comments": setup.comment_pages,
                "fail_rc": setup.fail_rc,
            },
        ),
        encoding="utf-8",
    )
    workflow_py.write_text(_extract_celebrate_python_script(), encoding="utf-8")
    harness_py.write_text(
        f"""import json, pathlib, runpy, subprocess

state_path = pathlib.Path({str(state_file)!r})
log_path = pathlib.Path({str(log_file)!r})


def _fake_run(cmd, *, input=None, capture_output=False, text=False, check=False):
    assert cmd[:2] == ["gh", "api"], f"Unexpected command: {{cmd}}"
    assert capture_output is True and text is True and check is False
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state["fail_rc"]:
        return subprocess.CompletedProcess(cmd, state["fail_rc"], stdout="", stderr="gh: HTTP 503")
    rest = cmd[2:]
    if rest[0] == "graphql":
        idx = state["gql_idx"]
        page = state["gql_pages"][idx]
        state["gql_idx"] = idx + 1
        state_path.write_text(json.dumps(state), encoding="utf-8")
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps({{"data": {{"repository": {{"pullRequests": page}}}}}}),
            stderr="",
        )
    if "-X" in rest:
        idx = rest.index("-X")
        method = rest[idx + 1]
        target = [a for a in rest if "/" in a][0]
        body = json.loads(input) if input is not None else None
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({{"method": method, "endpoint": target, "body": body}}) + "\\n")
        return subprocess.CompletedProcess(cmd, 0, stdout="{{}}", stderr="")
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
        "PR_NUMBER": setup.pr_number,
        "PR_AUTHOR": setup.pr_author,
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
    """Validate .github/workflows/welcome.yml triggers, SHA pinning, bot guards, and doc links (#635)."""
    wf = _load_yaml(".github/workflows/welcome.yml")
    triggers = wf.get("on", wf.get(True))
    assert isinstance(triggers, dict)
    assert triggers.get("issues") == {"types": ["opened"]}
    assert triggers.get("pull_request_target") == {"types": ["opened", "closed"]}
    assert wf.get("permissions") == {}

    welcome_job = wf["jobs"]["welcome-first-interaction"]
    assert welcome_job.get("timeout-minutes") == 5
    assert welcome_job.get("permissions") == {"issues": "write", "pull-requests": "write"}
    welcome_if = str(welcome_job.get("if", ""))
    assert "github.event.sender.type != 'Bot'" in welcome_if

    steps = welcome_job.get("steps", [])
    assert len(steps) == 1
    uses = str(steps[0].get("uses", ""))
    assert re.fullmatch(r"actions/first-interaction@[0-9a-f]{40}", uses)

    inputs = steps[0].get("with", {})
    assert isinstance(inputs, dict)
    assert inputs.get("repo_token") == "${{ secrets.GITHUB_TOKEN }}"
    issue_msg = str(inputs.get("issue_message", ""))
    pr_msg = str(inputs.get("pr_message", ""))
    assert "CONTRIBUTING.md" in issue_msg
    assert "issues/new/choose" in issue_msg
    assert "SUPPORT.md" in issue_msg
    assert "CODE_OF_CONDUCT.md" in issue_msg
    assert "CONTRIBUTING.md" in pr_msg
    assert "CODE_OF_CONDUCT.md" in pr_msg
    for doc_file in ("CONTRIBUTING.md", "SUPPORT.md", "CODE_OF_CONDUCT.md"):
        assert (_repo_root() / doc_file).is_file()

    celebrate_job = wf["jobs"]["celebrate-first-merged-pr"]
    assert celebrate_job.get("timeout-minutes") == 5
    assert celebrate_job.get("permissions") == {"contents": "read", "pull-requests": "write"}
    celebrate_if = str(celebrate_job.get("if", ""))
    assert "github.event.pull_request.merged == true" in celebrate_if
    assert "github.event.pull_request.user.type != 'Bot'" in celebrate_if
    for step in celebrate_job.get("steps", []):
        assert "uses" not in step, "celebrate-first-merged-pr must not check out untrusted PR code"


def test_celebrate_first_merged_pr_posts_for_first_time_author(tmp_path: Path) -> None:
    """Verify congratulatory comment posts across paginated GraphQL history for a first-time merger (#635)."""
    proc, mutations = _run_celebrate_script(
        tmp_path,
        FakeMergeSetup(
            gql_pages=[
                {
                    "pageInfo": {"hasNextPage": True, "endCursor": "cur1"},
                    "nodes": [
                        {"number": 635, "author": {"login": "alice-dev"}},
                        {"number": 634, "author": {"login": "bdperkin"}},
                        {"number": 633, "author": None},
                    ],
                },
                {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [{"number": 630, "author": {"login": "bob-dev"}}],
                },
            ],
            comment_pages=[
                [{"id": 1, "user": {"login": "evil"}, "body": "<!-- findfmt-first-merge-welcome -->"}],
            ],
        ),
    )
    assert proc.returncode == 0
    assert len(mutations) == 1
    assert mutations[0]["method"] == "POST"
    assert mutations[0]["endpoint"] == "repos/bdperkin/findfmt/issues/635/comments"
    assert "Congratulations @alice-dev" in mutations[0]["body"]["body"]


def test_celebrate_skips_repeat_authors_existing_comments_and_errors(tmp_path: Path) -> None:
    """Verify repeat mergers, duplicate bot comments, invalid logins, and API failures do not post (#635)."""
    proc_repeat, mut_repeat = _run_celebrate_script(
        tmp_path / "repeat",
        FakeMergeSetup(
            gql_pages=[
                {
                    "pageInfo": {"hasNextPage": True, "endCursor": "cur1"},
                    "nodes": [{"number": 635, "author": {"login": "alice-dev"}}],
                },
                {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [{"number": 500, "author": {"login": "Alice-Dev"}}],
                },
            ],
            comment_pages=[[]],
        ),
    )
    assert proc_repeat.returncode == 0
    assert mut_repeat == []

    proc_dup, mut_dup = _run_celebrate_script(
        tmp_path / "dup",
        FakeMergeSetup(
            gql_pages=[{"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": []}],
            comment_pages=[
                [
                    {
                        "id": 9,
                        "user": {"login": "github-actions[bot]"},
                        "body": "<!-- findfmt-first-merge-welcome -->",
                    },
                ],
            ],
        ),
    )
    assert proc_dup.returncode == 0
    assert mut_dup == []

    proc_bad, mut_bad = _run_celebrate_script(
        tmp_path / "bad",
        FakeMergeSetup(gql_pages=[], comment_pages=[], pr_author="bad login!"),
    )
    assert proc_bad.returncode == 1
    assert "Invalid PR_AUTHOR" in proc_bad.stderr
    assert mut_bad == []

    proc_err, mut_err = _run_celebrate_script(
        tmp_path / "err",
        FakeMergeSetup(gql_pages=[], comment_pages=[], fail_rc=5),
    )
    assert proc_err.returncode == 5
    assert "gh: HTTP 503" in proc_err.stderr
    assert mut_err == []
