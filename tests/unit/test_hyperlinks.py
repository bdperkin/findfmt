"""Unit tests for terminal OSC 8 hyperlinks, URI construction, and CLI options."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from findfmt import (
    build_file_uri,
    format_hyperlink,
    format_osc8_link,
    format_rich_link,
    get_formatter,
)
from findfmt.cli import app
from findfmt.formatters.text import TextFormatter
from findfmt.formatters.tree import RichTreeFormatter
from findfmt.formatters.visual import RichTableFormatter
from findfmt.models import FileInfo
from findfmt.terminal import strip_ansi
from findfmt.utils.hyperlinks import _normalize_schema
from findfmt.utils.strings import format_display_path


def test_normalize_schema() -> None:
    """Verify _normalize_schema parses schemes and components."""
    assert _normalize_schema("file://") == ("file", "")
    assert _normalize_schema("vscode://file/") == ("vscode", "file")
    assert _normalize_schema("cursor://file///") == ("cursor", "file")
    assert _normalize_schema("subl://") == ("subl", "")
    assert _normalize_schema("custom") == ("custom", "")


def test_build_file_uri_basic() -> None:
    """Verify default file:// URI generation without authority."""
    assert build_file_uri("/workspace/app.py") == "file:///workspace/app.py"
    assert build_file_uri(Path("/workspace/app.py")) == "file:///workspace/app.py"
    assert build_file_uri("relative/path.py") == "file:///relative/path.py"


def test_build_file_uri_special_chars() -> None:
    """Verify URI quoting handles spaces and special characters properly."""
    uri = build_file_uri("/workspace/my folder/file #1.py")
    assert uri == "file:///workspace/my%20folder/file%20%231.py"


def test_build_file_uri_with_authority() -> None:
    """Verify file:// URI construction with authority overrides."""
    uri_localhost = build_file_uri("/workspace/app.py", authority="localhost")
    assert uri_localhost == "file://localhost/workspace/app.py"

    uri_remote = build_file_uri("/workspace/app.py", authority="workstation.local")
    assert uri_remote == "file://workstation.local/workspace/app.py"


def test_build_file_uri_custom_schemas() -> None:
    """Verify custom editor schemas with and without authority."""
    uri_vscode = build_file_uri("/workspace/app.py", schema="vscode://file/")
    assert uri_vscode == "vscode://file/workspace/app.py"

    uri_vscode_auth = build_file_uri(
        "/workspace/app.py",
        schema="vscode://file/",
        authority="remote.host",
    )
    assert uri_vscode_auth == "vscode://remote.host/file/workspace/app.py"

    uri_subl = build_file_uri("/workspace/app.py", schema="subl://")
    assert uri_subl == "subl:///workspace/app.py"

    uri_subl_auth = build_file_uri("/workspace/app.py", schema="subl://", authority="myauth")
    assert uri_subl_auth == "subl://myauth/workspace/app.py"


def test_format_osc8_link() -> None:
    """Verify raw OSC 8 escape sequences wrapping text."""
    link = format_osc8_link("app.py", "file:///workspace/app.py")
    expected = "\033]8;;file:///workspace/app.py\033\\app.py\033]8;;\033\\"
    assert link == expected


def test_format_rich_link() -> None:
    """Verify Rich console markup link wrapping text."""
    link = format_rich_link("app.py", "file:///workspace/app.py")
    assert link == "[link=file:///workspace/app.py]app.py[/link]"


def test_format_hyperlink_dispatcher() -> None:
    """Verify format_hyperlink dispatches to OSC 8 or Rich markup based on flag."""
    osc8 = format_hyperlink("app.py", "file:///workspace/app.py", rich_markup=False)
    assert osc8 == "\033]8;;file:///workspace/app.py\033\\app.py\033]8;;\033\\"

    rich = format_hyperlink("app.py", "file:///workspace/app.py", rich_markup=True)
    assert rich == "[link=file:///workspace/app.py]app.py[/link]"


def test_strip_ansi_osc8() -> None:
    """Verify strip_ansi cleans OSC 8 sequences and complex colored link markup."""
    raw = format_osc8_link("app.py", "file:///workspace/app.py")
    assert strip_ansi(raw) == "app.py"

    colored_link = f"\x1b[32m{raw}\x1b[0m"
    assert strip_ansi(colored_link) == "app.py"


