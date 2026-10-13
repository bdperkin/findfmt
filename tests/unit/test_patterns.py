"""Unit tests for wildcard and glob pattern compiler and matcher engine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from findfmt.models import FileInfo, TraversalConfig
from findfmt.patterns import (
    PatternMatcher,
    _apply_ignore_case,
    compile_pattern_spec,
    create_pattern_matcher,
    matches_pattern_criteria,
    split_pattern_alternations,
)


def test_split_pattern_alternations() -> None:
    """Verify split_pattern_alternations handles simple, pipe, bracket, and empty patterns."""
    assert split_pattern_alternations("") == []
    assert split_pattern_alternations("*.py") == ["*.py"]
    assert split_pattern_alternations("*.py|*.md") == ["*.py", "*.md"]
    assert split_pattern_alternations("*.py|*.md|*.rst") == ["*.py", "*.md", "*.rst"]
    assert split_pattern_alternations("  *.py  |  *.md  ") == ["*.py", "*.md"]
    assert split_pattern_alternations("[a|b].txt") == ["[a|b].txt"]
    assert split_pattern_alternations("[a|b].txt|*.doc") == ["[a|b].txt", "*.doc"]
    assert split_pattern_alternations("|||") == []


def test_compile_pattern_spec_empty_and_none() -> None:
    """Verify compile_pattern_spec returns None for empty pattern inputs."""
    assert compile_pattern_spec(()) is None
    assert compile_pattern_spec([]) is None
    assert compile_pattern_spec(["", "|||"]) is None


def test_compile_pattern_spec_case_sensitivity() -> None:
    """Verify compile_pattern_spec compiles with and without case sensitivity."""
    spec_sens = compile_pattern_spec(["*.py"], ignore_case=False)
    assert spec_sens is not None
    assert spec_sens.match_file("foo.py")
    assert not spec_sens.match_file("FOO.PY")

    spec_insens = compile_pattern_spec(["*.py"], ignore_case=True)
    assert spec_insens is not None
    assert spec_insens.match_file("foo.py")
    assert spec_insens.match_file("FOO.PY")
    assert spec_insens.match_file("Foo.Py")

    # Test mock pattern without regex attribute
    mock_spec = MagicMock()
    mock_pat = MagicMock(spec=[])
    mock_spec.patterns = [mock_pat]
    _apply_ignore_case(mock_spec)


def test_pattern_matcher_from_config() -> None:
    """Verify PatternMatcher can be created from TraversalConfig."""
    cfg = TraversalConfig(
        include_patterns=("*.py",),
        exclude_patterns=("*.tmp",),
        ignore_case=True,
        match_dirs=True,
    )
    matcher = create_pattern_matcher(cfg)
    assert matcher.has_includes
    assert matcher.has_excludes
    assert matcher.ignore_case
    assert matcher.match_dirs


def test_pattern_matcher_relative_to_base_root() -> None:
    """Verify to_posix handles paths relative to base_root and fallback paths."""
    matcher = PatternMatcher(include_patterns=("*.py",))
    base = Path("/repo")
    path_inside = Path("/repo/src/app.py")
    path_outside = Path("/other/app.py")

    rel_in, name_in = matcher.to_posix(path_inside, base)
    assert rel_in == "src/app.py"
    assert name_in == "app.py"

    rel_out, name_out = matcher.to_posix(path_outside, base)
    assert rel_out == "/other/app.py"
    assert name_out == "app.py"


def test_pattern_matcher_should_exclude() -> None:
    """Verify should_exclude handles empty excludes, file excludes, and directory excludes."""
    matcher_none = PatternMatcher()
    assert not matcher_none.should_exclude("foo.tmp", is_dir=False)
    assert not matcher_none.should_exclude("build", is_dir=True)

    matcher = PatternMatcher(exclude_patterns=("*.tmp", "build/", "dist", "sub/temp/"))
    assert matcher.should_exclude("foo.tmp", is_dir=False)
    assert not matcher.should_exclude("foo.py", is_dir=False)

    # Trailing slash pattern matches directory only
    assert matcher.should_exclude("build", is_dir=True)
    assert not matcher.should_exclude("build", is_dir=False)

    # Without trailing slash matches both dir and file
    assert matcher.should_exclude("dist", is_dir=True)
    assert matcher.should_exclude("dist", is_dir=False)

    # Nested directory path exclusion
    assert matcher.should_exclude("sub/temp", is_dir=True)
    assert not matcher.should_exclude("other/temp", is_dir=True)


def test_pattern_matcher_matches_file() -> None:
    """Verify matches_file evaluates exclusions, inclusions, inherited matches, and operators."""
    matcher = PatternMatcher(
        include_patterns=("*.py", "docs/*.rst", "src/**/*.ts", "[0-9].txt", "[!a-z].dat"),
        exclude_patterns=("test_*.py",),
    )
    # File matching exclusion
    assert not matcher.matches_file("test_main.py")

    # Regular inclusion matches
    assert matcher.matches_file("main.py")
    assert matcher.matches_file("docs/guide.rst")
    assert matcher.matches_file("src/nested/deep/app.ts")
    assert matcher.matches_file("1.txt")
    assert matcher.matches_file("9.dat")
    assert not matcher.matches_file("a.dat")
    assert not matcher.matches_file("styles.css")

    # Inherited match bypasses include_patterns but still respects exclude_patterns
    assert matcher.matches_file("styles.css", inherited_match=True)
    assert not matcher.matches_file("test_main.py", inherited_match=True)

    # When no include patterns are configured
    matcher_no_inc = PatternMatcher(exclude_patterns=("*.bak",))
    assert matcher_no_inc.matches_file("random.txt")
    assert not matcher_no_inc.matches_file("backup.bak")


def test_pattern_matcher_matches_dir() -> None:
    """Verify matches_dir evaluates include patterns against directory paths and names."""
    matcher_empty = PatternMatcher()
    assert matcher_empty.matches_dir("any_dir")

    matcher = PatternMatcher(include_patterns=("tests*", "src/", "docs/**/*.md"))
    assert matcher.matches_dir("tests")
    assert matcher.matches_dir("tests/")
    assert matcher.matches_dir("src")
    assert matcher.matches_dir("src/")
    assert not matcher.matches_dir("dist")


def test_pattern_matcher_should_inherit_match() -> None:
    """Verify should_inherit_match respects match_dirs, parent_inherited, and dir matches."""
    matcher_off = PatternMatcher(include_patterns=("tests*",), match_dirs=False)
    assert not matcher_off.should_inherit_match("tests")
    assert not matcher_off.should_inherit_match("tests", parent_inherited=True)

    matcher_on = PatternMatcher(include_patterns=("tests*",), match_dirs=True)
    assert matcher_on.should_inherit_match("other", parent_inherited=True)
    assert matcher_on.should_inherit_match("tests")
    assert not matcher_on.should_inherit_match("other")


def test_matches_pattern_criteria_dirs_only(tmp_path: Path) -> None:
    """Verify matches_pattern_criteria behavior when dirs_only is enabled."""
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    info = FileInfo(
        path=dir_path,
        relative_path=Path("test_dir"),
        tags=frozenset({"directory"}),
        shebang=None,
        mime_type=None,
        is_executable=False,
        is_symlink=False,
        size_bytes=4096,
    )

    # No patterns configured
    cfg_empty = TraversalConfig(dirs_only=True)
    assert matches_pattern_criteria(info, cfg_empty)

    # Excluded directory
    cfg_ex = TraversalConfig(dirs_only=True, exclude_patterns=("test_*",))
    assert not matches_pattern_criteria(info, cfg_ex)

    # Included directory with match_dirs=True
    cfg_inc = TraversalConfig(dirs_only=True, include_patterns=("test_*",), match_dirs=True)
    assert matches_pattern_criteria(info, cfg_inc)

    # Directory with match_dirs=False allows directory descent
    cfg_no_md = TraversalConfig(dirs_only=True, include_patterns=("other_*",), match_dirs=False)
    assert matches_pattern_criteria(info, cfg_no_md)

    # Missed directory with match_dirs=True
    cfg_miss = TraversalConfig(dirs_only=True, include_patterns=("other_*",), match_dirs=True)
    assert not matches_pattern_criteria(info, cfg_miss)
    assert matches_pattern_criteria(info, cfg_miss, inherited_match=True)
