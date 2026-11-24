"""Unit tests for Vale pre-commit hook, .vale.ini scopes, and CI version parity (#727)."""

from __future__ import annotations

import configparser
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file into a dictionary."""
    assert path.is_file(), f"Missing expected configuration file: {path}"
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    assert isinstance(data, dict), f"{path.name} must parse to a YAML mapping"
    return data


def _find_vale_binary() -> str | None:
    """Locate an installed Vale executable on PATH or inside pre-commit's cache."""
    direct = shutil.which("vale")
    if direct is not None:
        return direct

    cache_root = Path(os.environ.get("PRE_COMMIT_HOME", Path.home() / ".cache" / "pre-commit"))
    if not cache_root.is_dir():
        return None

    exe_name = "vale.exe" if os.name == "nt" else "vale"
    for candidate in sorted(cache_root.glob(f"**/bin/{exe_name}")):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

    return None


def test_vale_pre_commit_hooks_and_ci_parity() -> None:
    """Validate vale-cli/vale pre-commit hooks, ci.skip offline exclusions, and vale.yml parity (#727)."""
    root = _repo_root()
    pc_data = _load_yaml(root / ".pre-commit-config.yaml")

    ci_skip = pc_data.get("ci", {}).get("skip", [])
    assert isinstance(ci_skip, list)
    assert "vale" in ci_skip
    assert "vale-commit-msg" in ci_skip

    vale_repo = next(
        (r for r in pc_data.get("repos", []) if r.get("repo") == "https://github.com/vale-cli/vale"),
        None,
    )
    assert vale_repo is not None, "https://github.com/vale-cli/vale must be in .pre-commit-config.yaml"
    rev = str(vale_repo.get("rev", ""))
    assert rev.startswith("v"), f"vale-cli/vale rev must be a release tag starting with 'v', got {rev!r}"

    hooks = vale_repo.get("hooks", [])
    assert isinstance(hooks, list)
    assert len(hooks) == 3

    sync_hook = next((h for h in hooks if h.get("alias") == "vale-sync"), None)
    assert sync_hook is not None
    assert sync_hook.get("id") == "vale"
    assert sync_hook.get("pass_filenames") is False
    assert sync_hook.get("args") == ["sync"]
    assert sync_hook.get("stages") == ["manual"]
    assert f"download/{rev}" in str(sync_hook.get("entry", ""))

    lint_hook = next((h for h in hooks if h.get("id") == "vale" and "alias" not in h), None)
    assert lint_hook is not None
    assert lint_hook.get("args") == ["--output=line", "--minAlertLevel=error"]
    assert "types" not in lint_hook

    msg_hook = next((h for h in hooks if h.get("id") == "vale-commit-msg"), None)
    assert msg_hook is not None
    assert msg_hook.get("stages") == ["commit-msg"]
    msg_entry = str(msg_hook.get("entry", ""))
    assert "sed" in msg_entry
    assert "--minAlertLevel=error" in msg_entry
    assert "--path=COMMIT_EDITMSG" in msg_entry

    pc_hooks_repo = next(
        (
            r
            for r in pc_data.get("repos", [])
            if r.get("repo") == "https://github.com/pre-commit/pre-commit-hooks"
        ),
        None,
    )
    assert pc_hooks_repo is not None
    sorter_hook = next(
        (h for h in pc_hooks_repo.get("hooks", []) if h.get("id") == "file-contents-sorter"),
        None,
    )
    assert sorter_hook is not None
    assert sorter_hook.get("files") == r"^\.github/styles/config/vocabularies/findfmt/(accept|reject)\.txt$"

    wf_data = _load_yaml(root / ".github" / "workflows" / "vale.yml")
    vale_steps = wf_data["jobs"]["vale"]["steps"]
    action_step = next(s for s in vale_steps if "vale-cli/vale-action" in str(s.get("uses", "")))
    assert str(action_step["with"]["version"]) == rev.lstrip("v")

    contributing_text = (root / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "uv run pre-commit run vale-sync --hook-stage manual --all-files" in contributing_text


def test_vale_ini_sections_and_gitignore_entries() -> None:
    """Validate .vale.ini formats, Markdown, code-comment, and commit-msg sections (#727)."""
    root = _repo_root()
    vale_ini_text = (root / ".vale.ini").read_text(encoding="utf-8")
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string("[__root__]\n" + vale_ini_text)

    assert parser.has_section("formats")
    assert parser.get("formats", "py") == "md"
    assert parser.get("formats", "rs") == "md"
    assert parser.get("formats", "commit_editmsg") == "md"

    assert "[[!.]*.md]" in vale_ini_text
    assert parser.has_section("*.{py,rs}")
    assert parser.has_section("COMMIT_EDITMSG")
    assert parser.get("*.{py,rs}", "basedonstyles") == "Vale, Google, proselint"
    assert parser.get("COMMIT_EDITMSG", "basedonstyles") == "Vale, Google, proselint"

    gitignore_lines = {
        line.strip()
        for line in (root / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    assert ".github/styles/Google/" in gitignore_lines
    assert ".github/styles/proselint/" in gitignore_lines
    assert ".github/styles/config/grammars/" in gitignore_lines


def test_vale_behavioral_comments_and_commit_metadata(tmp_path: Path) -> None:
    """Verify commit metadata filtering and live Vale markup/prose behavior when synced (#727)."""
    root = _repo_root()
    commit_file = tmp_path / "COMMIT_EDITMSG"
    commit_file.write_text(
        "ci(pre-commit): integrate `my_nonexistent_ident_xyz` hook (#727)\n\n"
        "# git interactive comment with zxqwvut token\n"
        "Signed-off-by: Jane Kaczmarek <jk@example.com>\n",
        encoding="utf-8",
    )

    sed_bin = shutil.which("sed")
    if sed_bin is not None:
        filtered = subprocess.run(
            [sed_bin, "-e", "/^#/d", "-e", "/^[A-Za-z-]*-by: /d", str(commit_file)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert "Kaczmarek" not in filtered
        assert "zxqwvut" not in filtered
        assert "ci(pre-commit): integrate `my_nonexistent_ident_xyz` hook (#727)" in filtered

    vale_bin = _find_vale_binary()
    styles_synced = (root / ".github" / "styles" / "Google").is_dir() and (
        root / ".github" / "styles" / "proselint"
    ).is_dir()
    if vale_bin is None or not styles_synced or sed_bin is None:
        return

    cfg_flag = f"--config={root / '.vale.ini'}"
    filtered_msg = subprocess.run(
        [sed_bin, "-e", "/^#/d", "-e", "/^[A-Za-z-]*-by: /d", str(commit_file)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    ok_msg_res = subprocess.run(
        [vale_bin, cfg_flag, "--output=line", "--minAlertLevel=error", "--path=COMMIT_EDITMSG"],
        input=filtered_msg,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ok_msg_res.returncode == 0, ok_msg_res.stdout + ok_msg_res.stderr

    bad_msg_res = subprocess.run(
        [vale_bin, cfg_flag, "--output=line", "--minAlertLevel=error", "--path=COMMIT_EDITMSG"],
        input="ci(pre-commit): integrate zxqwvut prose hook\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert bad_msg_res.returncode != 0

    py_escaped = tmp_path / "escaped_literal.py"
    py_escaped.write_text("# Match `the the` in code.\nx = 1\n", encoding="utf-8")
    escaped_res = subprocess.run(
        [vale_bin, cfg_flag, "--output=line", "--minAlertLevel=error", str(py_escaped)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert escaped_res.returncode == 0, escaped_res.stdout + escaped_res.stderr

    py_error = tmp_path / "ordinary_error.py"
    py_error.write_text("# Match the the in ordinary prose.\nx = 1\n", encoding="utf-8")
    error_res = subprocess.run(
        [vale_bin, cfg_flag, "--output=line", "--minAlertLevel=error", str(py_error)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert error_res.returncode != 0
