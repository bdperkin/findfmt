"""Unit tests for Vale pre-commit hook, .vale.ini scopes, and CI version parity (#727)."""

from __future__ import annotations

import configparser
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture(scope="session")
def pre_commit_cache_dir() -> Path:
    """Resolve the host pre-commit cache directory before function-level HOME isolation."""
    env_home = os.environ.get("PRE_COMMIT_HOME")
    if env_home is not None and env_home != "":
        return Path(env_home)

    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache is not None and xdg_cache != "":
        return Path(xdg_cache) / "pre-commit"

    return Path.home() / ".cache" / "pre-commit"


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


def _find_vale_binary(cache_root: Path) -> str | None:
    """Locate an installed Vale executable on PATH or inside the pre-commit cache."""
    direct = shutil.which("vale")
    if direct is not None:
        return direct

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
    assert msg_hook.get("entry") == "sh tools/vale_commit_msg.sh"
    script_text = (root / "tools" / "vale_commit_msg.sh").read_text(encoding="utf-8")
    assert "commit.cleanup" in script_text
    assert "git stripspace --strip-comments" in script_text
    assert "sed" in script_text
    assert "--minAlertLevel=error" in script_text
    assert "--path=COMMIT_EDITMSG" in script_text

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


def _vale_commit_msg_argv(root: Path) -> list[str]:
    """Return tokenized argv for the vale-commit-msg hook entry with script path resolved."""
    pc_data = _load_yaml(root / ".pre-commit-config.yaml")
    vale_repo = next(
        r for r in pc_data.get("repos", []) if r.get("repo") == "https://github.com/vale-cli/vale"
    )
    msg_hook = next(h for h in vale_repo["hooks"] if h.get("id") == "vale-commit-msg")
    tokens = shlex.split(str(msg_hook["entry"]))
    return [str(root / tok) if tok.startswith("tools/") else tok for tok in tokens]


def test_vale_commit_msg_filter_respects_comment_char_and_cleanup(tmp_path: Path) -> None:
    """Verify vale-commit-msg honors cleanup modes, commentChar, scissors, and trailers (#727)."""
    if os.name == "nt":
        pytest.skip("POSIX sh commit-msg filter test requires POSIX shell environment")

    git_bin = shutil.which("git")
    if shutil.which("sh") is None or git_bin is None or shutil.which("sed") is None:
        pytest.skip("sh, git, or sed binary not available")

    root = _repo_root()
    repo_dir = tmp_path / "isolated_repo"
    repo_dir.mkdir()
    subprocess.run([git_bin, "init", str(repo_dir)], capture_output=True, text=True, check=True)

    shim_dir = tmp_path / "shim_bin"
    shim_dir.mkdir()
    vale_shim = shim_dir / "vale"
    vale_shim.write_text("#!/bin/sh\ncat\n", encoding="utf-8")
    vale_shim.chmod(0o755)

    hook_argv = _vale_commit_msg_argv(root)
    base_env = os.environ.copy()
    base_env.pop("GIT_EDITOR", None)
    base_env["PATH"] = f"{shim_dir}{os.pathsep}{base_env.get('PATH', '')}"

    default_msg = tmp_path / "COMMIT_EDITMSG_DEFAULT"
    default_msg.write_text(
        "ci(pre-commit): integrate `my_nonexistent_ident_xyz` hook (#727)\n\n"
        "# git interactive comment with zxqwvut token\n"
        "Signed-off-by: Jane Kaczmarek <jk@example.com>\n",
        encoding="utf-8",
    )
    default_res = subprocess.run(
        [*hook_argv, str(default_msg)],
        cwd=repo_dir,
        env=base_env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "ci(pre-commit): integrate `my_nonexistent_ident_xyz` hook (#727)" in default_res.stdout
    assert "zxqwvut" not in default_res.stdout
    assert "Kaczmarek" not in default_res.stdout

    non_editor_env = base_env.copy()
    non_editor_env["GIT_EDITOR"] = ":"
    non_editor_res = subprocess.run(
        [*hook_argv, str(default_msg)],
        cwd=repo_dir,
        env=non_editor_env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "# git interactive comment with zxqwvut token" in non_editor_res.stdout
    assert "Kaczmarek" not in non_editor_res.stdout

    semicolon_msg = tmp_path / "COMMIT_EDITMSG_SEMICOLON"
    semicolon_msg.write_text(
        "ci(pre-commit): honor custom comment char (#727)\n\n"
        "; zxqwvut template comment with custom commentChar\n"
        "Co-authored-by: Jane Kaczmarek <jk@example.com>\n"
        "; ------------------------ >8 ------------------------\n"
        "diff --git a/foo.py b/foo.py\n"
        "+zxqwvut_diff_token\n",
        encoding="utf-8",
    )
    semicolon_env = base_env.copy()
    semicolon_env["GIT_CONFIG_COUNT"] = "1"
    semicolon_env["GIT_CONFIG_KEY_0"] = "core.commentChar"
    semicolon_env["GIT_CONFIG_VALUE_0"] = ";"
    semicolon_res = subprocess.run(
        [*hook_argv, str(semicolon_msg)],
        cwd=repo_dir,
        env=semicolon_env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "ci(pre-commit): honor custom comment char (#727)" in semicolon_res.stdout
    assert "zxqwvut" not in semicolon_res.stdout
    assert "Kaczmarek" not in semicolon_res.stdout


def test_vale_live_prose_and_code_comment_linting(
    tmp_path: Path,
    pre_commit_cache_dir: Path,
) -> None:
    """Verify live Vale commit-msg and Python comment prose checks when synced (#727)."""
    root = _repo_root()
    vale_bin = _find_vale_binary(pre_commit_cache_dir)
    styles_synced = (root / ".github" / "styles" / "Google").is_dir() and (
        root / ".github" / "styles" / "proselint"
    ).is_dir()
    if vale_bin is None or not styles_synced:
        pytest.skip("Vale binary or synced styles (.github/styles/{Google,proselint}) not available")

    cfg_flag = f"--config={root / '.vale.ini'}"
    ok_msg_res = subprocess.run(
        [vale_bin, cfg_flag, "--output=line", "--minAlertLevel=error", "--path=COMMIT_EDITMSG"],
        input="ci(pre-commit): integrate `my_nonexistent_ident_xyz` hook (#727)\n",
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
    assert bad_msg_res.returncode == 1, bad_msg_res.stdout + bad_msg_res.stderr
    assert "Vale.Spelling" in bad_msg_res.stdout

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
    assert error_res.returncode == 1, error_res.stdout + error_res.stderr
    assert "Vale.Repetition" in error_res.stdout
