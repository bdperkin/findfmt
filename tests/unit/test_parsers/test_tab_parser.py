"""Unit tests for tab-indented and outline hierarchy parsing."""

from __future__ import annotations

from findfmt.parsers.tab_parser import parse_tab_outline


def test_parse_tab_outline_simple_tabs() -> None:
    """Verify standard tab-indented nested hierarchy."""
    lines = [
        "src",
        "\tfindfmt",
        "\t\tmain.py",
        "\t\tutils.py",
        "tests",
        "\ttest_main.py",
        "README.md",
    ]
    entries = list(parse_tab_outline(lines))
    assert len(entries) == 7

    assert entries[0].path_str == "src"
    assert entries[0].is_dir is True

    assert entries[1].path_str == "src/findfmt"
    assert entries[1].is_dir is True

    assert entries[2].path_str == "src/findfmt/main.py"
    assert entries[2].is_dir is False

    assert entries[3].path_str == "src/findfmt/utils.py"
    assert entries[3].is_dir is False

    assert entries[4].path_str == "tests"
    assert entries[4].is_dir is True

    assert entries[5].path_str == "tests/test_main.py"
    assert entries[5].is_dir is False

    assert entries[6].path_str == "README.md"
    assert entries[6].is_dir is False


def test_parse_tab_outline_spaces_and_comments() -> None:
    """Verify space-indented outline with comments and blank lines."""
    lines = [
        "# Project Outline",
        "project/",
        "  config",
        "    settings.toml",
        "",
        "  # docs folder",
        "  docs/",
        "    index.md",
    ]
    entries = list(parse_tab_outline(lines))
    paths = [e.path_str for e in entries]
    assert paths == [
        "project",
        "project/config",
        "project/config/settings.toml",
        "project/docs",
        "project/docs/index.md",
    ]
    assert entries[0].is_dir is True
    assert entries[1].is_dir is True
    assert entries[2].is_dir is False
    assert entries[3].is_dir is True
    assert entries[4].is_dir is False


def test_parse_tab_outline_tree_glyphs_and_symlinks() -> None:
    """Verify outline containing tree drawing glyphs and embedded symlinks."""
    lines = [
        "root",
        "├── child1",
        "│   └── lib.so -> lib.so.1",
        "└── child2",
        "    └── script.sh",
    ]
    entries = list(parse_tab_outline(lines))
    assert len(entries) == 5

    sym_entry = entries[2]
    assert sym_entry.path_str == "root/child1/lib.so"
    assert sym_entry.is_symlink is True
    assert sym_entry.symlink_target == "lib.so.1"
    assert sym_entry.is_dir is False


def test_parse_tab_outline_malformed_indentation_transitions() -> None:
    """Verify graceful handling when dedenting to intermediate unaligned columns."""
    lines = [
        "root",
        "        level2",
        "    level1_unaligned",
        "        subfile.txt",
    ]
    entries = list(parse_tab_outline(lines))
    assert len(entries) == 4
    assert entries[0].path_str == "root"
    assert entries[1].path_str == "root/level2"
    assert entries[2].path_str == "root/level1_unaligned"
    assert entries[3].path_str == "root/level1_unaligned/subfile.txt"


def test_parse_tab_outline_empty_and_no_items() -> None:
    """Verify empty input handling."""
    assert list(parse_tab_outline([])) == []
    assert list(parse_tab_outline(["", "  ", "# comment only"])) == []
    assert list(parse_tab_outline(["///", "  ///  "])) == []
