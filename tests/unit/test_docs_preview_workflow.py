"""Unit tests for .github/workflows/docs-preview.yml security and sticky PR comments (#633)."""

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
class FakeGhSetup:
    """Synthetic GitHub API state for executing the docs-preview workflow script."""

    file_pages: list[list[dict[str, Any]]]
    comment_pages: list[list[dict[str, Any]]]
    slug: str = "findfmt"
    pr_number: str = "633"
    fail_suffix: str | None = None
    fail_rc: int = 3


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


def _extract_preview_python_script() -> str:
    """Extract the embedded Python script from .github/workflows/docs-preview.yml."""
    wf = _load_yaml(".github/workflows/docs-preview.yml")
    step = wf["jobs"]["comment-preview-links"]["steps"][0]
    run_script = str(step.get("run", ""))
    assert "${{" not in run_script, "Untrusted inputs must not be interpolated directly in run:"
    lines = run_script.strip().splitlines()
    assert lines[0].strip().startswith("python3 - <<'PY'")
    assert lines[-1].strip() == "PY"
    return "\n".join(lines[1:-1])


def _run_preview_script(
    tmp_path: Path,
    setup: FakeGhSetup,
) -> tuple[subprocess.CompletedProcess[str], list[dict[str, Any]]]:
    """Execute the docs-preview script cross-platform with an intercepted gh subprocess runner."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    state_file = tmp_path / "gh_state.json"
    log_file = tmp_path / "gh_mutations.jsonl"
    workflow_py = tmp_path / "workflow_script.py"
    harness_py = tmp_path / "harness.py"

    state_file.write_text(
        json.dumps(
            {
                "files": setup.file_pages,
                "comments": setup.comment_pages,
                "fail_suffix": setup.fail_suffix,
                "fail_rc": setup.fail_rc,
            },
        ),
        encoding="utf-8",
    )
    workflow_py.write_text(_extract_preview_python_script(), encoding="utf-8")
    harness_py.write_text(
        f"""import json, pathlib, runpy, subprocess

state = json.loads(pathlib.Path({str(state_file)!r}).read_text(encoding="utf-8"))
log_path = pathlib.Path({str(log_file)!r})


def _fake_run(cmd, *, input=None, capture_output=False, text=False, check=False):
    assert cmd[:2] == ["gh", "api"], f"Unexpected command: {{cmd}}"
    assert capture_output is True and text is True and check is False
    rest = cmd[2:]
    endpoint = [a for a in rest if "/" in a][0]
    if state["fail_suffix"] and endpoint.endswith(state["fail_suffix"]):
        return subprocess.CompletedProcess(
            cmd, state["fail_rc"], stdout="", stderr="gh: HTTP 502 Bad Gateway"
        )
    if "-X" in rest:
        idx = rest.index("-X")
        method = rest[idx + 1]
        target = [a for a in rest[idx + 2 :] if a not in ("--input", "-")][0]
        body = json.loads(input) if "--input" in rest and input is not None else None
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({{"method": method, "endpoint": target, "body": body}}) + "\\n")
        return subprocess.CompletedProcess(cmd, 0, stdout="{{}}", stderr="")
    if endpoint.endswith("/files"):
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(state["files"]), stderr="")
    if endpoint.endswith("/comments"):
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(state["comments"]), stderr="")
    return subprocess.CompletedProcess(cmd, 2, stdout="", stderr="unknown endpoint")


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
        "RTD_SLUG": setup.slug,
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


def test_docs_preview_workflow_security_and_structure() -> None:
    """Validate .github/workflows/docs-preview.yml fork safety, permissions, and triggers (#633)."""
    wf = _load_yaml(".github/workflows/docs-preview.yml")
    triggers = wf.get("on", wf.get(True))
    assert isinstance(triggers, dict)
    assert "pull_request" not in triggers
    assert triggers.get("pull_request_target") == {
        "branches": ["main"],
        "types": ["opened", "synchronize", "reopened"],
    }
    assert wf.get("permissions") == {}

    job = wf["jobs"]["comment-preview-links"]
    assert "if" not in job
    assert job.get("timeout-minutes") == 5
    assert job.get("permissions") == {"contents": "read", "pull-requests": "write"}
    for step in job.get("steps", []):
        assert "uses" not in step, "docs-preview.yml must not check out or execute untrusted PR code"