def test_format_display_path_hyperlink() -> None:
    """Verify format_display_path wraps output with hyperlink when active."""
    uri = "file:///workspace/src/app.py"
    path_with_link = format_display_path("src/app.py", hyperlink=True, uri=uri)
    assert f"\033]8;;{uri}\033\\src/app.py\033]8;;\033\\" in path_with_link

    # Inactive hyperlink
    path_no_link = format_display_path("src/app.py", hyperlink=False, uri=uri)
    assert path_no_link == "src/app.py"

    # Missing uri fallback
    path_missing_uri = format_display_path("src/app.py", hyperlink=True, uri=None)
    assert path_missing_uri == "src/app.py"


def test_text_formatter_hyperlink() -> None:
    """Verify TextFormatter wraps paths in OSC 8 links."""
    file_info = FileInfo(
        path=Path("/workspace/project/src/app.py"),
        relative_path=Path("src/app.py"),
        tags=frozenset({"python"}),
    )
    formatter = TextFormatter(
        hyperlink=True,
        hyperlink_schema="vscode://file/",
        hyperlink_authority="localhost",
    )
    output = formatter.format([file_info])
    assert "\033]8;;vscode://localhost/file/workspace/project/src/app.py\033\\" in output
    assert strip_ansi(output).strip() == str(file_info.relative_path)


def test_tree_formatter_hyperlink() -> None:
    """Verify RichTreeFormatter wraps directory and file labels in OSC 8 links."""
    file_info = FileInfo(
        path=Path("/workspace/project/src/app.py"),
        relative_path=Path("src/app.py"),
        tags=frozenset({"python"}),
    )
    formatter = RichTreeFormatter(hyperlink=True)
    output = formatter.format([file_info])
    assert "\033]8;;file:///workspace/project/src/app.py\033\\" in output
    assert "app.py" in strip_ansi(output)


def test_table_formatter_hyperlink() -> None:
    """Verify RichTableFormatter wraps table path cells in OSC 8 links."""
    file_info = FileInfo(
        path=Path("/workspace/project/src/app.py"),
        relative_path=Path("src/app.py"),
        tags=frozenset({"python"}),
    )
    formatter = RichTableFormatter(hyperlink=True)
    output = formatter.format([file_info])
    assert "\033]8;;file:///workspace/project/src/app.py\033\\" in output
    assert str(file_info.relative_path) in strip_ansi(output)


def test_get_formatter_with_hyperlink_document() -> None:
    """Verify get_formatter handles hyperlink arguments gracefully for xml/html."""
    xml_fmt = get_formatter("xml", hyperlink=True, hyperlink_schema="file://")
    assert xml_fmt is not None
    html_fmt = get_formatter("html", hyperlink=True, hyperlink_schema="file://")
    assert html_fmt is not None


def test_cli_hyperlink_flags(sample_repo: Path) -> None:
    """Verify CLI flags --hyperlink and --no-hyperlink."""
    runner = CliRunner()

    res_link = runner.invoke(app, ["--hyperlink", str(sample_repo)])
    assert res_link.exit_code == 0
    assert "\033]8;;file://" in res_link.stdout

    res_no_link = runner.invoke(app, ["--no-hyperlink", str(sample_repo)])
    assert res_no_link.exit_code == 0
    assert "\033]8;;file://" not in res_no_link.stdout


def test_cli_hyperlink_schema_and_authority(sample_repo: Path) -> None:
    """Verify CLI flags --hyperlink-schema and --hyperlink-authority."""
    runner = CliRunner()
    res = runner.invoke(
        app,
        [
            "--hyperlink",
            "--hyperlink-schema",
            "vscode://file/",
            "--hyperlink-authority",
            "devbox.local",
            str(sample_repo),
        ],
    )
    assert res.exit_code == 0
    assert "\033]8;;vscode://devbox.local/file/" in res.stdout


def test_cli_hyperlink_formats(sample_repo: Path) -> None:
    """Verify --hyperlink works across table and tree formats."""
    runner = CliRunner()

    res_table = runner.invoke(app, ["--format", "table", "--hyperlink", str(sample_repo)])
    assert res_table.exit_code == 0
    assert "\033]8;;file://" in res_table.stdout

    res_tree = runner.invoke(app, ["--format", "tree", "--hyperlink", str(sample_repo)])
    assert res_tree.exit_code == 0
    assert "\033]8;;file://" in res_tree.stdout
