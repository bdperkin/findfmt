"""Unit tests for repository automation configurations (.coderabbit.yaml, etc.)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_coderabbit_config() -> dict[str, Any]:
    """Load and parse .coderabbit.yaml from the repository root."""
    cfg_path = _repo_root() / ".coderabbit.yaml"
    assert cfg_path.is_file(), f"Missing CodeRabbit configuration at {cfg_path}"
    with cfg_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), ".coderabbit.yaml must parse to a YAML mapping"
    return data


def test_coderabbit_top_level_and_review_profile() -> None:
    """Validate .coderabbit.yaml schema directive, language, and review profile (#628)."""
    raw = (_repo_root() / ".coderabbit.yaml").read_text(encoding="utf-8")
    assert "https://coderabbit.ai/integrations/schema.v2.json" in raw

    cfg = _load_coderabbit_config()
    assert cfg.get("language") == "en-US"
    assert cfg.get("early_access") is False

    reviews = cfg.get("reviews")
    assert isinstance(reviews, dict)
    assert reviews.get("profile") == "chill"
    assert reviews.get("high_level_summary") is True
    assert reviews.get("poem") is False
    assert reviews.get("review_status") is True

    auto_review = reviews.get("auto_review")
    assert isinstance(auto_review, dict)
    assert auto_review.get("enabled") is True
    assert auto_review.get("drafts") is True
    assert auto_review.get("base_branches") == ["main"]
    assert auto_review.get("ignore_title_keywords") == ["merge queue: checking"]
    assert auto_review.get("ignore_usernames") == ["mergify[bot]"]

    chat = cfg.get("chat")
    assert isinstance(chat, dict)
    assert chat.get("auto_reply") is True


def test_coderabbit_path_filters_and_instructions() -> None:
    """Validate .coderabbit.yaml path filters and Python/.gitignore/tests instructions (#628)."""
    reviews = _load_coderabbit_config()["reviews"]

    path_filters = reviews.get("path_filters")
    assert isinstance(path_filters, list)
    assert "!uv.lock" in path_filters
    assert "!dist/**" in path_filters

    instructions = reviews.get("path_instructions")
    assert isinstance(instructions, list)
    by_path = {
        str(entry.get("path")): str(entry.get("instructions", ""))
        for entry in instructions
        if isinstance(entry, dict)
    }

    assert "src/findfmt/**/*.py" in by_path
    assert "annotations" in by_path["src/findfmt/**/*.py"]
    assert "ty" in by_path["src/findfmt/**/*.py"]

    assert "src/findfmt/traversal/**/*.py" in by_path
    assert ".gitignore" in by_path["src/findfmt/traversal/**/*.py"]

    assert "tests/**/*.py" in by_path
    assert "coverage" in by_path["tests/**/*.py"]
    assert "assert" in by_path["tests/**/*.py"]


def _load_renovate_config() -> dict[str, Any]:
    """Load and parse renovate.json from the repository root."""
    cfg_path = _repo_root() / "renovate.json"
    assert cfg_path.is_file(), f"Missing Renovate configuration at {cfg_path}"
    with cfg_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict), "renovate.json must parse to a JSON object"
    return data


def test_renovate_top_level_and_package_groups() -> None:
    """Validate renovate.json schema, presets, schedule, and dependency groups (#629)."""
    cfg = _load_renovate_config()
    assert cfg.get("$schema") == "https://docs.renovatebot.com/renovate-schema.json"

    extends = cfg.get("extends")
    assert isinstance(extends, list)
    assert "config:recommended" in extends
    assert ":semanticCommits" in extends
    assert "helpers:pinGitHubActionDigestsToSemver" in extends

    assert cfg.get("rangeStrategy") == "update-lockfile"
    assert cfg.get("minimumReleaseAge") == "7 days"
    assert cfg.get("labels") == ["dependencies"]
    assert cfg.get("ignorePaths") == [".clusterfuzzlite/requirements.txt"]

    lock_maint = cfg.get("lockFileMaintenance")
    assert isinstance(lock_maint, dict)
    assert lock_maint.get("enabled") is True

    rules = cfg.get("packageRules")
    assert isinstance(rules, list)
    groups = {str(r.get("groupName")): r for r in rules if isinstance(r, dict) and "groupName" in r}

    assert "python-dev-dependencies" in groups
    dev_rule = groups["python-dev-dependencies"]
    assert dev_rule.get("matchManagers") == ["pep621"]
    assert "dependency-groups" in dev_rule.get("matchDepTypes", [])
    assert "python-production-dependencies" in groups
    prod_rule = groups["python-production-dependencies"]
    assert prod_rule.get("matchManagers") == ["pep621"]
    assert "dependencies" in prod_rule.get("matchDepTypes", [])

    assert "github-actions" in groups
    gha_rule = groups["github-actions"]
    assert gha_rule.get("matchManagers") == ["github-actions"]

    assert "rust-dependencies" in groups
    rust_rule = groups["rust-dependencies"]
    assert rust_rule.get("matchManagers") == ["cargo"]
    assert rust_rule.get("groupSlug") == "rust-deps"

    disabled_rules = [r for r in rules if isinstance(r, dict) and r.get("enabled") is False]
    assert any(
        r.get("matchManagers") == ["github-actions"] and "python" in r.get("matchPackageNames", [])
        for r in disabled_rules
    )
    assert any(
        r.get("matchManagers") == ["dockerfile"]
        and r.get("matchPackageNames") == ["python"]
        and r.get("matchUpdateTypes") == ["major", "minor"]
        for r in disabled_rules
    )

    dependabot_path = _repo_root() / ".github" / "dependabot.yml"
    with dependabot_path.open(encoding="utf-8") as f:
        dep_cfg = yaml.safe_load(f)

    for entry in dep_cfg.get("updates", []):
        assert entry.get("open-pull-requests-limit") == 0


