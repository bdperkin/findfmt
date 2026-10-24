"""Keep the "Upgrading to 1.1" guide in step with the changelog and discoverable (#499)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "source" / "guides" / "upgrading.md"
GUIDE_URL = "https://bdperkin.github.io/findfmt/guides/upgrading.html"


def _unreleased_breaking_changes() -> str:
    """Return the ``### Breaking Changes`` text of the changelog's ``[Unreleased]`` section."""
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = changelog.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0]
    assert "### Breaking Changes" in unreleased, "[Unreleased] must list its breaking changes"
    return unreleased.split("### Breaking Changes", 1)[1].split("\n### ", 1)[0]


def test_upgrade_guide_is_in_the_guides_toctree() -> None:
    """The guide exists and is reachable from the Sphinx navigation."""
    assert GUIDE.is_file()
    index = (GUIDE.parent / "index.md").read_text(encoding="utf-8")
    toctree = index.split("```{toctree}", 1)[1].split("```", 1)[0]
    assert "upgrading" in toctree.split()


def test_upgrade_guide_covers_every_breaking_change() -> None:
    """Every issue cited under [Unreleased] -> Breaking Changes is explained in the guide."""
    cited = set(re.findall(r"#(\d+)", _unreleased_breaking_changes()))
    assert cited, "Breaking Changes must cite issue numbers"
    guide = GUIDE.read_text(encoding="utf-8")
    missing = sorted(n for n in cited if f"#{n}" not in guide)
    assert not missing, f"Breaking changes missing from the upgrade guide: {missing}"


def test_upgrade_guide_is_linked_from_changelog_and_readme() -> None:
    """The changelog's [Unreleased] section and the README point readers to the guide."""
    unreleased = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").split("## [Unreleased]", 1)[1]
    assert GUIDE_URL in unreleased.split("\n## [", 1)[0]
    assert GUIDE_URL in (ROOT / "README.md").read_text(encoding="utf-8")
