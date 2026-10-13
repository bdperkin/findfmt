"""Unit tests for CLI input options (--from-file, --fromfile, and --offline)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from findfmt.cli import app

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