def _load_mergify_config() -> dict[str, Any]:
    """Load and parse .mergify.yml from the repository root."""
    cfg_path = _repo_root() / ".mergify.yml"
    assert cfg_path.is_file(), f"Missing Mergify configuration at {cfg_path}"
    with cfg_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), ".mergify.yml must parse to a YAML mapping"
    return data


def test_mergify_queue_and_pull_request_rules() -> None:
    """Validate .mergify.yml queue rules, bot/human PR triggers, and branch cleanup (#630)."""
    raw = (_repo_root() / ".mergify.yml").read_text(encoding="utf-8")
    assert "https://docs.mergify.com/mergify-configuration-schema.json" in raw

    cfg = _load_mergify_config()
    queue_rules = cfg.get("queue_rules")
    assert isinstance(queue_rules, list)
    assert len(queue_rules) >= 1

    default_queue = queue_rules[0]
    assert isinstance(default_queue, dict)
    assert default_queue.get("name") == "default"
    assert default_queue.get("merge_method") == "squash"
    assert default_queue.get("update_method") == "rebase"

    for cond_key in ("queue_conditions", "merge_conditions"):
        conds = default_queue.get(cond_key)
        assert isinstance(conds, list)
        assert "base = main" in conds
        assert "-draft" in conds
        assert "-conflict" in conds
        assert "#changes-requested-reviews-by = 0" in conds
        assert "#review-threads-unresolved = 0" in conds
        assert "check-success = pre-commit.ci - pr" in conds
        assert "check-success = codecov/project" in conds
        assert "check-success = Code Quality & Gatekeeping" in conds

    # CodeRabbit skips Mergify queue draft PRs (.coderabbit.yaml ignore filters), gating queue entry (#730).
    assert "check-success = CodeRabbit" in default_queue["queue_conditions"]
    assert "check-success = CodeRabbit" not in default_queue["merge_conditions"]

    pr_rules = cfg.get("pull_request_rules")
    assert isinstance(pr_rules, list)
    by_name = {str(r.get("name")): r for r in pr_rules if isinstance(r, dict)}

    bot_rule = by_name["Automatic merge queue for Renovate and pre-commit.ci bot PRs"]
    bot_conds = bot_rule.get("conditions", [])
    assert any(
        isinstance(c, dict)
        and "author = renovate[bot]" in c.get("or", [])
        and "author = pre-commit-ci[bot]" in c.get("or", [])
        for c in bot_conds
    )
    assert bot_rule.get("actions", {}).get("queue", {}).get("name") == "default"

    human_rule = by_name["Automatic merge queue for approved or automerge-labeled PRs"]
    human_conds = human_rule.get("conditions", [])
    assert any(
        isinstance(c, dict)
        and "label = automerge" in c.get("or", [])
        and "#approved-reviews-by >= 1" in c.get("or", [])
        for c in human_conds
    )
    assert human_rule.get("actions", {}).get("queue", {}).get("name") == "default"
    assert all("delete_head_branch" not in r.get("actions", {}) for r in pr_rules if isinstance(r, dict))


