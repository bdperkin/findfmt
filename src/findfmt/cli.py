"""Command-line interface for findfmt."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import Annotated

import typer

from findfmt.cli_help import (
    APP_HELP,
    CLI_EPILOG,
    HELP_ABSOLUTE,
    HELP_ALL_TAGS,
    HELP_ANSI_LINES,
    HELP_COLOR,
    HELP_CP437,
    HELP_DIAGNOSTICS,
    HELP_EXCLUDE_TAGS,
    HELP_FOLLOW_SYMLINKS,
    HELP_FORMAT,
    HELP_HELP_ALL,
    HELP_HIDDEN,
    HELP_KNOWN_TAGS,
    HELP_LIST_TAGS,
    HELP_NO_IGNORE,
    HELP_NO_INDENT,
    HELP_PAGER,
    HELP_PATHS,
    HELP_PRINT0,
    HELP_SHEBANG,
    HELP_SUMMARY,
    HELP_TABLE_STYLE,
    HELP_TAGS,
    HELP_TREE,
    HELP_VERBOSE,
    HELP_VERSION,
    get_help_all,
    help_all_callback,
    known_tags_callback,
)
from findfmt.cli_pager import FindfmtCommand
from findfmt.cli_runner import execute_findfmt
from findfmt.diagnostics import (
    diagnostics_callback,
    get_diagnostics,
    get_git_version,
    get_version,
    version_callback,
)
from findfmt.entrypoints import (
    main,
    main_findfilefmt,
    main_findfilemime,
    main_findfiles,
    main_findfmt0,
    main_findshebang,
    main_findsummary,
)
from findfmt.formatters import OutputFormat
from findfmt.summary import parse_tag_arguments, write_summary
from findfmt.terminal import PagerController
from findfmt.traversal import find_files

__all__ = [
    "FindfmtCommand",
    "PagerController",
    "app",
    "diagnostics_callback",
    "find_files",
    "get_diagnostics",
    "get_git_version",
    "get_help_all",
    "get_version",
    "help_all_callback",
    "known_tags_callback",
    "main",
    "main_findfilefmt",
    "main_findfilemime",
    "main_findfiles",
    "main_findfmt0",
    "main_findshebang",
    "main_findsummary",
    "parse_tag_arguments",
    "version_callback",
    "write_summary",
]

_PANEL_TAGS = "Tag Filtering"
_PANEL_TRAVERSAL = "Traversal Controls"
_PANEL_OUTPUT = "Output Formatting"

app = typer.Typer(
    name="findfmt",
    help=APP_HELP,
    add_completion=False,
    no_args_is_help=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.command(name="findfmt", cls=FindfmtCommand, help=APP_HELP, epilog=CLI_EPILOG)
def findfmt(
    paths: Annotated[list[Path] | None, typer.Argument(help=HELP_PATHS)] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--type", "-t", "--tag", rich_help_panel=_PANEL_TAGS, help=HELP_TAGS),
    ] = None,
    exclude_tags: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude",
            "-e",
            "--exclude-tag",
            rich_help_panel=_PANEL_TAGS,
            help=HELP_EXCLUDE_TAGS,
        ),
    ] = None,
    all_tags: Annotated[
        bool,
        typer.Option("--all-tags/--no-all-tags", rich_help_panel=_PANEL_TAGS, help=HELP_ALL_TAGS),
    ] = False,
    shebang: Annotated[
        str | None,
        typer.Option("--shebang", rich_help_panel=_PANEL_TRAVERSAL, help=HELP_SHEBANG),
    ] = None,
    no_ignore: Annotated[
        bool,
        typer.Option("--no-ignore/--ignore", rich_help_panel=_PANEL_TRAVERSAL, help=HELP_NO_IGNORE),
    ] = False,
    hidden: Annotated[
        bool,
        typer.Option("--hidden/--no-hidden", rich_help_panel=_PANEL_TRAVERSAL, help=HELP_HIDDEN),
    ] = False,
    follow_symlinks: Annotated[
        bool,
        typer.Option(
            "--follow-symlinks/--no-follow-symlinks",
            "--symlinks/--no-symlinks",
            "-L",
            rich_help_panel=_PANEL_TRAVERSAL,
            help=HELP_FOLLOW_SYMLINKS,
        ),
    ] = False,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            case_sensitive=False,
            rich_help_panel=_PANEL_OUTPUT,
            help=HELP_FORMAT,
        ),
    ] = OutputFormat.TEXT,
    tree: Annotated[
        bool,
        typer.Option("--tree/--no-tree", rich_help_panel=_PANEL_OUTPUT, help=HELP_TREE),
    ] = False,
    table_style: Annotated[
        str | None,
        typer.Option("--table-style", rich_help_panel=_PANEL_OUTPUT, help=HELP_TABLE_STYLE),
    ] = None,
    pager: Annotated[
        bool | None,
        typer.Option("--pager/--no-pager", "-P", rich_help_panel=_PANEL_OUTPUT, help=HELP_PAGER),
    ] = None,
    no_indent: Annotated[
        bool,
        typer.Option(
            "--no-indent/--indent",
            "-i",
            rich_help_panel=_PANEL_OUTPUT,
            help=HELP_NO_INDENT,
        ),
    ] = False,
    ansi_lines: Annotated[
        bool,
        typer.Option(
            "--ansi-lines/--no-ansi-lines",
            "-A",
            rich_help_panel=_PANEL_OUTPUT,
            help=HELP_ANSI_LINES,
        ),
    ] = False,
    cp437: Annotated[
        bool,
        typer.Option("--cp437/--no-cp437", "-S", rich_help_panel=_PANEL_OUTPUT, help=HELP_CP437),
    ] = False,
    color: Annotated[
        bool | None,
        typer.Option("--color/--no-color", "-C/-n", rich_help_panel=_PANEL_OUTPUT, help=HELP_COLOR),
    ] = None,
    absolute: Annotated[
        bool,
        typer.Option(
            "--absolute/--no-absolute",
            "--full-path/--no-full-path",
            rich_help_panel=_PANEL_OUTPUT,
            help=HELP_ABSOLUTE,
        ),
    ] = False,
    print0: Annotated[
        bool,
        typer.Option("--print0/--no-print0", "-0", rich_help_panel=_PANEL_OUTPUT, help=HELP_PRINT0),
    ] = False,
    list_tags: Annotated[
        bool,
        typer.Option(
            "--list-tags/--no-list-tags",
            "-l",
            rich_help_panel=_PANEL_OUTPUT,
            help=HELP_LIST_TAGS,
        ),
    ] = False,
    summary: Annotated[
        bool,
        typer.Option(
            "--summary/--no-summary",
            "-s",
            rich_help_panel=_PANEL_OUTPUT,
            help=HELP_SUMMARY,
        ),
    ] = False,
    known_tags: Annotated[
        bool,
        typer.Option(
            "--known-tags",
            is_eager=True,
            callback=known_tags_callback,
            help=HELP_KNOWN_TAGS,
        ),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help=HELP_VERBOSE)] = False,
    diagnostics: Annotated[
        bool,
        typer.Option(
            "--diagnostics",
            is_eager=True,
            callback=diagnostics_callback,
            help=HELP_DIAGNOSTICS,
        ),
    ] = False,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            "-V",
            is_eager=True,
            callback=version_callback,
            help=HELP_VERSION,
        ),
    ] = None,
    help_all: Annotated[
        bool,
        typer.Option("--help-all", is_eager=True, callback=help_all_callback, help=HELP_HELP_ALL),
    ] = False,
) -> None:
    """Execute file discovery and classification matching."""
    execute_findfmt(
        paths=paths,
        tags=tags,
        exclude_tags=exclude_tags,
        all_tags=all_tags,
        shebang=shebang,
        no_ignore=no_ignore,
        hidden=hidden,
        follow_symlinks=follow_symlinks,
        output_format=output_format,
        tree=tree,
        table_style=table_style,
        absolute=absolute,
        print0=print0,
        list_tags=list_tags,
        summary=summary,
        pager=pager,
        find_files_func=find_files,
        no_indent=no_indent,
        ansi_lines=ansi_lines,
        cp437=cp437,
        color=color,
    )


if __name__ == "__main__":  # pragma: no cover
    app()
