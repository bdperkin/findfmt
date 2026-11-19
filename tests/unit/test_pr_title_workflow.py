"""Tests for .github/workflows/pr-title.yml and Mergify merge-queue draft PR exemption (#692)."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import coverage
import yaml


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_yaml_mapping(rel_path: str) -> dict[str, Any]:
    """Load and validate a YAML mapping file relative to the repository root."""
    path = _repo_root() / rel_path
    assert path.is_file(), f"Missing YAML file at {path}"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"Expected YAML mapping in {path}"
    return data


def _extract_pr_title_python_script() -> str:
    """Extract the embedded Python script from .github/workflows/pr-title.yml."""
    wf = _load_yaml_mapping(".github/workflows/pr-title.yml")
    step = wf["jobs"]["validate-pr-title"]["steps"][0]
    run_script = str(step.get("run", ""))
    assert "${{" not in run_script, "PR_TITLE must be passed via env:, never interpolated in run:"
    lines = run_script.strip().splitlines()
    assert lines[0].strip().startswith("python3 - <<'PY'")
    assert lines[-1].strip() == "PY"
    return "\n".join(lines[1:-1])


def _eval_mergify_guard(
    *,
    user_login: str,
    head_repo_full_name: str,
    repository: str,
    head_ref: str,
) -> bool:
    """Mirror the job-level if: expression on validate-pr-title."""
    wf = _load_yaml_mapping(".github/workflows/pr-title.yml")
    condition = " ".join(str(wf["jobs"]["validate-pr-title"].get("if", "")).split())
    expected = (
        "!(github.event.pull_request.user.login == 'mergify[bot]' && "
        "github.event.pull_request.head.repo.full_name == github.repository && "
        "startsWith(github.head_ref, 'mergify/merge-queue/'))"
    )
    assert condition == expected
    return not (
        user_login == "mergify[bot]"
        and head_repo_full_name == repository
        and head_ref.startswith("mergify/merge-queue/")
    )


def test_pr_title_workflow_triggers_permissions_and_mergify_alignment() -> None:
    """Validate pr-title.yml triggers, zero permissions, Mergify queue skip, and .mergify.yml sync (#692)."""
    wf = _load_yaml_mapping(".github/workflows/pr-title.yml")
    assert wf.get("name") == "PR Title Lint"
    assert wf.get("permissions") == {}

    triggers = wf.get("on", wf.get(True, {}))
    assert isinstance(triggers, dict)
    pr_trigger = triggers.get("pull_request")
    assert isinstance(pr_trigger, dict)
    assert pr_trigger.get("branches") == ["main"]
    assert pr_trigger.get("types") == ["opened", "edited", "synchronize", "reopened"]

    job = wf["jobs"]["validate-pr-title"]
    assert job.get("name") == "Validate Conventional Commit PR Title"
    assert job.get("runs-on") == "ubuntu-latest"
    assert job.get("timeout-minutes") == 5
    steps = job.get("steps", [])
    assert len(steps) == 1
    assert "uses" not in steps[0]

    # Mergify speculative draft PR (#691) is skipped
    assert (
        _eval_mergify_guard(
            user_login="mergify[bot]",
            head_repo_full_name="bdperkin/findfmt",
            repository="bdperkin/findfmt",
            head_ref="mergify/merge-queue/3f5cb22681",
        )
        is False
    )
    # Fork branch spoofing mergify/merge-queue/* still runs validation
    assert (
        _eval_mergify_guard(
            user_login="contributor",
            head_repo_full_name="contributor/findfmt",
            repository="bdperkin/findfmt",
            head_ref="mergify/merge-queue/3f5cb22681",
        )
        is True
    )
    # Renovate, pre-commit.ci, and contributor PRs still run validation
    for login, ref in (
        ("renovate[bot]", "renovate/ruff-0.x"),
        ("pre-commit-ci[bot]", "pre-commit-ci-update-config"),
        ("bdperkin", "fix/692-mergify-queue-pr-title"),
    ):
        assert (
            _eval_mergify_guard(
                user_login=login,
                head_repo_full_name="bdperkin/findfmt",
                repository="bdperkin/findfmt",
                head_ref=ref,
            )
            is True
        )

    # Verify .mergify.yml requires title check before queueing, but not on temporary queue draft PRs
    mergify = _load_yaml_mapping(".mergify.yml")
    queue_rule = mergify["queue_rules"][0]
    check_cond = "check-success = Validate Conventional Commit PR Title"
    assert check_cond in queue_rule["queue_conditions"]
    assert check_cond not in queue_rule["merge_conditions"]


def test_pr_title_embedded_script_validation_and_100_percent_branch_coverage(
    tmp_path: Path,
) -> None:
    """Execute embedded pr-title.yml Python script and enforce 100% branch coverage (#692)."""
    script_py = tmp_path / "pr_title_script.py"
    harness_py = tmp_path / "harness.py"
    cov_data = tmp_path / ".coverage"
    script_py.write_text(_extract_pr_title_python_script(), encoding="utf-8")
    harness_py.write_text(
        f"""import coverage, runpy

cov = coverage.Coverage(
    data_file={str(cov_data)!r},
    data_suffix=True,
    branch=True,
    config_file=False,
    include=[{str(script_py)!r}],
)
cov.start()
try:
    runpy.run_path({str(script_py)!r}, run_name="__main__")
finally:
    cov.stop()
    cov.save()
""",
        encoding="utf-8",
    )

    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("COV_CORE_")}
    cases = [
        ("ci(workflows): skip PR Title Lint on Mergify queue draft PRs (#692)", 0),
        ("chore(deps)!: drop legacy dependency", 0),
        ("revert: revert bad commit", 0),
        ("merge queue: checking #690 on main (21b8842)", 1),
        ("feat:missing space after colon", 1),
    ]
    for title, expected_rc in cases:
        proc = subprocess.run(
            [sys.executable, str(harness_py)],
            env={**clean_env, "PR_TITLE": title},
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == expected_rc, f"Unexpected rc for {title!r}: {proc.stderr}"

    cov = coverage.Coverage(
        data_file=str(cov_data),
        branch=True,
        config_file=False,
        include=[str(script_py)],
    )
    cov.combine()
    report_buf = io.StringIO()
    total = cov.report(file=report_buf, show_missing=True)
    assert total == 100.0, report_buf.getvalue()
