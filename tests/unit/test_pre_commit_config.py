"""Tests for Stage 1-4, Rust, and TOML hooks in .pre-commit-config.yaml (#591, #716-#719)."""

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


def test_stage2_packaging_lockfiles_and_config_hooks() -> None:
    """Verify Stage 2 ordering, retained packaging/lockfile hooks, and skipped variants (#717)."""
    config = _load_pre_commit_config()
    ci_skip = set(config["ci"]["skip"])
    repos = config["repos"]
    stage2_repos = [r["repo"] for r in repos[4:9]]
    assert stage2_repos == [
        "https://github.com/tox-dev/pyproject-fmt",
        "https://github.com/ComPWA/taplo-pre-commit",
        "https://github.com/abravalheri/validate-pyproject",
        "https://github.com/astral-sh/uv-pre-commit",
        "https://github.com/regebro/pyroma",
    ]

    all_repo_urls = {r["repo"] for r in repos}
    assert "https://github.com/tox-dev/tox-ini-fmt" not in all_repo_urls

    pyproject_fmt = _find_repo_entry(config, "https://github.com/tox-dev/pyproject-fmt")
    assert [h["id"] for h in pyproject_fmt["hooks"]] == ["pyproject-fmt"]
    assert "pyproject-fmt" not in ci_skip

    validate_pyproject = _find_repo_entry(config, "https://github.com/abravalheri/validate-pyproject")
    assert [h["id"] for h in validate_pyproject["hooks"]] == ["validate-pyproject"]
    assert "validate-pyproject" not in ci_skip

    uv_repo = _find_repo_entry(config, "https://github.com/astral-sh/uv-pre-commit")
    uv_hooks = {h["id"]: h for h in uv_repo["hooks"]}
    assert set(uv_hooks) == {"uv-lock", "uv-export"}
    assert set(uv_hooks).isdisjoint({"uv-sync", "pip-compile", "uv-audit"})
    assert set(uv_hooks).isdisjoint(ci_skip)
    assert "--output-file=.clusterfuzzlite/requirements.txt" in uv_hooks["uv-export"]["args"]

    pyroma_repo = _find_repo_entry(config, "https://github.com/regebro/pyroma")
    pyroma_hooks = pyroma_repo["hooks"]
    assert [h["id"] for h in pyroma_hooks] == ["pyroma"]
    assert "--min=10" in pyroma_hooks[0]["args"]
    assert "pyroma" in ci_skip


def test_stage3_python_auto_formatters_and_code_modifiers() -> None:
    """Verify Stage 3 mutator sequence, ruff-check migration, and skipped docformatter (#718)."""
    config = _load_pre_commit_config()
    ci_skip = set(config["ci"]["skip"])
    repos = config["repos"]
    stage3_slice = repos[9:15]
    stage3_pairs = [(r["repo"], [h["id"] for h in r["hooks"]]) for r in stage3_slice]
    assert stage3_pairs == [
        ("https://github.com/bwhmather/ssort", ["ssort"]),
        ("https://github.com/marcogorelli/absolufy-imports", ["absolufy-imports"]),
        ("https://github.com/asottile/add-trailing-comma", ["add-trailing-comma"]),
        ("https://github.com/astral-sh/ruff-pre-commit", ["ruff-check"]),
        ("https://github.com/jsh9/blank-line-after-blocks", ["blank-line-after-blocks"]),
        ("https://github.com/astral-sh/ruff-pre-commit", ["ruff-format"]),
    ]

    ruff_check_entry = stage3_slice[3]["hooks"][0]
    assert ruff_check_entry.get("args") == ["--fix", "--exit-non-zero-on-fix"]
    assert stage3_slice[3]["rev"] == stage3_slice[5]["rev"]

    all_hook_ids = {h["id"] for r in repos for h in r["hooks"]}
    assert "ruff" not in all_hook_ids
    assert "docformatter" not in all_hook_ids
    assert {
        "ssort",
        "absolufy-imports",
        "add-trailing-comma",
        "ruff-check",
        "blank-line-after-blocks",
        "ruff-format",
    }.isdisjoint(ci_skip)


def test_stage4_python_type_dependency_and_static_quality_hooks() -> None:
    """Verify Stage 4 analyzer ordering, ci.skip policy, and QUALITY_STEPS parity (#719)."""
    config = _load_pre_commit_config()
    ci_skip = set(config["ci"]["skip"])
    repos = config["repos"]
    stage4_slice = repos[15:20]
    stage4_pairs = [(r["repo"], [h["id"] for h in r["hooks"]]) for r in stage4_slice]
    assert stage4_pairs == [
        ("https://github.com/astral-sh/ty-pre-commit", ["ty"]),
        ("https://github.com/osprey-oss/deptry", ["deptry"]),
        ("https://github.com/jendrikseipp/vulture", ["vulture"]),
        ("https://github.com/rubik/xenon", ["xenon"]),
        ("https://github.com/econchick/interrogate", ["interrogate"]),
    ]

    assert stage4_slice[0]["hooks"][0].get("args") == ["--group", "lint"]
    assert stage4_slice[2]["hooks"][0].get("args") == ["src"]
    assert stage4_slice[3]["hooks"][0].get("args") == ["-b", "B", "-m", "B", "-a", "A", "src"]
    assert stage4_slice[3]["hooks"][0].get("pass_filenames") is False
    assert stage4_slice[4]["hooks"][0].get("args") == ["src"]
    assert stage4_slice[4]["hooks"][0].get("pass_filenames") is False

    assert {"ty", "deptry"} <= ci_skip
    assert {"vulture", "xenon", "interrogate"}.isdisjoint(ci_skip)

    quality_cmds = {cmd for _, cmd in QUALITY_STEPS}
    assert ("uv", "run", "ty", "check") in quality_cmds
    assert ("uv", "run", "deptry", ".") in quality_cmds
    assert ("uv", "run", "vulture", "src") in quality_cmds
    assert ("uv", "run", "xenon", "-b", "B", "-m", "B", "-a", "A", "src") in quality_cmds
    assert ("uv", "run", "interrogate", "src") in quality_cmds
