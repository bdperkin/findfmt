"""Security audit and regression tests for untrusted filenames and terminal escape sanitization."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import docutils.core
import docutils.writers
import pytest
from typer.testing import CliRunner

from findfmt import (
    build_file_uri,
    format_display_path,
    format_hyperlink,
    format_osc8_link,
    format_rich_link,
    mask_control_characters,
    strip_ansi_escapes,
)
from findfmt.cli import app
from findfmt.formatters import (
    CsvTableFormatter,
    HtmlFormatter,
    MarkdownFormatter,
    RstFormatter,
    TextFormatter,
    XmlFormatter,
)
from findfmt.formatters.badges import format_tag_badge
from findfmt.formatters.tree import RichTreeFormatter
from findfmt.formatters.visual import RichTableFormatter
from findfmt.models import FileInfo

runner = CliRunner()


def test_strip_ansi_escapes_csi_and_osc() -> None:
    """Verify strip_ansi_escapes eliminates CSI, OSC, and auxiliary escape sequences."""
    # 7-bit CSI color and cursor
    csi_colored = "\x1b[31;1mtoxic_file\x1b[0m.txt"
    assert strip_ansi_escapes(csi_colored) == "toxic_file.txt"

    csi_cursor = "\x1b[2J\x1b[Hrootkit.sh"
    assert strip_ansi_escapes(csi_cursor) == "rootkit.sh"

    # 7-bit OSC window title and clipboard
    osc_title = "\x1b]0;Spoofed Title\x07malicious.bin"
    assert strip_ansi_escapes(osc_title) == "malicious.bin"

    osc_st = "\x1b]2;Evil Terminal Title\x1b\\payload.py"
    assert strip_ansi_escapes(osc_st) == "payload.py"

    # 8-bit C1 CSI and OSC
    c1_csi = "\x9b31mred_c1\x9b0m.dat"
    assert strip_ansi_escapes(c1_csi) == "red_c1.dat"

    c1_osc = "\x9d0;C1 Title\x07c1_osc.bin"
    assert strip_ansi_escapes(c1_osc) == "c1_osc.bin"

    c1_osc_st = "\x9d0;C1 Title\x9cc1_osc_term.bin"
    assert strip_ansi_escapes(c1_osc_st) == "c1_osc_term.bin"

    # 7-bit 2-character / Fe sequences
    fe_seq = "\x1b(Bcharset\x1b=keypad\x1b7save\x1b8restore"
    assert strip_ansi_escapes(fe_seq) == "charsetkeypadsaverestore"

    # Clean string passthrough
    clean = "regular-filename_01.txt"
    assert strip_ansi_escapes(clean) == clean


def test_mask_control_characters_c0_del_c1() -> None:
    """Verify mask_control_characters masks C0, DEL, and C1 controls while preserving Unicode."""
    # C0 control characters (0-31)
    c0_text = "start\x00\x07\x08\r\n\x1bend"
    assert mask_control_characters(c0_text) == "start??????end"

    # Delete character 127
    del_text = "file\x7fdel.txt"
    assert mask_control_characters(del_text) == "file?del.txt"

    # C1 control characters (128-159)
    c1_text = "c1_\x80\x90\x9b\x9d\x9f_end"
    assert mask_control_characters(c1_text) == "c1_?????_end"

    # Printable Latin-1 and Unicode above 159 remain untouched
    unicode_text = "café \u2713 \u00a0 \u20ac"
    assert mask_control_characters(unicode_text) == unicode_text


def test_format_display_path_default_sanitization() -> None:
    """Verify format_display_path cleans untrusted filenames by default and respects --literal."""
    toxic_name = "\x1b[31;1m\x1b]0;Title\x07bad\x00\r\nfile\x1b[0m.txt"

    # Default options strip ANSI and mask controls
    sanitized = format_display_path(toxic_name)
    assert "\x1b" not in sanitized
    assert "\x07" not in sanitized
    assert "\r" not in sanitized
    assert "\x00" not in sanitized
    assert sanitized == "bad???file.txt"

    # Literal preserves the entire byte sequence verbatim
    literal_out = format_display_path(toxic_name, literal=True)
    assert literal_out == toxic_name


def test_format_display_path_escape_markup() -> None:
    """Verify format_display_path escapes Rich console markup when requested."""
    markup_name = "[bold red]test[/bold red]"
    escaped = format_display_path(markup_name, escape_markup=True)
    assert r"\[bold red]test\[/bold red]" in escaped

    # Hyperlink with leading escaped bracket
    uri = "file:///tmp/test"
    linked_escaped = format_display_path(
        markup_name,
        hyperlink=True,
        uri=uri,
        escape_markup=True,
    )
    assert uri in linked_escaped
    assert r"\[bold red]" in linked_escaped


def test_hyperlink_uri_security() -> None:
    """Verify URI construction and formatting strips terminal control characters."""
    # Authority injection attempt with terminal escapes
    malicious_auth = "localhost\x1b]0;Title\x07\x1b\\evil"
    uri = build_file_uri("/workspace/app.py", authority=malicious_auth)
    assert "\x1b" not in uri
    assert "\x07" not in uri
    assert "localhost" in uri

    # Schema injection attempt with terminal escapes
    malicious_schema = "vscode\x1b]0;Hacked\x07://file/"
    uri_schema = build_file_uri("/workspace/app.py", schema=malicious_schema)
    assert "\x1b" not in uri_schema
    assert "\x07" not in uri_schema

    # format_osc8_link stripping control chars to prevent early termination
    hostile_target = "file:///tmp/safe\x1b\\rm -rf /\x07"
    link = format_osc8_link("safe_file.txt", hostile_target)
    assert "\x1b\\rm" not in link
    assert "\x07" not in link

    # format_rich_link escaping brackets and quotes
    rich_target = 'https://example.com/[evil]"test"'
    rich_link = format_rich_link("click", rich_target)
    assert "[" not in rich_link[6:-14]
    assert "]" not in rich_link[6:-14]
    assert '"' not in rich_link[6:-14]

    # format_hyperlink dispatcher
    dispatched = format_hyperlink("click", "file:///test", rich_markup=False)
    assert "\033]8;;" in dispatched


def test_text_formatter_terminal_safety() -> None:
    """Verify TextFormatter sanitizes paths, tags, and metadata unless literal=True."""
    hostile_file = FileInfo(
        path=Path("/tmp/\x1b[31mhostile\x1b[0m.sh"),
        relative_path=Path("\x1b[31mhostile\x1b[0m.sh"),
        tags=frozenset({"\x1b[32mtag\x1b[0m", "shell"}),
        shebang="#!/bin/sh \x1b]0;Evil\x07",
    )

    fmt_default = TextFormatter(show_tags=True)
    out_default = fmt_default.format([hostile_file])
    assert "\x1b" not in out_default
    assert "\x07" not in out_default
    assert "hostile.sh" in out_default
    assert "tag" in out_default

    fmt_literal = TextFormatter(show_tags=True, literal=True)
    out_literal = fmt_literal.format([hostile_file])
    assert "\x1b[31m" in out_literal
    assert "\x1b[32m" in out_literal


def test_rich_table_formatter_markup_injection() -> None:
    """Verify RichTableFormatter escapes filenames and metadata, preventing markup execution."""
    file_markup = FileInfo(
        path=Path("/tmp/[bold red]malicious[/bold red].py"),
        relative_path=Path("[bold red]malicious[/bold red].py"),
        tags=frozenset({"[yellow]custom_tag[/yellow]"}),
        mime_type="text/[malicious]",
        shebang="#!/bin/sh [danger]",
    )

    formatter = RichTableFormatter(absolute=False, console_width=200)
    output = formatter.format([file_markup])
    # The literal tag string must appear in the rendered table without being stripped
    assert str(file_markup.relative_path) in output
    assert "text/[malicious]" in output
    assert "#!/bin/sh [danger]" in output


def test_rich_tree_formatter_markup_injection() -> None:
    """Verify RichTreeFormatter escapes directory branch and leaf node labels."""
    file_markup = FileInfo(
        path=Path("[blue_dir]/[green_leaf].txt"),
        relative_path=Path("[blue_dir]/[green_leaf].txt"),
        tags=frozenset({"tag"}),
        mime_type="text/[mime]",
    )

    formatter = RichTreeFormatter(absolute=False, console_width=200)
    output = formatter.format([file_markup])
    # Both branch directory and leaf file must preserve their brackets literally
    assert "[blue_dir]" in output
    assert "[green_leaf].txt" in output
    assert "text/[mime]" in output


def test_csv_table_formatter_markup_injection() -> None:
    """Verify CsvTableFormatter escapes CSV record cells before adding to Rich table."""
    file_markup = FileInfo(
        path=Path("/tmp/[red]test[/red].txt"),
        relative_path=Path("[red]test[/red].txt"),
        tags=frozenset({"[cyan]tag[/cyan]"}),
        mime_type="text/[custom]",
        shebang="#!/bin/bash [opt]",
    )

    formatter = CsvTableFormatter(absolute=False, console_width=200)
    output = formatter.format([file_markup])
    assert str(file_markup.relative_path) in output
    assert "[cyan]tag[/cyan]" in output


def test_markdown_formatter_special_delimiters() -> None:
    """Verify MarkdownFormatter escapes pipes and backticks in filenames."""
    file_delims = FileInfo(
        path=Path("table|delimited`code`name.md"),
        relative_path=Path("table|delimited`code`name.md"),
        tags=frozenset({"tag"}),
    )

    formatter = MarkdownFormatter(absolute=False)
    output = formatter.format([file_delims])
    # Pipes and backticks must be backslash-escaped
    assert r"table\|delimited\`code\`name.md" in output


def test_rst_formatter_special_delimiters() -> None:
    """Verify RstFormatter escapes pipes and backticks and produces valid docutils output."""
    file_delims = FileInfo(
        path=Path("rst|pipe`tick`file.txt"),
        relative_path=Path("rst|pipe`tick`file.txt"),
        tags=frozenset({"rst"}),
    )

    formatter = RstFormatter(absolute=False)
    output = formatter.format([file_delims])
    assert r"rst\|pipe\`tick\`file.txt" in output

    # Docutils parser should parse the generated RST table without syntax errors
    writer = docutils.writers.get_writer_class("html")()
    parsed_html = docutils.core.publish_string(output, writer=writer)
    assert parsed_html is not None


def test_xml_formatter_injection_and_control_chars() -> None:
    """Verify XmlFormatter masks invalid control characters and produces well-formed XML 1.0."""
    hostile_file = FileInfo(
        path=Path("dir\x01\x07sub/file\x00\x08<script>alert(1)</script>.xml"),
        relative_path=Path("dir\x01\x07sub/file\x00\x08<script>alert(1)</script>.xml"),
        tags=frozenset({"xml", "tag\x02"}),
        symlink_target="target\x03link",
        shebang="#!/bin/sh \x1b[31mred\x1b[0m",
        mime_type="text/xml\x1b[0m",
    )

    formatter = XmlFormatter(absolute=False)
    xml_output = formatter.format([hostile_file])

    # ElementTree must successfully parse the serialized document without ParseError
    parsed_tree = ET.fromstring(xml_output)
    assert parsed_tree.tag == "tree"
    # Verify XML entities were properly escaped (no unescaped <script>)
    assert "<script>" not in xml_output
    assert "&lt;script&gt;" in xml_output

    # Literal mode preserves raw values
    fmt_literal = XmlFormatter(absolute=False, literal=True)
    xml_literal = fmt_literal.format([hostile_file])
    assert "target\x03link" in xml_literal


def test_html_formatter_xss_prevention() -> None:
    """Verify HtmlFormatter strictly escapes HTML delimiters preventing XSS."""
    xss_file = FileInfo(
        path=Path("safe_dir/<script>alert(1).html"),
        relative_path=Path("safe_dir/<script>alert(1).html"),
        tags=frozenset({"html", '<b style="color:red">tag</b>'}),
        mime_type='text/html"><script>alert(2)</script>',
    )

    formatter = HtmlFormatter(absolute=False, title='<script>alert("title")</script>')
    html_output = formatter.format([xss_file])

    # Raw script or img injection tags must not be present
    assert '<script>alert("title")</script>' not in html_output
    assert "&lt;script&gt;alert(&quot;title&quot;)&lt;/script&gt;" in html_output
    assert "<script>alert(1).html" not in html_output
    assert "&lt;script&gt;alert(1).html" in html_output


def test_tag_badge_markup_safety() -> None:
    """Verify format_tag_badge escapes Rich markup characters in custom tags."""
    badge = format_tag_badge("[bold red]injected[/bold red]")
    assert r"\[bold red]injected\[/bold red]" in badge


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows filesystems disallow control characters in filenames",
)
def test_cli_literal_and_sanitization_e2e(tmp_path: Path) -> None:
    """Verify CLI end-to-end default sanitization and --literal flag preservation."""
    # Create file with control characters
    bad_filename = "bad\x07file.txt"
    file_path = tmp_path / bad_filename
    file_path.write_text("content\n", encoding="utf-8")

    # Default CLI run should mask control character
    res_default = runner.invoke(app, [str(tmp_path)])
    assert res_default.exit_code == 0
    assert "bad?file.txt" in res_default.stdout
    assert "\x07" not in res_default.stdout

    # --literal should preserve control character
    res_literal = runner.invoke(app, ["-N", str(tmp_path)])
    assert res_literal.exit_code == 0
    assert "\x07" in res_literal.stdout
