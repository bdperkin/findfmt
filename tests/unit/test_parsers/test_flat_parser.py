"""Unit tests for flat newline-delimited path listings."""

from __future__ import annotations

from findfmt.parsers.flat_parser import ParsedEntry, parse_flat_listing


def test_parse_flat_listing_standard() -> None:
    """Verify flat parsing of regular files."""
    lines = [
        "src/findfmt/__init__.py",
        "src/findfmt/main.py",
        "tests/test_main.py",
    ]
    entries = list(parse_flat_listing(lines))
    assert len(entries) == 3
    assert [e.path_str for e in entries] == lines
    assert all(not e.is_dir for e in entries)
    assert all(not e.is_symlink for e in entries)


def test_parse_flat_listing_normalized_and_comments() -> None:
    """Verify leading ./ stripping, comment skipping, and whitespace ignoring."""
    lines = [
        "# Initial comment",
        "",
        "   ",
        "./src/app.py",
        "docs/guide.md",
        "  # Inline comment line",
        "./sub/nested.txt",
    ]
    entries = list(parse_flat_listing(lines))
    assert len(entries) == 3
    assert [e.path_str for e in entries] == [
        "src/app.py",
        "docs/guide.md",
        "sub/nested.txt",
    ]


def test_parse_flat_listing_directories_and_symlinks() -> None:
    """Verify directory slashes and symlink target syntax parsing."""
    lines = [
        "src/components/",
        "docs\\architecture\\",
        "lib/libfoo.so -> libfoo.so.1",
        "./",
        ".",
        "///",
    ]
    entries = list(parse_flat_listing(lines))
    assert len(entries) == 3

    assert entries[0] == ParsedEntry(
        path_str="src/components",
        is_symlink=False,
        symlink_target=None,
        is_dir=True,
    )
    assert entries[1] == ParsedEntry(
        path_str="docs\\architecture",
        is_symlink=False,
        symlink_target=None,
        is_dir=True,
    )
    assert entries[2] == ParsedEntry(
        path_str="lib/libfoo.so",
        is_symlink=True,
        symlink_target="libfoo.so.1",
        is_dir=False,
    )


def test_parse_flat_listing_ignores_tree_summary_trailers() -> None:
    """Verify tree summary trailers are ignored in flat mode (e.g. empty tree output) (#459)."""
    lines = [
        ".",
        "src/main.py",
        "",
        "0 directories, 1 file",
        "1 directory, 0 files",
    ]
    entries = list(parse_flat_listing(lines))
    assert [e.path_str for e in entries] == ["src/main.py"]


def test_parse_flat_listing_nul_delimited_embedded_newlines() -> None:
    """Verify NUL-delimited records preserve embedded newlines, spaces, and # prefixes (#461)."""
    raw_stream = [
        "./dir/line1\nline2.py\0  leading_space.py\0#hash_file.py\0a -> b.py\0sub/dir/\0.\0\0",
    ]
    entries = list(parse_flat_listing(raw_stream))
    assert entries == [
        ParsedEntry(path_str="dir/line1\nline2.py", is_symlink=False, symlink_target=None),
        ParsedEntry(path_str="  leading_space.py", is_symlink=False, symlink_target=None),
        ParsedEntry(path_str="#hash_file.py", is_symlink=False, symlink_target=None),
        ParsedEntry(path_str="a -> b.py", is_symlink=False, symlink_target=None),
        ParsedEntry(path_str="sub/dir", is_symlink=False, symlink_target=None, is_dir=True),
    ]

    pre_split = ["./first\nfile.py", "  second\rfile.py", "./", "///"]
    entries_pre_split = list(parse_flat_listing(pre_split))
    assert entries_pre_split == [
        ParsedEntry(path_str="first\nfile.py", is_symlink=False, symlink_target=None),
        ParsedEntry(path_str="  second\rfile.py", is_symlink=False, symlink_target=None),
    ]
