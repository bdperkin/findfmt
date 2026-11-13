"""Unit tests for symbolic link tokenization and syntax parsing."""

from __future__ import annotations

from findfmt.parsers.symlink_parser import _strip_quotes, parse_symlink_target


def test_strip_quotes() -> None:
    """Verify enclosing quote removal and interior quote/space preservation."""
    assert _strip_quotes('"hello"') == "hello"
    assert _strip_quotes("'world'") == "world"
    assert _strip_quotes("no_quotes") == "no_quotes"
    assert _strip_quotes("\"mismatched'") == "\"mismatched'"
    assert _strip_quotes('""') == ""
    assert _strip_quotes("x") == "x"
    assert _strip_quotes("") == ""
    assert _strip_quotes('"  spaced  "') == "  spaced  "
    assert _strip_quotes("'file \"with\" quotes.txt'") == 'file "with" quotes.txt'
    assert _strip_quotes('"file \\"with\\" quotes.txt"') == 'file "with" quotes.txt'
    assert _strip_quotes('"a"b"c"') == '"a"b"c"'
    assert _strip_quotes('"abc\\"') == '"abc\\"'


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


def test_name_containing_arrow() -> None:
    """Verify symlink names and targets containing ' -> ' delimiters (#355)."""
    # Unquoted link name containing ' -> ' splits on the last unquoted arrow
    name, is_link, target = parse_symlink_target("a -> b.txt -> target")
    assert name == "a -> b.txt"
    assert is_link is True
    assert target == "target"

    # ls -l style quoted link name containing ' -> '
    name2, is_link2, target2 = parse_symlink_target("'a -> b.txt' -> target")
    assert name2 == "a -> b.txt"
    assert is_link2 is True
    assert target2 == "target"

    # Quoted target containing ' -> '
    name3, is_link3, target3 = parse_symlink_target("link.txt -> 'target -> dest.txt'")
    assert name3 == "link.txt"
    assert is_link3 is True
    assert target3 == "target -> dest.txt"

    # Both link name and target quoted and containing ' -> '
    name4, is_link4, target4 = parse_symlink_target('"a -> b.txt" -> "c -> d.txt"')
    assert name4 == "a -> b.txt"
    assert is_link4 is True
    assert target4 == "c -> d.txt"

    # Single quoted filename containing ' -> ' without a target is a regular file
    name5, is_link5, target5 = parse_symlink_target("'a -> b.txt'")
    assert name5 == "a -> b.txt"
    assert is_link5 is False
    assert target5 is None


def test_parse_symlink_target_preserves_quotes_and_special_chars() -> None:
    """Verify embedded, escaped, and unmatched quotes in symlink filenames (#355)."""
    # Unquoted filename containing literal double quotes
    name, is_link, target = parse_symlink_target('file"quote".txt -> target"quote".txt')
    assert name == 'file"quote".txt'
    assert is_link is True
    assert target == 'target"quote".txt'

    # Escaped quotes inside outer quotes
    name2, is_link2, target2 = parse_symlink_target("\"a \\\"->\\\" b.txt\" -> 'c \\'->\\' d.txt'")
    assert name2 == 'a "->" b.txt'
    assert is_link2 is True
    assert target2 == "c '->' d.txt"

    # Unmatched apostrophe in unquoted link name and target
    name3, is_link3, target3 = parse_symlink_target("bob's_link.txt -> alice's_target.txt")
    assert name3 == "bob's_link.txt"
    assert is_link3 is True
    assert target3 == "alice's_target.txt"

    # Single unmatched apostrophe in link name only
    name4, is_link4, target4 = parse_symlink_target("bob's_link.txt -> target.txt")
    assert name4 == "bob's_link.txt"
    assert is_link4 is True
    assert target4 == "target.txt"


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

    name3, is_link3, target3 = parse_symlink_target('"" -> target')
    assert name3 == '"" -> target'
    assert is_link3 is False
    assert target3 is None

    name4, is_link4, target4 = parse_symlink_target('link -> ""')
    assert name4 == 'link -> ""'
    assert is_link4 is False
    assert target4 is None
