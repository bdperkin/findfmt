"""Tests for Stage 5-9 hooks in .pre-commit-config.yaml (#720-#724)."""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any

import yaml
from tools.quality_steps import QUALITY_STEPS


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
    assert repos[21]["repo"] == "https://github.com/doublify/pre-commit-rust"

    stage5_slice = repos[22:26]
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

    stage6_slice = repos[26:30]
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

    expected_prose_repos = {
        "https://github.com/codespell-project/codespell",
        "https://github.com/PrincetonUniversity/blocklint",
        "https://github.com/vale-cli/vale",
    }
    prose_indices_by_repo = {
        entry["repo"]: idx for idx, entry in enumerate(repos) if entry["repo"] in expected_prose_repos
    }
    assert set(prose_indices_by_repo) == expected_prose_repos
    assert all(idx > 29 for idx in prose_indices_by_repo.values())

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


def test_stage7_shell_docker_and_ci_workflow_hooks() -> None:
    """Verify Stage 7 shell, Docker, and workflow hooks and skipped non-hermetic variants (#722)."""
    config = _load_pre_commit_config()
    ci_skip = set(config["ci"]["skip"])
    repos = config["repos"]

    stage7_slice = repos[30:35]
    stage7_pairs = [(r["repo"], [h["id"] for h in r["hooks"]]) for r in stage7_slice]
    assert stage7_pairs == [
        ("https://github.com/scop/pre-commit-shfmt", ["shfmt"]),
        ("https://github.com/shellcheck-py/shellcheck-py", ["shellcheck"]),
        ("https://github.com/AleksaC/hadolint-py", ["hadolint"]),
        ("https://github.com/rhysd/actionlint", ["actionlint"]),
        ("https://github.com/zizmorcore/zizmor-pre-commit", ["zizmor"]),
    ]

    assert stage7_slice[0]["hooks"][0].get("args") == ["-i", "2", "-ci", "-bn", "-w"]
    assert stage7_slice[2]["hooks"][0].get("args") == ["--failure-threshold=warning"]

    stage7_hook_ids = {h["id"] for r in stage7_slice for h in r["hooks"]}
    assert stage7_hook_ids.isdisjoint(ci_skip)

    all_repo_urls = {r["repo"] for r in repos}
    assert "https://github.com/hadolint/hadolint" not in all_repo_urls

    all_hook_ids = {h["id"] for r in repos for h in r["hooks"]}
    assert all_hook_ids.isdisjoint(
        {
            "shfmt-docker",
            "shfmt-src",
            "hadolint-docker",
            "actionlint-docker",
            "actionlint-system",
        },
    )


def test_stage8_security_secrets_and_semgrep_hooks() -> None:
    """Verify Stage 8 detect-secrets, offline Semgrep ruleset, and pygrep ordering (#723)."""
    root = _repo_root()
    config = _load_pre_commit_config()
    ci_skip = set(config["ci"]["skip"])
    repos = config["repos"]

    stage8_slice = repos[35:38]
    stage8_pairs = [(r["repo"], [h["id"] for h in r["hooks"]]) for r in stage8_slice]
    assert stage8_pairs == [
        ("https://github.com/Yelp/detect-secrets", ["detect-secrets"]),
        ("https://github.com/semgrep/pre-commit", ["semgrep"]),
        (
            "https://github.com/pre-commit/pygrep-hooks",
            [
                "python-check-blanket-noqa",
                "python-check-blanket-type-ignore",
                "python-check-mock-methods",
                "python-no-eval",
                "python-no-log-warn",
                "python-use-type-annotations",
                "text-unicode-replacement-char",
            ],
        ),
    ]

    detect_secrets_hook = stage8_slice[0]["hooks"][0]
    assert detect_secrets_hook.get("exclude") == r"(^|/)(uv|Cargo)\.lock$"

    semgrep_hook = stage8_slice[1]["hooks"][0]
    assert semgrep_hook.get("types_or") == ["python", "rust"]
    semgrep_args = semgrep_hook.get("args", [])
    assert "--config" in semgrep_args
    assert ".semgrep.yml" in semgrep_args
    assert "--error" in semgrep_args
    assert "--metrics=off" in semgrep_args
    assert "--disable-version-check" in semgrep_args

    assert "semgrep" in ci_skip
    online_safe_ids = {h["id"] for r in (stage8_slice[0], stage8_slice[2]) for h in r["hooks"]}
    assert online_safe_ids.isdisjoint(ci_skip)

    semgrep_rev = stage8_slice[1]["rev"].lstrip("v")
    quality_cmds = dict(QUALITY_STEPS)
    semgrep_step = quality_cmds["Semgrep Hybrid Security & Boundary Audit"]
    assert f"semgrep=={semgrep_rev}" in semgrep_step
    assert ".semgrep.yml" in semgrep_step
    assert "--error" in semgrep_step

    all_hook_ids = {h["id"] for r in repos for h in r["hooks"]}
    assert all_hook_ids.isdisjoint({"semgrep-ci", "semgrep-docker", "semgrep-docker-develop"})

    semgrep_cfg_path = root / ".semgrep.yml"
    assert semgrep_cfg_path.is_file()
    with semgrep_cfg_path.open(encoding="utf-8") as f:
        semgrep_cfg = yaml.safe_load(f)

    assert isinstance(semgrep_cfg, dict)
    rules = semgrep_cfg.get("rules", [])
    assert isinstance(rules, list)
    rule_ids = {r["id"] for r in rules}
    assert {
        "findfmt-python-no-shell-true",
        "findfmt-python-no-unsafe-yaml-load",
        "findfmt-python-no-pickle-deserialization",
        "findfmt-gateway-boundary-rust-ext",
        "findfmt-rust-no-process-exit-or-abort",
        "findfmt-rust-no-raw-stdio-macros",
    } <= rule_ids
    rule_langs = {lang for r in rules for lang in r.get("languages", [])}
    assert {"python", "rust"} <= rule_langs


