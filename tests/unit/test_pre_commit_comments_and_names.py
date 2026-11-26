"""Tests for repo header comments, ci.skip rationales, and hook names in .pre-commit-config.yaml (#748)."""

from __future__ import annotations

import copy
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

_REPO_DECL_RE = re.compile(r"^  - repo: (\S+)(?:  # .*)?$")
_HEADER_COMMENT_RE = re.compile(r"^  # (\S.*)$")
_CI_SKIP_ITEM_RE = re.compile(r"^    - ([a-z0-9-]+)  # (\S.{10,})$")

_PRE_COMMIT_HOOKS_URL = "https://github.com/pre-commit/pre-commit-hooks"
_CHECK_JSONSCHEMA_URL = "https://github.com/python-jsonschema/check-jsonschema"
_PYGREP_HOOKS_URL = "https://github.com/pre-commit/pygrep-hooks"

CLEAR_UPSTREAM_NAME_HOOKS: frozenset[tuple[str, str]] = frozenset(
    {
        ("meta", "check-hooks-apply"),
        ("meta", "check-useless-excludes"),
        ("https://github.com/pre-commit-ci/pre-commit-ci-config", "check-pre-commit-ci-config"),
        *(
            (_PRE_COMMIT_HOOKS_URL, hook_id)
            for hook_id in (
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
                "fix-byte-order-marker",
                "forbid-submodules",
                "mixed-line-ending",
                "name-tests-test",
                "trailing-whitespace",
            )
        ),
        ("https://github.com/abravalheri/validate-pyproject", "validate-pyproject"),
        ("https://github.com/regebro/pyroma", "pyroma"),
        ("https://github.com/asottile/add-trailing-comma", "add-trailing-comma"),
        ("https://github.com/jsh9/blank-line-after-blocks", "blank-line-after-blocks"),
        *(
            (_CHECK_JSONSCHEMA_URL, hook_id)
            for hook_id in (
                "check-codecov",
                "check-dependabot",
                "check-github-issue-config",
                "check-github-issue-forms",
                "check-github-workflows",
                "check-github-workflows-require-timeout",
                "check-mergify",
                "check-readthedocs",
                "check-renovate",
            )
        ),
        ("https://github.com/djlint/djLint", "djlint-reformat-jinja"),
        ("https://github.com/djlint/djLint", "djlint-jinja"),
        ("https://github.com/jsh9/markdown-heading-numbering", "markdown-heading-numbering"),
        ("https://github.com/rhysd/actionlint", "actionlint"),
        ("https://github.com/Yelp/detect-secrets", "detect-secrets"),
        *(
            (_PYGREP_HOOKS_URL, hook_id)
            for hook_id in (
                "python-check-blanket-noqa",
                "python-check-blanket-type-ignore",
                "python-check-mock-methods",
                "python-no-eval",
                "python-use-type-annotations",
                "text-unicode-replacement-char",
            )
        ),
        ("https://github.com/editorconfig-checker/editorconfig-checker.python", "editorconfig-checker"),
        ("https://github.com/compilerla/conventional-pre-commit", "conventional-pre-commit"),
    },
)


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _assert_single_line_repo_headers(lines: list[str], expected_repo_count: int) -> None:
    """Verify every '- repo:' block has exactly one descriptive single-line '# ...' header comment."""
    repo_indices = [idx for idx, line in enumerate(lines) if _REPO_DECL_RE.match(line)]
    assert len(repo_indices) == expected_repo_count, (
        f"Expected {expected_repo_count} '- repo:' lines, found {len(repo_indices)}"
    )

    for pos, idx in enumerate(repo_indices):
        repo_match = _REPO_DECL_RE.match(lines[idx])
        assert repo_match is not None
        repo_url = repo_match.group(1)

        assert idx >= 2, f"'- repo: {repo_url}' at line {idx + 1} lacks a preceding header comment"
        header_match = _HEADER_COMMENT_RE.match(lines[idx - 1])
        assert header_match is not None, (
            f"Line {idx} before '- repo: {repo_url}' must be a 2-space indented '# ...' comment"
        )

        prev_line = lines[idx - 2]
        expected_prev = "repos:" if pos == 0 else ""
        assert prev_line == expected_prev, (
            f"'- repo: {repo_url}' at line {idx + 1} must be preceded by a single-line comment "
            f"(found {prev_line!r} two lines above)"
        )

        comment_text = header_match.group(1).strip()
        assert len(comment_text.split()) >= 4, (
            f"Header comment {comment_text!r} for {repo_url} is too terse (< 4 words)"
        )
        assert len(comment_text) >= 25, (
            f"Header comment {comment_text!r} for {repo_url} is too short (< 25 chars)"
        )
        if repo_url == "local":
            assert comment_text != "File Line Length Enforcement"


def _assert_ci_skip_inline_rationales(lines: list[str], expected_skip_ids: list[str]) -> None:
    """Verify every entry in ci.skip carries an inline rationale comment."""
    skip_header_idx = next(
        (idx for idx, line in enumerate(lines) if line.startswith("  skip:")),
        None,
    )
    assert skip_header_idx is not None, "Missing '  skip:' section under ci:"

    parsed_ids: list[str] = []
    for line in lines[skip_header_idx + 1 :]:
        if not line.startswith("    - "):
            break

        item_match = _CI_SKIP_ITEM_RE.match(line)
        assert item_match is not None, f"ci.skip entry {line!r} must include a descriptive inline '# ...'"
        parsed_ids.append(item_match.group(1))

    assert parsed_ids == expected_skip_ids