def test_check_jsonschema_hooks_and_workflow_timeouts() -> None:
    """Validate check-jsonschema pre-commit hooks and workflow job timeout-minutes (#470, #630)."""
    repo = _repo_root()
    pre_commit_path = repo / ".pre-commit-config.yaml"
    with pre_commit_path.open(encoding="utf-8") as f:
        pc_data = yaml.safe_load(f)

    expected_hooks = {
        "check-github-workflows",
        "check-github-workflows-require-timeout",
        "check-dependabot",
        "check-github-issue-forms",
        "check-github-issue-config",
        "check-codecov",
        "check-renovate",
        "check-mergify",
        "check-readthedocs",
    }
    schema_repo = next(
        (r for r in pc_data.get("repos", []) if "python-jsonschema/check-jsonschema" in str(r.get("repo"))),
        None,
    )
    assert schema_repo is not None, "check-jsonschema repo must be configured in .pre-commit-config.yaml"
    assert schema_repo.get("rev"), "check-jsonschema repo must pin rev"
    actual_hooks = {h.get("id") for h in schema_repo.get("hooks", [])}
    assert actual_hooks == expected_hooks

    ci_skip = set(pc_data.get("ci", {}).get("skip", []))
    assert not (expected_hooks & ci_skip), "check-jsonschema hooks work offline and must not be in ci.skip"

    for wf_path in sorted((repo / ".github" / "workflows").glob("*.yml")):
        with wf_path.open(encoding="utf-8") as f:
            wf_data = yaml.safe_load(f)

        for job_name, job_def in wf_data.get("jobs", {}).items():
            timeout = job_def.get("timeout-minutes")
            assert isinstance(timeout, int), f"{wf_path.name}:{job_name} missing integer timeout-minutes"
            assert timeout > 0, f"{wf_path.name}:{job_name} timeout-minutes must be positive"


def test_pre_commit_meta_hooks_and_no_unused_symlinks_hook() -> None:
    """Validate pre-commit meta hooks (check-hooks-apply, check-useless-excludes, identity) (#471)."""
    pre_commit_path = _repo_root() / ".pre-commit-config.yaml"
    with pre_commit_path.open(encoding="utf-8") as f:
        pc_data = yaml.safe_load(f)

    repos = pc_data.get("repos", [])
    meta_repo = next((r for r in repos if r.get("repo") == "meta"), None)
    assert meta_repo is not None, "meta repo must be configured in .pre-commit-config.yaml"

    meta_hooks = {str(h.get("id")): h for h in meta_repo.get("hooks", []) if isinstance(h, dict)}
    assert set(meta_hooks) == {"check-hooks-apply", "check-useless-excludes", "identity"}
    assert meta_hooks["identity"].get("stages") == ["manual"]

    ci_skip = set(pc_data.get("ci", {}).get("skip", []))
    assert not (set(meta_hooks) & ci_skip), "meta hooks must not be in ci.skip"

    std_repo = next(
        (r for r in repos if "pre-commit/pre-commit-hooks" in str(r.get("repo"))),
        None,
    )
    assert std_repo is not None
    std_hook_ids = {h.get("id") for h in std_repo.get("hooks", []) if isinstance(h, dict)}
    assert "check-symlinks" not in std_hook_ids


def test_mergify_pr_size_labeler_rules_and_labels_taxonomy() -> None:
    """Validate PR size labeling rules in .mergify.yml and size:* entries in .github/labels.yml (#631)."""
    cfg = _load_mergify_config()
    pr_rules = cfg.get("pull_request_rules", [])
    by_name = {str(r.get("name")): r for r in pr_rules if isinstance(r, dict)}

    expected_size_rules = {
        "Label small pull requests (size:S)": ("size:S", ["#modified-lines < 100"]),
        "Label medium pull requests (size:M)": (
            "size:M",
            ["#modified-lines >= 100", "#modified-lines < 500"],
        ),
        "Label large pull requests (size:L)": (
            "size:L",
            ["#modified-lines >= 500", "#modified-lines < 1000"],
        ),
        "Label extra-large pull requests (size:XL)": ("size:XL", ["#modified-lines >= 1000"]),
    }
    all_size_labels = {"size:S", "size:M", "size:L", "size:XL"}

    for rule_name, (target_label, expected_conds) in expected_size_rules.items():
        assert rule_name in by_name, f"Missing Mergify size rule: {rule_name}"
        rule = by_name[rule_name]
        conds = rule.get("conditions", [])
        assert "-closed" in conds
        for cond in expected_conds:
            assert cond in conds

        label_action = rule.get("actions", {}).get("label", {})
        assert label_action.get("add") == [target_label]
        assert set(label_action.get("remove", [])) == all_size_labels - {target_label}

    labels_path = _repo_root() / ".github" / "labels.yml"
    with labels_path.open(encoding="utf-8") as f:
        labels_data = yaml.safe_load(f)

    defined_labels = {str(item.get("name")) for item in labels_data if isinstance(item, dict)}
    assert all_size_labels.issubset(defined_labels)