def test_docs_preview_posts_page_links_and_handles_pagination(tmp_path: Path) -> None:
    """Verify POST with page links, URL percent-encoding, included docs, and removed files (#633)."""
    proc, mutations = _run_preview_script(
        tmp_path,
        FakeGhSetup(
            file_pages=[
                [
                    {"filename": "docs/source/guides/quickstart.md", "status": "modified"},
                    {"filename": "docs/source/guides/a#b.md", "status": "added"},
                    {"filename": "docs/source/old_removed.md", "status": "removed"},
                    {"filename": "docs/source/locale/es/LC_MESSAGES/index.po", "status": "modified"},
                ],
                [
                    {"filename": "docs/performance.md", "status": "modified"},
                    {"filename": "src/findfmt/cli/main.py", "status": "modified"},
                ],
            ],
            comment_pages=[[]],
        ),
    )
    assert proc.returncode == 0
    assert len(mutations) == 1
    assert mutations[0]["method"] == "POST"
    assert mutations[0]["endpoint"] == "repos/bdperkin/findfmt/issues/633/comments"
    body = mutations[0]["body"]["body"]
    assert "https://findfmt--633.org.readthedocs.build/en/633/" in body
    assert "`docs/source/guides/quickstart.md`" in body
    assert "guides/quickstart.html)" in body
    expected_encoded_row = (
        "| `docs/source/guides/a#b.md` | "
        "[`guides/a#b.html`](https://findfmt--633.org.readthedocs.build/en/633/guides/a%23b.html) |"
    )
    assert expected_encoded_row in body
    assert "`docs/performance.md`" in body
    assert "quality/performance.html)" in body
    assert "old_removed" not in body
    assert "locale/es" not in body


def test_docs_preview_config_only_and_idempotent_noop(tmp_path: Path) -> None:
    """Verify config-only preview message and no-op when bot sticky comment is already current (#633)."""
    proc1, mutations1 = _run_preview_script(
        tmp_path,
        FakeGhSetup(
            file_pages=[[{"filename": ".readthedocs.yaml", "status": "added"}]],
            comment_pages=[[]],
        ),
    )
    assert proc1.returncode == 0
    assert len(mutations1) == 1
    posted_body = mutations1[0]["body"]["body"]
    assert "Documentation build configuration or shared assets changed" in posted_body

    proc2, mutations2 = _run_preview_script(
        tmp_path / "run2",
        FakeGhSetup(
            file_pages=[[{"filename": ".readthedocs.yaml", "status": "added"}]],
            comment_pages=[[{"id": 99, "user": {"login": "github-actions[bot]"}, "body": posted_body}]],
        ),
    )
    assert proc2.returncode == 0
    assert mutations2 == []


def test_docs_preview_updates_bot_comment_and_deletes_when_reverted(tmp_path: Path) -> None:
    """Verify PATCH ignores spoofed human comments and DELETE cleans up reverted doc PRs (#633)."""
    proc_patch, mut_patch = _run_preview_script(
        tmp_path / "patch",
        FakeGhSetup(
            file_pages=[[{"filename": "docs/source/index.md", "status": "modified"}]],
            comment_pages=[
                [
                    {"id": 11, "user": {"login": "evil-user"}, "body": "<!-- findfmt-docs-preview --> spoof"},
                    {
                        "id": 22,
                        "user": {"login": "github-actions[bot]"},
                        "body": "<!-- findfmt-docs-preview --> old",
                    },
                ],
            ],
            slug="custom-slug",
        ),
    )
    assert proc_patch.returncode == 0
    assert len(mut_patch) == 1
    assert mut_patch[0]["method"] == "PATCH"
    assert mut_patch[0]["endpoint"] == "repos/bdperkin/findfmt/issues/comments/22"
    assert "https://custom-slug--633.org.readthedocs.build/en/633/index.html" in mut_patch[0]["body"]["body"]

    proc_del, mut_del = _run_preview_script(
        tmp_path / "delete",
        FakeGhSetup(
            file_pages=[[{"filename": "README.md", "status": "modified"}]],
            comment_pages=[
                [
                    {
                        "id": 22,
                        "user": {"login": "github-actions[bot]"},
                        "body": "<!-- findfmt-docs-preview --> old",
                    },
                ],
            ],
        ),
    )
    assert proc_del.returncode == 0
    assert mut_del == [
        {
            "method": "DELETE",
            "endpoint": "repos/bdperkin/findfmt/issues/comments/22",
            "body": None,
        },
    ]

    proc_none, mut_none = _run_preview_script(
        tmp_path / "none",
        FakeGhSetup(file_pages=[[{"filename": "README.md", "status": "modified"}]], comment_pages=[[]]),
    )
    assert proc_none.returncode == 0
    assert mut_none == []

    proc_bad, _ = _run_preview_script(
        tmp_path / "bad",
        FakeGhSetup(file_pages=[[]], comment_pages=[[]], slug="BAD SLUG!"),
    )
    assert proc_bad.returncode == 1
    assert "Invalid READTHEDOCS_SLUG" in proc_bad.stderr

    proc_api_err, mut_api_err = _run_preview_script(
        tmp_path / "api_err",
        FakeGhSetup(
            file_pages=[[{"filename": "docs/source/index.md", "status": "modified"}]],
            comment_pages=[[]],
            fail_suffix="/comments",
            fail_rc=4,
        ),
    )
    assert proc_api_err.returncode == 4
    assert "gh: HTTP 502 Bad Gateway" in proc_api_err.stderr
    assert mut_api_err == []