def _assert_descriptive_hook_names(config: dict[str, Any]) -> None:
    """Verify every hook has either a descriptive explicit name: or an audited upstream name."""
    repos = config["repos"]
    assert isinstance(repos, list)

    present_pairs = {
        (str(r["repo"]), str(h["id"]))
        for r in repos
        if isinstance(r, dict)
        for h in r["hooks"]
        if isinstance(h, dict)
    }
    stale_allowlist = CLEAR_UPSTREAM_NAME_HOOKS - present_pairs
    assert not stale_allowlist, f"Stale CLEAR_UPSTREAM_NAME_HOOKS entries: {sorted(stale_allowlist)}"

    for repo_entry in repos:
        assert isinstance(repo_entry, dict)
        repo_url = str(repo_entry["repo"])
        for hook in repo_entry["hooks"]:
            assert isinstance(hook, dict)
            hook_id = str(hook["id"])
            alias = str(hook.get("alias", ""))
            pair = (repo_url, hook_id)

            if "name" in hook:
                assert pair not in CLEAR_UPSTREAM_NAME_HOOKS, (
                    f"{repo_url}#{hook_id} defines explicit name: and must not be in allowlist"
                )
                raw_name = hook["name"]
                assert isinstance(raw_name, str)
                assert raw_name == raw_name.strip()
                assert raw_name, f"Empty name: on {repo_url}#{hook_id}"
                assert raw_name.count("(") == raw_name.count(")"), (
                    f"Unbalanced parentheses in hook name {raw_name!r} on {repo_url}#{hook_id}"
                )
                assert len(raw_name.split()) >= 2, (
                    f"Hook name {raw_name!r} on {repo_url}#{hook_id} must be multi-word (not a bare slug)"
                )
                assert raw_name.lower() not in {hook_id.lower(), alias.lower()}, (
                    f"Hook name {raw_name!r} on {repo_url}#{hook_id} merely repeats id/alias"
                )
            else:
                assert pair in CLEAR_UPSTREAM_NAME_HOOKS, (
                    f"{repo_url}#{hook_id} omits 'name:' and is not in CLEAR_UPSTREAM_NAME_HOOKS"
                )


def assert_repo_comments_and_hook_names(raw_text: str, config: dict[str, Any]) -> None:
    """Enforce single-line repo header comments, ci.skip rationales, and descriptive hook names (#748)."""
    lines = raw_text.splitlines()
    _assert_single_line_repo_headers(lines, expected_repo_count=len(config["repos"]))
    _assert_ci_skip_inline_rationales(lines, expected_skip_ids=list(config["ci"]["skip"]))
    _assert_descriptive_hook_names(config)


@pytest.mark.parametrize(
    ("text_mutator", "cfg_mutator", "expected_match"),
    [
        (
            lambda t: t.replace(
                "  # Auto-format YAML configuration and workflow files (runs before yamllint)\n",
                "",
                1,
            ),
            None,
            r"must be a 2-space indented '# \.\.\.' comment",
        ),
        (
            lambda t: t.replace(
                "  # Auto-format YAML configuration and workflow files (runs before yamllint)\n",
                "  # Extra line\n"
                "  # Auto-format YAML configuration and workflow files (runs before yamllint)\n",
                1,
            ),
            None,
            r"must be preceded by a single-line comment",
        ),
        (
            lambda t: t.replace(
                "  # Auto-format YAML configuration and workflow files (runs before yamllint)",
                "  # Yamlfix formatter",
                1,
            ),
            None,
            r"too terse",
        ),
        (
            lambda t: re.sub(r"^    - ty  # .*$", "    - ty", t, count=1, flags=re.MULTILINE),
            None,
            r"ci\.skip entry .* must include a descriptive inline",
        ),
        (
            None,
            lambda c: c["repos"][15]["hooks"][0].update({"name": "ty"}),
            r"must be multi-word",
        ),
        (
            None,
            lambda c: c["repos"][15]["hooks"][0].update({"name": "use logger.warning("}),
            r"Unbalanced parentheses",
        ),
        (
            None,
            lambda c: c["repos"][15]["hooks"][0].pop("name"),
            r"omits 'name:' and is not in CLEAR_UPSTREAM_NAME_HOOKS",
        ),
    ],
)
def test_repo_comments_and_hook_names_rejects_violations(
    text_mutator: Callable[[str], str] | None,
    cfg_mutator: Callable[[dict[str, Any]], object] | None,
    expected_match: str,
) -> None:
    """Verify assert_repo_comments_and_hook_names catches missing/terse comments and bad names (#748)."""
    cfg_path = _repo_root() / ".pre-commit-config.yaml"
    raw_text = cfg_path.read_text(encoding="utf-8")
    config = copy.deepcopy(yaml.safe_load(raw_text))
    assert isinstance(config, dict)

    if text_mutator is not None:
        raw_text = text_mutator(raw_text)

    if cfg_mutator is not None:
        cfg_mutator(config)

    with pytest.raises(AssertionError, match=expected_match):
        assert_repo_comments_and_hook_names(raw_text, config)
