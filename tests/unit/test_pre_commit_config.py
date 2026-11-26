"""Tests for sequence sorting and mapping key order in .pre-commit-config.yaml (#741)."""

from __future__ import annotations

import copy
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from tools.sync_pre_commit_deps import sync_deps

CANONICAL_HOOK_KEY_ORDER: tuple[str, ...] = (
    "id",
    "alias",
    "name",
    "description",
    "entry",
    "language",
    "language_version",
    "minimum_pre_commit_version",
    "files",
    "exclude",
    "types",
    "types_or",
    "exclude_types",
    "stages",
    "always_run",
    "pass_filenames",
    "require_serial",
    "fail_fast",
    "verbose",
    "log_file",
    "args",
    "additional_dependencies",
)
CANONICAL_HOOK_KEY_RANK: dict[str, int] = {key: idx for idx, key in enumerate(CANONICAL_HOOK_KEY_ORDER)}

FUNCTIONAL_ORDER_MULTI_HOOK_REPOS: dict[str, list[tuple[str, str]]] = {
    "https://github.com/ComPWA/taplo-pre-commit": [
        ("taplo-format", ""),
        ("taplo-lint", ""),
    ],
    "https://github.com/astral-sh/uv-pre-commit": [
        ("uv-lock", ""),
        ("uv-export", ""),
    ],
    "https://github.com/doublify/pre-commit-rust": [
        ("fmt", "cargo-fmt"),
        ("cargo-check", ""),
        ("clippy", "cargo-clippy"),
        ("clippy", "cargo-clippy-all-targets"),
    ],
    "https://github.com/djlint/djLint": [
        ("djlint-reformat-jinja", ""),
        ("djlint-jinja", ""),
    ],
    "https://github.com/vale-cli/vale": [
        ("vale", "vale-sync"),
        ("vale", ""),
        ("vale-commit-msg", ""),
    ],
}

UNORDERED_HOOK_SET_FIELDS: tuple[str, ...] = ("types", "types_or", "exclude_types", "stages")


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_pre_commit_config(cfg_path: Path | None = None) -> dict[str, Any]:
    """Load and parse .pre-commit-config.yaml."""
    target = cfg_path if cfg_path is not None else _repo_root() / ".pre-commit-config.yaml"
    assert target.is_file()
    with target.open(encoding="utf-8") as f:
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


def _as_str_list(value: object, label: str) -> list[str]:
    """Validate that value is a list of strings and return a typed copy."""
    assert isinstance(value, list), f"{label} must be a list"
    assert all(isinstance(item, str) for item in value), f"{label} items must all be strings"
    return [str(item) for item in value]


def _normalize_dep_pkg_name(requirement: str) -> str:
    """Extract and PEP 503-normalize package name from a requirement specifier."""
    raw_name = re.split(r"[<>=!~;\[\s@]", requirement, maxsplit=1)[0].strip()
    return re.sub(r"[-_.]+", "-", raw_name).lower()


def _assert_hook_keys_and_sets(repo_url: str, hook: dict[str, Any]) -> None:
    """Assert canonical hook mapping key order and sorted per-hook set sequences."""
    hook_id = f"{repo_url}#{hook.get('id')}"
    hook_keys = [str(k) for k in hook]
    unknown_keys = set(hook_keys) - set(CANONICAL_HOOK_KEY_RANK)
    assert not unknown_keys, f"Unrecognized hook keys {sorted(unknown_keys)} in {hook_id}"
    key_ranks = [CANONICAL_HOOK_KEY_RANK[k] for k in hook_keys]
    assert key_ranks == sorted(key_ranks), (
        f"Hook keys in {hook_id} violate canonical schema order: {hook_keys}"
    )

    for set_field in UNORDERED_HOOK_SET_FIELDS:
        if set_field in hook:
            vals = _as_str_list(hook[set_field], f"{hook_id}.{set_field}")
            assert vals == sorted(vals), f"{hook_id}.{set_field} must be sorted alphabetically"
            assert len(vals) == len(set(vals)), f"{hook_id}.{set_field} must not contain duplicates"

    if "additional_dependencies" in hook:
        deps = _as_str_list(hook["additional_dependencies"], f"{hook_id}.additional_dependencies")
        norm_names = [_normalize_dep_pkg_name(dep) for dep in deps]
        assert norm_names == sorted(norm_names), (
            f"{hook_id}.additional_dependencies must be sorted by normalized package name"
        )
        assert len(norm_names) == len(set(norm_names)), (
            f"{hook_id}.additional_dependencies must not contain duplicate packages"
        )


