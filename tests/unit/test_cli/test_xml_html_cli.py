"""CLI integration tests for XML and HTML formatting flags.

Covers: -X, -H, --intro, --outro, -T, --nolinks.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from findfmt.cli import app

if TYPE_CHECKING:
    from pathlib import Path


def test_cli_xml_flag(sample_repo: Path) -> None:
    """Verify -X flag produces well-formed XML directory tree."""
    runner = CliRunner()
    res = runner.invoke(app, ["-X", str(sample_repo)])
    assert res.exit_code == 0
    assert res.stdout.startswith("<?xml")
    parsed = ET.fromstring(res.stdout)
    assert parsed.tag == "tree"
    assert parsed.find("directory") is not None


def test_cli_format_xml(sample_repo: Path) -> None:
    """Verify --format xml produces valid XML output."""
    runner = CliRunner()
    res = runner.invoke(app, ["--format", "xml", str(sample_repo)])
    assert res.exit_code == 0
    assert res.stdout.startswith("<?xml")
    parsed = ET.fromstring(res.stdout)
    assert parsed.tag == "tree"


def test_cli_html_flag(sample_repo: Path) -> None:
    """Verify -H flag produces semantic HTML5 output with hyperlinks."""
    runner = CliRunner()
    res = runner.invoke(app, ["-H", "http://localhost:8000", str(sample_repo)])
    assert res.exit_code == 0
    assert "<!DOCTYPE html>" in res.stdout
    assert "<title>Directory Tree</title>" in res.stdout
    assert '<a href="http://localhost:8000' in res.stdout


def test_cli_format_html(sample_repo: Path) -> None:
    """Verify --format html produces semantic HTML5 output."""
    runner = CliRunner()
    res = runner.invoke(app, ["--format", "html", str(sample_repo)])
    assert res.exit_code == 0
    assert "<!DOCTYPE html>" in res.stdout
    assert "<title>Directory Tree</title>" in res.stdout


def test_cli_html_title(sample_repo: Path) -> None:
    """Verify -T / --title customizes title and h1 in HTML mode."""
    runner = CliRunner()
    res = runner.invoke(
        app,
        ["-H", "http://localhost:8000", "-T", "My Repository Tree", str(sample_repo)],
    )
    assert res.exit_code == 0
    assert "<title>My Repository Tree</title>" in res.stdout
    assert "<h1>My Repository Tree</h1>" in res.stdout


def test_cli_html_intro_outro(sample_repo: Path, tmp_path: Path) -> None:
    """Verify --intro and --outro insert custom HTML fragments."""
    intro_file = tmp_path / "intro.html"
    intro_file.write_text("<header>Project Header</header>\n", encoding="utf-8")
    outro_file = tmp_path / "outro.html"
    outro_file.write_text("<footer>Project Footer</footer>\n", encoding="utf-8")

    runner = CliRunner()
    res = runner.invoke(
        app,
        [
            "-H",
            "http://localhost:8000",
            "--intro",
            str(intro_file),
            "--outro",
            str(outro_file),
            str(sample_repo),
        ],
    )
    assert res.exit_code == 0
    assert "<header>Project Header</header>" in res.stdout
    assert "<footer>Project Footer</footer>" in res.stdout


def test_cli_html_intro_missing_file(sample_repo: Path, tmp_path: Path) -> None:
    """Verify missing --intro file exits with code 2 and informative error message."""
    missing_intro = tmp_path / "nonexistent_intro.html"
    runner = CliRunner()
    res = runner.invoke(
        app,
        ["-H", "http://localhost:8000", "--intro", str(missing_intro), str(sample_repo)],
    )
    assert res.exit_code == 2
    assert "Error: Intro file" in res.stderr
    assert "not found" in res.stderr


def test_cli_html_outro_missing_file(sample_repo: Path, tmp_path: Path) -> None:
    """Verify missing --outro file exits with code 2 and informative error message."""
    missing_outro = tmp_path / "nonexistent_outro.html"
    runner = CliRunner()
    res = runner.invoke(
        app,
        ["-H", "http://localhost:8000", "--outro", str(missing_outro), str(sample_repo)],
    )
    assert res.exit_code == 2
    assert "Error: Outro file" in res.stderr
    assert "not found" in res.stderr


def test_cli_html_nolinks(sample_repo: Path) -> None:
    """Verify --nolinks suppresses anchor tags in HTML mode."""
    runner = CliRunner()
    res = runner.invoke(
        app,
        ["-H", "http://localhost:8000", "--nolinks", str(sample_repo)],
    )
    assert res.exit_code == 0
    assert "<a href=" not in res.stdout
    assert '<span class="file">' in res.stdout


def test_cli_conflicting_formats(sample_repo: Path) -> None:
    """Verify specifying mutually exclusive format flags exits with code 2."""
    runner = CliRunner()
    res_xh = runner.invoke(
        app,
        ["-X", "-H", "http://localhost:8000", str(sample_repo)],
    )
    assert res_xh.exit_code == 2
    assert "Error: Conflicting format options" in res_xh.stderr

    res_tree_xml = runner.invoke(
        app,
        ["--tree", "-X", str(sample_repo)],
    )
    assert res_tree_xml.exit_code == 2
    assert "Error: Conflicting format options" in res_tree_xml.stderr

    res_tree_html = runner.invoke(
        app,
        ["--tree", "-H", "http://localhost:8000", str(sample_repo)],
    )
    assert res_tree_html.exit_code == 2
    assert "Error: Conflicting format options" in res_tree_html.stderr


def test_cli_xml_html_output_redirect(sample_repo: Path, tmp_path: Path) -> None:
    """Verify -o redirects XML and HTML output directly to files."""
    xml_out = tmp_path / "out.xml"
    html_out = tmp_path / "out.html"

    runner = CliRunner()
    res_x = runner.invoke(app, ["-X", "-o", str(xml_out), str(sample_repo)])
    assert res_x.exit_code == 0
    assert xml_out.is_file()
    assert "<tree" in xml_out.read_text(encoding="utf-8")

    res_h = runner.invoke(
        app,
        ["-H", "http://example.com", "-o", str(html_out), str(sample_repo)],
    )
    assert res_h.exit_code == 0
    assert html_out.is_file()
    assert "<!DOCTYPE html>" in html_out.read_text(encoding="utf-8")
