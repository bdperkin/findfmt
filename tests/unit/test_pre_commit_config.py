"""Tests for Stage 1 hygiene, Rust, and TOML hooks in .pre-commit-config.yaml (#591, #716)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from tools.quality_steps import CARGO_MANIFEST, QUALITY_STEPS


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_pre_commit_config() -> dict[str, Any]:
    """Load and parse .pre-commit-config.yaml."""
    cfg_path = _repo_root() / ".pre-commit-config.yaml"
    assert cfg_path.is_file()
    with cfg_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict)
    return data


def _find_repo_entry(config: dict[str, Any], repo_url: str) -> dict[str, Any]:
    """Locate a repository block in .pre-commit-config.yaml by URL."""
    repos = config.get("repos")
    assert isinstance(repos, list)
    matches = [r for r in repos if isinstance(r, dict) and r.get("repo") == repo_url]
    assert len(matches) == 1, f"Expected exactly 1 entry for {repo_url}, got {len(matches)}"
    return matches[0]


def test_taplo_hooks_scoped_to_findfmt_rs_and_enabled_in_pre_commit_ci() -> None:
    """Verify taplo-format and offline taplo-lint cover findfmt_rs TOML files without pyproject conflict."""
    config = _load_pre_commit_config()
    ci_skip = set(config["ci"]["skip"])
    taplo_repo = _find_repo_entry(config, "https://github.com/ComPWA/taplo-pre-commit")
    assert taplo_repo.get("rev")

    hooks_by_id = {h["id"]: h for h in taplo_repo["hooks"]}
    assert set(hooks_by_id) == {"taplo-format", "taplo-lint"}
    for hook_id, hook in hooks_by_id.items():
        assert hook.get("files") == r"^findfmt_rs/.*\.toml$"
        assert hook_id not in ci_skip

    assert hooks_by_id["taplo-lint"].get("args") == ["--no-schema"]


def test_rust_cargo_hooks_and_ci_skip_parity_with_quality_gate() -> None:
    """Verify doublify/pre-commit-rust hooks, ^findfmt_rs/ scoping, ci.skip, and CI step parity (#591)."""
    config = _load_pre_commit_config()
    ci_skip = set(config["ci"]["skip"])
    assert {"fmt", "cargo-check", "clippy"} <= ci_skip

    rust_repo = _find_repo_entry(config, "https://github.com/doublify/pre-commit-rust")
    assert rust_repo.get("rev")
    hooks = rust_repo["hooks"]
    assert [h["id"] for h in hooks] == ["fmt", "cargo-check", "clippy", "clippy"]

    for hook in hooks:
        assert hook.get("files") == "^findfmt_rs/"
        assert hook.get("types") == ["file"]
        assert hook.get("types_or") == ["rust", "toml"]

    fmt_hook, check_hook, clippy_lib_hook, clippy_all_hook = hooks
    assert fmt_hook.get("alias") == "cargo-fmt"
    assert fmt_hook.get("pass_filenames") is False
    assert fmt_hook.get("args") == ["--manifest-path", CARGO_MANIFEST]

    assert check_hook.get("args") == ["--manifest-path", CARGO_MANIFEST, "--locked"]
    assert clippy_lib_hook.get("alias") == "cargo-clippy"
    assert clippy_lib_hook.get("args") == [
        "--manifest-path",
        CARGO_MANIFEST,
        "--locked",
        "--lib",
        "--",
        "-D",
        "warnings",
    ]
    assert clippy_all_hook.get("alias") == "cargo-clippy-all-targets"
    assert clippy_all_hook.get("args") == [
        "--manifest-path",
        CARGO_MANIFEST,
        "--locked",
        "--no-default-features",
        "--all-targets",
        "--",
        "-D",
        "warnings",
    ]

    quality_cmds = {cmd for _, cmd in QUALITY_STEPS}
    assert ("cargo", "fmt", "--manifest-path", CARGO_MANIFEST, "--check") in quality_cmds
    assert ("cargo", "check", "--manifest-path", CARGO_MANIFEST, "--locked") in quality_cmds
    assert (
        "cargo",
        "clippy",
        "--manifest-path",
        CARGO_MANIFEST,
        "--locked",
        "--lib",
        "--",
        "-D",
        "warnings",
    ) in quality_cmds
    assert (
        "cargo",
        "clippy",
        "--manifest-path",
        CARGO_MANIFEST,
        "--locked",
        "--no-default-features",
        "--all-targets",
        "--",
        "-D",
        "warnings",
    ) in quality_cmds


def test_stage1_meta_and_core_hygiene_hooks() -> None:
    """Verify Stage 1 ordering and adopted/deferred/skipped pre-commit-hooks (#716)."""
    config = _load_pre_commit_config()
    repos = config["repos"]
    first_four_repos = [r["repo"] for r in repos[:4]]
    assert first_four_repos == [
        "meta",
        "https://github.com/pre-commit-ci/pre-commit-ci-config",
        "https://github.com/pre-commit/sync-pre-commit-deps",
        "https://github.com/pre-commit/pre-commit-hooks",
    ]

    core_repo = repos[3]
    hooks_by_id = {h["id"]: h for h in core_repo["hooks"]}
    expected_adopted = {
        "check-added-large-files",
        "check-ast",
        "check-case-conflict",
        "check-executables-have-shebangs",
        "check-illegal-windows-names",
        "check-json",
        "check-merge-conflict",
        "check-shebang-scripts-are-executable",
        "check-toml",
        "check-vcs-permalinks",
        "check-yaml",
        "debug-statements",
        "destroyed-symlinks",
        "detect-private-key",
        "end-of-file-fixer",
        "file-contents-sorter",
        "fix-byte-order-marker",
        "forbid-submodules",
        "mixed-line-ending",
        "name-tests-test",
        "trailing-whitespace",
    }
    assert set(hooks_by_id) == expected_adopted
    assert hooks_by_id["mixed-line-ending"].get("args") == ["--fix=lf"]
    assert (
        hooks_by_id["check-shebang-scripts-are-executable"].get("exclude") == "^findfmt_rs/fuzz/seed_corpus/"
    )

    skipped_or_deferred = {
        "check-builtin-literals",
        "check-docstring-first",
        "check-symlinks",
        "check-xml",
        "detect-aws-credentials",
        "double-quote-string-fixer",
        "forbid-new-submodules",
        "no-commit-to-branch",
        "pretty-format-json",
        "requirements-txt-fixer",
        "sort-simple-yaml",
    }
    assert set(hooks_by_id).isdisjoint(skipped_or_deferred)
