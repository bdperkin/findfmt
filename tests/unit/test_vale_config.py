"""Unit tests for Vale pre-commit hook, .vale.ini scopes, and CI version parity (#727)."""

from __future__ import annotations

import configparser
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
    assert "--minAlertLevel=error" in str(msg_hook.get("entry", ""))
    assert "--path=COMMIT_EDITMSG" in str(msg_hook.get("entry", ""))

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


def test_vale_ini_sections_and_gitignore_entries() -> None:
    """Validate .vale.ini Markdown, code-comment, and commit-msg sections plus .gitignore entries (#727)."""
    root = _repo_root()
    vale_ini_text = (root / ".vale.ini").read_text(encoding="utf-8")
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string("[__root__]\n" + vale_ini_text)

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