def test_stage9_prose_editorconfig_and_commit_msg_hooks() -> None:
    """Verify Stage 9 prose/EditorConfig/commit-msg order, .editorconfig rules, and skipped gitlint (#724)."""
    root = _repo_root()
    config = _load_pre_commit_config()
    ci_skip = set(config["ci"]["skip"])
    repos = config["repos"]

    assert len(repos) == 44
    assert repos[43]["repo"] == "local"

    stage9_slice = repos[38:43]
    stage9_pairs = [(r["repo"], [h["id"] for h in r["hooks"]]) for r in stage9_slice]
    assert stage9_pairs == [
        ("https://github.com/codespell-project/codespell", ["codespell"]),
        ("https://github.com/PrincetonUniversity/blocklint", ["blocklint"]),
        ("https://github.com/editorconfig-checker/editorconfig-checker.python", ["editorconfig-checker"]),
        ("https://github.com/vale-cli/vale", ["vale", "vale", "vale-commit-msg"]),
        ("https://github.com/compilerla/conventional-pre-commit", ["conventional-pre-commit"]),
    ]

    assert stage9_slice[0]["hooks"][0].get("exclude") == r"\.(po|pot)$"
    assert stage9_slice[2]["hooks"][0].get("args") == ["-disable-indent-size"]
    assert stage9_slice[4]["hooks"][0].get("stages") == ["commit-msg"]

    assert {"codespell", "blocklint", "editorconfig-checker", "conventional-pre-commit"}.isdisjoint(ci_skip)
    assert {"vale", "vale-commit-msg"} <= ci_skip

    all_repo_urls = {r["repo"] for r in repos}
    assert "https://github.com/jorisroovers/gitlint" not in all_repo_urls

    all_hook_ids = {h["id"] for r in repos for h in r["hooks"]}
    assert all_hook_ids.isdisjoint({"gitlint", "gitlint-ci", "editorconfig-checker-system"})

    editorconfig_path = root / ".editorconfig"
    assert editorconfig_path.is_file()
    parser = configparser.ConfigParser()
    parser.read_string("[__root__]\n" + editorconfig_path.read_text(encoding="utf-8"))
    assert parser["__root__"]["root"] == "true"
    assert dict(parser["*"]) == {
        "charset": "utf-8",
        "end_of_line": "lf",
        "insert_final_newline": "true",
        "trim_trailing_whitespace": "true",
    }
    assert parser["*.{py,pyi,rs}"]["indent_size"] == "4"
    assert parser["*.{toml,yml,yaml,json,jsonl,html,jinja,css,sh,svg,xml}"]["indent_size"] == "2"
    assert parser["tests/unit/api_surface.json"]["indent_size"] == "1"
    assert parser["{Makefile,*.mk}"]["indent_style"] == "tab"