def _assert_standardized_ordering(config: dict[str, Any]) -> None:
    """Assert mapping key order and unordered sequence sorting across .pre-commit-config.yaml."""
    top_keys = [str(k) for k in config]
    assert top_keys == sorted(top_keys) == ["ci", "default_install_hook_types", "default_stages", "repos"]

    ci_cfg = config["ci"]
    assert isinstance(ci_cfg, dict)
    ci_keys = [str(k) for k in ci_cfg]
    assert (
        ci_keys
        == sorted(ci_keys)
        == [
            "autofix_commit_msg",
            "autofix_prs",
            "autoupdate_branch",
            "autoupdate_commit_msg",
            "autoupdate_schedule",
            "skip",
            "submodules",
        ]
    )

    for label, raw_seq in (
        ("ci.skip", ci_cfg["skip"]),
        ("default_install_hook_types", config["default_install_hook_types"]),
        ("default_stages", config["default_stages"]),
    ):
        seq = _as_str_list(raw_seq, label)
        assert seq == sorted(seq), f"{label} must be sorted alphabetically"
        assert len(seq) == len(set(seq)), f"{label} must not contain duplicates"

    repos = config["repos"]
    assert isinstance(repos, list)
    present_repo_urls = {str(r["repo"]) for r in repos if isinstance(r, dict)}
    assert set(FUNCTIONAL_ORDER_MULTI_HOOK_REPOS) <= present_repo_urls

    for repo_entry in repos:
        assert isinstance(repo_entry, dict)
        repo_url = str(repo_entry["repo"])
        expected_repo_keys = ["repo", "hooks"] if repo_url in {"meta", "local"} else ["repo", "rev", "hooks"]
        assert [str(k) for k in repo_entry] == expected_repo_keys, f"Invalid repo key order for {repo_url}"

        hooks = repo_entry["hooks"]
        assert isinstance(hooks, list)
        assert hooks, f"Repository {repo_url} must declare at least one hook"

        if len(hooks) > 1:
            if repo_url in FUNCTIONAL_ORDER_MULTI_HOOK_REPOS:
                actual_pairs = [(str(h["id"]), str(h.get("alias", ""))) for h in hooks if isinstance(h, dict)]
                assert actual_pairs == FUNCTIONAL_ORDER_MULTI_HOOK_REPOS[repo_url]
            else:
                hook_ids = [str(h["id"]) for h in hooks if isinstance(h, dict)]
                assert hook_ids == sorted(hook_ids), f"Hooks in {repo_url} must be sorted alphabetically"
                assert len(hook_ids) == len(set(hook_ids)), f"Duplicate hook IDs in {repo_url}"

        for hook in hooks:
            assert isinstance(hook, dict)
            _assert_hook_keys_and_sets(repo_url, hook)


def test_pre_commit_config_sequence_sorting_and_mapping_key_order() -> None:
    """Enforce sequence sorting and canonical mapping key order across .pre-commit-config.yaml (#741)."""
    config = _load_pre_commit_config()
    _assert_standardized_ordering(config)

    local_repo = _find_repo_entry(config, "local")
    assert [h["id"] for h in local_repo["hooks"]] == [
        "check-no-absolute-locale-paths",
        "file-line-length-check",
        "i18n-catalog-check",
        "suppression-audit",
    ]
    for hook in local_repo["hooks"]:
        if hook.get("language") == "python":
            assert hook["additional_dependencies"] == [
                "identify",
                "pathspec",
                "pyyaml",
                "rich",
                "typer",
            ]


def test_sync_pre_commit_deps_preserves_standardized_ordering(tmp_path: Path) -> None:
    """Verify tools/sync_pre_commit_deps.py updates versions without disturbing key or list order (#741)."""
    root = _repo_root()
    config = _load_pre_commit_config()
    ruff_rev = str(
        next(
            r["rev"] for r in config["repos"] if r["repo"] == "https://github.com/astral-sh/ruff-pre-commit"
        ),
    )
    ruff_ver = ruff_rev.lstrip("v")

    shutil.copy2(root / "uv.lock", tmp_path / "uv.lock")
    raw_cfg = (root / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    stale_cfg = raw_cfg.replace(f"rev: {ruff_rev}", "rev: v0.0.1", 1).replace(
        f"ruff=={ruff_ver}",
        "ruff==0.0.1",
        1,
    )
    assert stale_cfg != raw_cfg
    target_cfg = tmp_path / ".pre-commit-config.yaml"
    target_cfg.write_text(stale_cfg, encoding="utf-8")

    assert sync_deps(tmp_path, write=True) == 0
    assert target_cfg.read_text(encoding="utf-8") == raw_cfg
    _assert_standardized_ordering(_load_pre_commit_config(target_cfg))


@pytest.mark.parametrize(
    ("mutator", "expected_match"),
    [
        (lambda c: c["ci"]["skip"].reverse(), r"ci\.skip must be sorted"),
        (
            lambda c: c["default_install_hook_types"].reverse(),
            r"default_install_hook_types must be sorted",
        ),
        (
            lambda c: c["repos"].append({"hooks": [{"id": "x"}], "repo": "local"}),
            r"Invalid repo key order",
        ),
        (
            lambda c: c["repos"][0]["hooks"].reverse(),
            r"Hooks in meta must be sorted alphabetically",
        ),
        (
            lambda c: c["repos"][5]["hooks"].reverse(),
            r"taplo-format",
        ),
        (
            lambda c: c["repos"][0]["hooks"].append({"args": ["--x"], "id": "z"}),
            r"violate canonical schema order",
        ),
        (
            lambda c: c["repos"][-1]["hooks"][1]["additional_dependencies"].reverse(),
            r"additional_dependencies must be sorted",
        ),
    ],
)
def test_standardized_ordering_rejects_violations(
    mutator: Callable[[dict[str, Any]], object],
    expected_match: str,
) -> None:
    """Verify _assert_standardized_ordering fails when key order or sequence sorting drifts (#741)."""
    broken = copy.deepcopy(_load_pre_commit_config())
    mutator(broken)
    with pytest.raises(AssertionError, match=expected_match):
        _assert_standardized_ordering(broken)
