"""Unit tests for CLI input options (--from-file, --fromfile, and --offline)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from findfmt.cli import app
from findfmt.exceptions import ParserError

runner = CliRunner()


def _normalize_lines(output: str) -> list[str]:
    """Strip whitespace and normalize path separators for cross-platform assertions."""
    return [line.strip().replace("\\", "/") for line in output.strip().splitlines() if line.strip()]


def test_cli_from_file_flat(tmp_path: Path) -> None:
    """Verify --from-file ingests flat path listings correctly."""
    input_file = tmp_path / "listing.txt"
    input_file.write_text("src/main.py\nsrc/utils.py\nREADME.md\n")

    result = runner.invoke(app, ["--from-file", str(input_file), "--no-pager"])
    assert result.exit_code == 0
    assert _normalize_lines(result.output) == [
        "README.md",
        "src/main.py",
        "src/utils.py",
    ]


def test_cli_fromfile_alias(tmp_path: Path) -> None:
    """Verify --fromfile alias functions identically to --from-file."""
    input_file = tmp_path / "listing.txt"
    input_file.write_text("a.py\nb.txt\n")

    result = runner.invoke(app, ["--fromfile", str(input_file), "--no-pager"])
    assert result.exit_code == 0
    assert _normalize_lines(result.output) == ["a.py", "b.txt"]


def test_cli_from_file_stdin() -> None:
    """Verify --from-file - consumes standard input."""
    data = "first.py\nsecond.txt\nthird.json\n"
    result = runner.invoke(app, ["--from-file", "-", "--no-pager"], input=data)
    assert result.exit_code == 0
    assert _normalize_lines(result.output) == [
        "first.py",
        "second.txt",
        "third.json",
    ]


def test_cli_from_file_outline_and_tree(tmp_path: Path) -> None:
    """Verify outline hierarchy reconstruction and tree rendering."""
    outline_file = tmp_path / "outline.txt"
    outline_file.write_text("project\n\tsrc\n\t\tmain.py\n\t\tutils.py\n\tREADME.md\n")

    result = runner.invoke(app, ["--from-file", str(outline_file), "--tree", "--no-pager"])
    assert result.exit_code == 0
    assert "main.py" in result.output
    assert "utils.py" in result.output
    assert "README.md" in result.output


def test_cli_from_file_symlink_and_offline(tmp_path: Path) -> None:
    """Verify symlink target ingestion and --offline flag enforcement."""
    manifest = tmp_path / "manifest.txt"
    manifest.write_text("lib/libfoo.so -> libfoo.so.1.0.0\napp/main.py\n")

    result = runner.invoke(
        app,
        ["--from-file", str(manifest), "--offline", "--format", "json", "--no-pager"],
    )
    assert result.exit_code == 0
    assert "libfoo.so.1.0.0" in result.output
    assert "text/x-python" in result.output


def test_cli_from_file_missing_error() -> None:
    """Verify validation error when input file does not exist."""
    result = runner.invoke(app, ["--from-file", "nonexistent_file_xyz.txt"])
    assert result.exit_code == 2
    assert "not found" in result.output.lower()


def test_cli_from_file_with_filtering_and_sorting(tmp_path: Path) -> None:
    """Verify filtering and sorting flags apply properly to ingested files."""
    listing = tmp_path / "files.txt"
    listing.write_text("file10.py\nfile2.py\nfile1.txt\n")

    # Filter by tag python
    result_tag = runner.invoke(
        app,
        ["--from-file", str(listing), "-t", "python", "--sort", "version", "--no-pager"],
    )
    assert result_tag.exit_code == 0
    assert _normalize_lines(result_tag.output) == ["file2.py", "file10.py"]


def test_cli_from_file_non_utf8_round_trip(tmp_path: Path) -> None:
    """Verify non-UTF-8 file names round-trip unchanged from stdin and files without traceback."""
    raw_input = b"bad\xff.txt\nraw\xe9.py\n"

    # 1. From stdin (--from-file -)
    res_stdin = runner.invoke(
        app,
        ["--from-file", "-", "--offline", "-0", "--no-pager"],
        input=raw_input,
    )
    assert res_stdin.exit_code == 0
    assert res_stdin.exception is None
    assert "Traceback" not in res_stdin.output
    assert res_stdin.stdout_bytes == b"bad\xff.txt\x00raw\xe9.py\x00"

    # 2. From external file (--from-file <path>)
    listing_file = tmp_path / "non_utf8_listing.txt"
    listing_file.write_bytes(raw_input)
    res_file = runner.invoke(
        app,
        ["--from-file", str(listing_file), "--offline", "-0", "--no-pager"],
    )
    assert res_file.exit_code == 0
    assert res_file.exception is None
    assert "Traceback" not in res_file.output
    assert res_file.stdout_bytes == b"bad\xff.txt\x00raw\xe9.py\x00"

    # 3. ParserError raised during output delivery exits 2 cleanly with no traceback
    with patch(
        "findfmt.parsers.engine._read_lines",
        side_effect=ParserError("Cannot read input from 'bad.txt': Permission denied"),
    ):
        res_err = runner.invoke(app, ["--from-file", "-", "--no-pager"], input=b"")

    assert res_err.exit_code == 2
    assert "Cannot read input from 'bad.txt'" in res_err.stderr
    assert "Traceback" not in res_err.output


def test_cli_from_file_ascii_and_unicode_tree_fixtures(tmp_path: Path) -> None:
    """Verify ASCII and Unicode tree fixtures strip branches and ignore summary trailers (#459)."""
    ascii_fixture = tmp_path / "ascii_tree.txt"
    ascii_fixture.write_text(
        ".\n|-- src\n|   |-- app.py\n|   `-- util.py\n`-- README.md\n\n1 directory, 3 files\n",
        encoding="utf-8",
    )
    res_ascii = runner.invoke(
        app,
        ["--from-file", str(ascii_fixture), "--offline", "--no-pager"],
    )
    assert res_ascii.exit_code == 0
    assert _normalize_lines(res_ascii.output) == [
        "README.md",
        "src/app.py",
        "src/util.py",
    ]

    unicode_fixture = tmp_path / "unicode_tree.txt"
    unicode_fixture.write_text(
        ".\n├── src\n│   ├── app.py\n│   └── util.py\n└── README.md\n\n1 directory, 3 files\n",
        encoding="utf-8",
    )
    res_unicode = runner.invoke(
        app,
        ["--from-file", str(unicode_fixture), "--offline", "--no-pager"],
    )
    assert res_unicode.exit_code == 0
    assert _normalize_lines(res_unicode.output) == [
        "README.md",
        "src/app.py",
        "src/util.py",
    ]
