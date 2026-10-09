"""Unit tests for line drawing glyph sets and console box styles."""

from __future__ import annotations

from rich.box import Box

from findfmt.formatters.glyphs import CP437_BOX, TREE_GUIDE_SETS, resolve_tree_guides


def test_tree_guide_sets_completeness() -> None:
    """Verify that all expected guide line sets are defined and formatted."""
    assert "unicode" in TREE_GUIDE_SETS
    assert "ansi" in TREE_GUIDE_SETS
    assert "cp437" in TREE_GUIDE_SETS
    assert "none" in TREE_GUIDE_SETS

    for name, guides in TREE_GUIDE_SETS.items():
        assert len(guides) == 4, f"Guide set '{name}' must contain exactly 4 elements."
        assert all(isinstance(g, str) for g in guides)

    assert TREE_GUIDE_SETS["none"] == ("", "", "", "")
    assert TREE_GUIDE_SETS["unicode"] == ("    ", "│   ", "├── ", "└── ")
    assert "\x1b(0" in TREE_GUIDE_SETS["ansi"][1]
    assert "\xb3" in TREE_GUIDE_SETS["cp437"][1]


def test_cp437_box_instance() -> None:
    """Verify that CP437_BOX is a valid rich Box instance."""
    assert isinstance(CP437_BOX, Box)


def test_resolve_tree_guides_default() -> None:
    """Verify default returns Unicode guide characters."""
    assert resolve_tree_guides() == TREE_GUIDE_SETS["unicode"]


def test_resolve_tree_guides_no_indent_precedence() -> None:
    """Verify no_indent takes precedence over ansi and cp437."""
    assert resolve_tree_guides(no_indent=True) == TREE_GUIDE_SETS["none"]
    assert resolve_tree_guides(no_indent=True, ansi_lines=True) == TREE_GUIDE_SETS["none"]
    assert resolve_tree_guides(no_indent=True, cp437=True) == TREE_GUIDE_SETS["none"]
    assert (
        resolve_tree_guides(no_indent=True, ansi_lines=True, cp437=True) == TREE_GUIDE_SETS["none"]
    )


def test_resolve_tree_guides_ansi_lines() -> None:
    """Verify ansi_lines returns ANSI escapes and precedes cp437."""
    assert resolve_tree_guides(ansi_lines=True) == TREE_GUIDE_SETS["ansi"]
    assert resolve_tree_guides(ansi_lines=True, cp437=True) == TREE_GUIDE_SETS["ansi"]


def test_resolve_tree_guides_cp437() -> None:
    """Verify cp437 returns CP437 character set."""
    assert resolve_tree_guides(cp437=True) == TREE_GUIDE_SETS["cp437"]
