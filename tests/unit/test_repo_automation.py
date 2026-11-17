"""Unit tests for repository automation configurations (.coderabbit.yaml, etc.)."""

from __future__ import annotations

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
    assert auto_review.get("drafts") is False
    assert auto_review.get("base_branches") == ["main"]

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
