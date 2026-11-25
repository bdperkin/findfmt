"""Tests for Stage 5-9 hooks in .pre-commit-config.yaml (#720-#724)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


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


def test_stage5_yaml_json_schemas_and_html_template_hooks() -> None:
    """Verify Stage 5 formatter-before-linter order, schema hooks, and djLint Jinja hooks (#720)."""
    config = _load_pre_commit_config()
    ci_skip = set(config["ci"]["skip"])
    repos = config["repos"]
    assert repos[20]["repo"] == "https://github.com/doublify/pre-commit-rust"

    stage5_slice = repos[21:25]
    assert [r["repo"] for r in stage5_slice] == [
        "https://github.com/lyz-code/yamlfix",
        "https://github.com/adrienverge/yamllint",
        "https://github.com/python-jsonschema/check-jsonschema",
        "https://github.com/djlint/djLint",
    ]

    assert [h["id"] for h in stage5_slice[0]["hooks"]] == ["yamlfix"]
    assert [h["id"] for h in stage5_slice[1]["hooks"]] == ["yamllint"]
    assert stage5_slice[1]["hooks"][0].get("args") == ["-c", ".yamllint.yaml"]

    schema_hook_ids = {h["id"] for h in stage5_slice[2]["hooks"]}
    assert schema_hook_ids == {
        "check-codecov",
        "check-dependabot",
        "check-github-issue-config",
        "check-github-issue-forms",
        "check-github-workflows",
        "check-github-workflows-require-timeout",
        "check-mergify",
        "check-readthedocs",
        "check-renovate",
    }

    djlint_hooks = stage5_slice[3]["hooks"]
    assert [h["id"] for h in djlint_hooks] == ["djlint-reformat-jinja", "djlint-jinja"]
    for hook in djlint_hooks:
        assert hook.get("files") == "^docs/source/_templates/"
        assert hook.get("types_or") == ["html", "jinja"]

    stage5_hook_ids = {h["id"] for r in stage5_slice for h in r["hooks"]}
    assert stage5_hook_ids.isdisjoint(ci_skip)


def test_stage6_documentation_markdown_and_rst_hooks() -> None:
    """Verify Stage 6 Markdown chain ordering, mdformat-ruff parity, and skipped reST/Node hooks (#721)."""
    root = _repo_root()
    config = _load_pre_commit_config()
    ci_skip = set(config["ci"]["skip"])
    repos = config["repos"]

    stage6_slice = repos[25:29]
    stage6_pairs = [(r["repo"], [h["id"] for h in r["hooks"]]) for r in stage6_slice]
    assert stage6_pairs == [
        ("https://github.com/jsh9/markdown-heading-numbering", ["markdown-heading-numbering"]),
        ("https://github.com/jsh9/markdown-toc-creator", ["markdown-toc-creator"]),
        ("https://github.com/hukkin/mdformat", ["mdformat"]),
        ("https://github.com/jackdewinter/pymarkdown", ["pymarkdown"]),
    ]

    assert stage6_slice[0]["hooks"][0].get("exclude") == r"^(CHANGELOG|THIRD_PARTY_LICENSES)\.md$"
    assert stage6_slice[1]["hooks"][0].get("args") == ["--proactive", "False"]

    mdformat_deps = stage6_slice[2]["hooks"][0].get("additional_dependencies", [])
    dep_names = {dep.split("==")[0] for dep in mdformat_deps}
    assert {"mdformat-frontmatter", "mdformat-gfm", "mdformat-ruff", "ruff"} == dep_names

    ruff_repo_rev = next(
        r["rev"] for r in repos if r["repo"] == "https://github.com/astral-sh/ruff-pre-commit"
    )
    assert f"ruff=={ruff_repo_rev.lstrip('v')}" in mdformat_deps

    stage6_hook_ids = {h["id"] for r in stage6_slice for h in r["hooks"]}
    assert stage6_hook_ids.isdisjoint(ci_skip)

    prose_indices = [
        idx
        for idx, entry in enumerate(repos)
        if entry["repo"]
        in {
            "https://github.com/codespell-project/codespell",
            "https://github.com/PrincetonUniversity/blocklint",
            "https://github.com/vale-cli/vale",
        }
    ]
    assert all(idx > 28 for idx in prose_indices)

    all_repo_urls = {r["repo"] for r in repos}
    assert all_repo_urls.isdisjoint(
        {
            "https://github.com/adamchainz/blacken-docs",
            "https://github.com/igorshubovych/markdownlint-cli",
            "https://github.com/PyCQA/doc8",
            "https://github.com/rstcheck/rstcheck",
        },
    )
    assert list((root / "docs").rglob("*.rst")) == []
