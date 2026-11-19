"""Unit tests for celebrate-first-merged-pr logic in .github/workflows/welcome.yml (#635)."""

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

RunOutcome = tuple[subprocess.CompletedProcess[str], list[dict[str, Any]]]


@dataclass(frozen=True)
class FakeMergeSetup:
    """Synthetic GitHub GraphQL and REST state for testing celebrate-first-merged-pr."""

    gql_pages: list[Any]
    comment_pages: list[list[dict[str, Any]]]
    pr_author: str = "alice-dev"
    pr_number: str = "635"
    pr_merged_at: str = "2026-11-18T12:00:00Z"
    fail_rc: int = 0
    post_stdout: str = ""


@dataclass(frozen=True)
class CelebrateSuiteResult:
    """Executed scenario outcomes and child-process coverage paths for celebrate-first-merged-pr."""

    runs: dict[str, RunOutcome]
    cov_data: Path
    workflow_py: Path


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
    case_dir: Path,
    setup: FakeMergeSetup,
    *,
    workflow_py: Path,
    cov_data: Path,
) -> RunOutcome:
    """Execute celebrate-first-merged-pr cross-platform under branch coverage."""
    case_dir.mkdir(parents=True, exist_ok=True)
    state_file = case_dir / "gh_state.json"
    log_file = case_dir / "gh_mutations.jsonl"
    harness_py = case_dir / "harness.py"

    state_file.write_text(
        json.dumps(
            {
                "gql_pages": setup.gql_pages,
                "gql_idx": 0,
                "comments": setup.comment_pages,
                "fail_rc": setup.fail_rc,
                "post_stdout": setup.post_stdout,
            },
        ),
        encoding="utf-8",
    )
    harness_py.write_text(
        f"""import coverage, json, pathlib, runpy, subprocess

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
        return subprocess.CompletedProcess(cmd, 0, stdout=state["post_stdout"], stderr="")
    return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(state["comments"]), stderr="")


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
        "REPO": "bdperkin/findfmt",
        "PR_NUMBER": setup.pr_number,
        "PR_AUTHOR": setup.pr_author,
        "PR_MERGED_AT": setup.pr_merged_at,
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


def _scenario_definitions() -> dict[str, FakeMergeSetup]:
    """Build synthetic scenario matrix exercising every celebrate-first-merged-pr branch."""
    return {
        "delayed_first_pr": FakeMergeSetup(
            pr_number="635",
            pr_merged_at="2026-11-18T12:00:00Z",
            post_stdout="",
            gql_pages=[
                {
                    "pageInfo": {"hasNextPage": True, "endCursor": "cur1"},
                    "nodes": [
                        None,
                        {"number": 640, "mergedAt": "2026-11-18T12:05:00Z", "author": {"login": "alice-dev"}},
                        {"number": 650, "mergedAt": None, "author": {"login": "alice-dev"}},
                        {"number": 635, "mergedAt": "2026-11-18T12:00:00Z", "author": {"login": "alice-dev"}},
                        {"number": 633, "mergedAt": "2026-11-18T11:00:00Z", "author": None},
                    ],
                },
                {
                    "pageInfo": {"hasNextPage": True, "endCursor": ""},
                    "nodes": [
                        {"number": 630, "mergedAt": "2026-11-18T10:00:00Z", "author": {"login": "bob-dev"}},
                    ],
                },
            ],
            comment_pages=[
                [{"id": 1, "user": {"login": "evil"}, "body": "<!-- findfmt-first-merge-welcome -->"}],
            ],
        ),
        "second_pr": FakeMergeSetup(
            pr_number="640",
            pr_merged_at="2026-11-18T12:05:00Z",
            gql_pages=[
                {
                    "pageInfo": {"hasNextPage": True, "endCursor": "cur1"},
                    "nodes": [
                        {"number": 640, "mergedAt": "2026-11-18T12:05:00Z", "author": {"login": "alice-dev"}},
                    ],
                },
                {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"number": 635, "mergedAt": "2026-11-18T12:00:00Z", "author": {"login": "Alice-Dev"}},
                    ],
                },
            ],
            comment_pages=[[]],
        ),
        "missing_merged_at_and_non_dict": FakeMergeSetup(
            pr_number="635",
            pr_merged_at="2026-11-18T12:00:00Z",
            gql_pages=[
                {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        "non-dict-history-node",
                        {"number": 630, "mergedAt": None, "author": {"login": "alice-dev"}},
                    ],
                },
            ],
            comment_pages=[[]],
        ),
        "dup": FakeMergeSetup(
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
        "bad": FakeMergeSetup(gql_pages=[], comment_pages=[], pr_author="bad login!"),
        "err": FakeMergeSetup(gql_pages=[], comment_pages=[], fail_rc=5),
    }


@pytest.fixture(scope="module")
def celebrate_suite(tmp_path_factory: pytest.TempPathFactory) -> CelebrateSuiteResult:
    """Execute all celebrate-first-merged-pr scenarios once and record child branch coverage."""
    suite_dir = tmp_path_factory.mktemp("celebrate_suite").resolve()
    workflow_py = suite_dir / "celebrate_script.py"
    cov_data = suite_dir / ".coverage"
    workflow_py.write_text(_extract_celebrate_python_script(), encoding="utf-8")

    runs = {
        name: _run_celebrate_script(
            suite_dir / name,
            setup,
            workflow_py=workflow_py,
            cov_data=cov_data,
        )
        for name, setup in _scenario_definitions().items()
    }
    return CelebrateSuiteResult(runs=runs, cov_data=cov_data, workflow_py=workflow_py)


def test_celebrate_first_merged_pr_and_delayed_later_merge(celebrate_suite: CelebrateSuiteResult) -> None:
    """Verify first merge posts despite later merges, null nodes, or missing mergedAt (#635)."""
    proc, mutations = celebrate_suite.runs["delayed_first_pr"]
    assert proc.returncode == 0
    assert len(mutations) == 1
    assert mutations[0]["method"] == "POST"
    assert mutations[0]["endpoint"] == "repos/bdperkin/findfmt/issues/635/comments"
    assert "Congratulations @alice-dev" in mutations[0]["body"]["body"]


def test_celebrate_skips_earlier_merges_existing_comments_and_errors(
    celebrate_suite: CelebrateSuiteResult,
) -> None:
    """Verify earlier merges, missing-mergedAt fallback, non-dict nodes, duplicates, and errors (#635)."""
    proc_second, mut_second = celebrate_suite.runs["second_pr"]
    assert proc_second.returncode == 0
    assert mut_second == []

    proc_fallback, mut_fallback = celebrate_suite.runs["missing_merged_at_and_non_dict"]
    assert proc_fallback.returncode == 0
    assert mut_fallback == []

    proc_dup, mut_dup = celebrate_suite.runs["dup"]
    assert proc_dup.returncode == 0
    assert mut_dup == []

    proc_bad, mut_bad = celebrate_suite.runs["bad"]
    assert proc_bad.returncode == 1
    assert "Invalid PR_AUTHOR" in proc_bad.stderr
    assert mut_bad == []

    proc_err, mut_err = celebrate_suite.runs["err"]
    assert proc_err.returncode == 5
    assert "gh: HTTP 503" in proc_err.stderr
    assert mut_err == []


def test_celebrate_embedded_script_100_percent_branch_coverage(
    celebrate_suite: CelebrateSuiteResult,
) -> None:
    """Enforce 100% statement and branch coverage on the embedded celebrate-first-merged-pr script (#635)."""
    cov = coverage.Coverage(
        data_file=str(celebrate_suite.cov_data),
        branch=True,
        config_file=False,
        include=[str(celebrate_suite.workflow_py)],
    )
    cov.combine()
    report_buf = io.StringIO()
    total = cov.report(file=report_buf, show_missing=True)
    assert total == 100.0, report_buf.getvalue()
