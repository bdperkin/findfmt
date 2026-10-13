"""Unit tests for symbolic link tokenization and syntax parsing."""

from __future__ import annotations

from findfmt.parsers.symlink_parser import _strip_quotes, parse_symlink_target


def test_strip_quotes() -> None:
    """Verify enclosing quote removal handling."""
    assert _strip_quotes('"hello"') == "hello"
    assert _strip_quotes("'world'") == "world"
    assert _strip_quotes("no_quotes") == "no_quotes"
    assert _strip_quotes("\"mismatched'") == "\"mismatched'"
    assert _strip_quotes('""') == ""
    assert _strip_quotes("x") == "x"
    assert _strip_quotes("") == ""


def test_parse_symlink_target_standard() -> None:
    """Verify standard link -> target syntax parsing."""
    name, is_link, target = parse_symlink_target("lib.so -> lib.so.1.2.3")
    assert name == "lib.so"
    assert is_link is True
    assert target == "lib.so.1.2.3"


def test_parse_symlink_target_quoted() -> None:
    """Verify quoted link names and target paths."""
    name, is_link, target = parse_symlink_target("\"my link\" -> 'my target'")
    assert name == "my link"
    assert is_link is True
    assert target == "my target"


def test_parse_symlink_target_regular_file() -> None:
    """Verify regular non-symlink paths return False and None target."""
    name, is_link, target = parse_symlink_target("regular_file.txt")
    assert name == "regular_file.txt"
    assert is_link is False
    assert target is None


def test_parse_symlink_target_embedded_arrow_without_spaces() -> None:
    """Verify arrow without spaces is treated as regular path."""
    name, is_link, target = parse_symlink_target("function->result.txt")
    assert name == "function->result.txt"
    assert is_link is False
    assert target is None


def test_parse_symlink_target_missing_parts() -> None:
    """Verify incomplete or empty target yields regular file."""
    name, is_link, target = parse_symlink_target("broken -> ")
    assert name == "broken ->"
    assert is_link is False
    assert target is None

    name2, is_link2, target2 = parse_symlink_target(" -> target")
    assert name2 == "-> target"
    assert is_link2 is False
    assert target2 is None
