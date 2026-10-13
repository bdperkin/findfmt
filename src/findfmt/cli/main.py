"""Command-line interface for findfmt."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import Annotated

import typer

from findfmt.cli import help as h
from findfmt.cli.pager import FindfmtCommand
from findfmt.cli.runner import execute_findfmt
from findfmt.diagnostics import (
    diagnostics_callback,
    get_diagnostics,
    get_git_version,
    get_version,
    version_callback,
)
from findfmt.entrypoints import main
from findfmt.formatters import OutputFormat
from findfmt.terminal import PagerController
from findfmt.traversal import find_files

get_help_all = h.get_help_all
help_all_callback = h.help_all_callback
known_tags_callback = h.known_tags_callback

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
    "version_callback",
]

_PT = "Tag Filtering"
_PC = "Traversal Controls"
_PO = "Output Formatting"
_PANEL_TAGS, _PANEL_TRAVERSAL, _PANEL_OUTPUT = _PT, _PC, _PO

app = typer.Typer(
    name="findfmt",
    help=h.APP_HELP,
    add_completion=False,
    no_args_is_help=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.command(name="findfmt", cls=FindfmtCommand, help=h.APP_HELP, epilog=h.CLI_EPILOG)
def findfmt(
    paths: Annotated[list[Path] | None, typer.Argument(help=h.HELP_PATHS)] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("-t", "--type", "--tag", rich_help_panel=_PT, help=h.HELP_TAGS),
    ] = None,
    exclude_tags: Annotated[
        list[str] | None,
        typer.Option(
            "-e",
            "--exclude",
            "--exclude-tag",
            rich_help_panel=_PT,
            help=h.HELP_EXCLUDE_TAGS,
        ),
    ] = None,
    all_tags: Annotated[
        bool,
        typer.Option("--all-tags/--no-all-tags", rich_help_panel=_PT, help=h.HELP_ALL_TAGS),
    ] = False,
    pattern: Annotated[
        list[str] | None,
        typer.Option(
            "-P",
            "--pattern",
            "--include-pattern",
            rich_help_panel=_PC,
            help=h.HELP_PATTERN,
        ),
    ] = None,
    exclude_pattern: Annotated[
        list[str] | None,
        typer.Option("-I", "--exclude-pattern", rich_help_panel=_PC, help=h.HELP_EXCLUDE_PATTERN),
    ] = None,
    ignore_case: Annotated[
        bool,
        typer.Option(
            "--ignore-case/--no-ignore-case",
            rich_help_panel=_PC,
            help=h.HELP_IGNORE_CASE,
        ),
    ] = False,
    match_dirs: Annotated[
        bool,
        typer.Option(
            "--match-dirs/--no-match-dirs",
            "--matchdirs/--no-matchdirs",
            rich_help_panel=_PC,
            help=h.HELP_MATCH_DIRS,
        ),
    ] = False,
    shebang: Annotated[
        str | None,
        typer.Option("--shebang", rich_help_panel=_PC, help=h.HELP_SHEBANG),
    ] = None,
    no_ignore: Annotated[
        bool,
        typer.Option("--no-ignore/--ignore", rich_help_panel=_PC, help=h.HELP_NO_IGNORE),
    ] = False,
    gitignore_file: Annotated[
        Path | None,
        typer.Option("--gitignore-file", rich_help_panel=_PC, help=h.HELP_GITIGNORE_FILE),
    ] = None,
    hidden: Annotated[
        bool,
        typer.Option("--hidden/--no-hidden", rich_help_panel=_PC, help=h.HELP_HIDDEN),
    ] = False,
    follow_symlinks: Annotated[
        bool,
        typer.Option(
            "-l",
            "--follow-links/--no-follow-links",
            "--follow-symlinks/--no-follow-symlinks",
            "--symlinks/--no-symlinks",
            rich_help_panel=_PC,
            help=h.HELP_FOLLOW_SYMLINKS,
        ),
    ] = False,
    dirs_only: Annotated[
        bool,
        typer.Option("-d", "--dirs-only", rich_help_panel=_PC, help=h.HELP_DIRS_ONLY),
    ] = False,
    one_file_system: Annotated[
        bool,
        typer.Option("-x", "--one-file-system", rich_help_panel=_PC, help=h.HELP_ONE_FILE_SYSTEM),
    ] = False,
    max_depth: Annotated[
        int | None,
        typer.Option("-L", "--max-depth", rich_help_panel=_PC, help=h.HELP_MAX_DEPTH),
    ] = None,
    file_limit: Annotated[
        int | None,
        typer.Option("--filelimit", rich_help_panel=_PC, help=h.HELP_FILE_LIMIT),
    ] = None,
    prune: Annotated[
        bool,
        typer.Option("--prune", rich_help_panel=_PC, help=h.HELP_PRUNE),
    ] = False,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "-f",
            "--format",
            case_sensitive=False,
            rich_help_panel=_PO,
            help=h.HELP_FORMAT,
        ),
    ] = OutputFormat.TEXT,
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", rich_help_panel=_PO, help=h.HELP_OUTPUT),
    ] = None,
    tree: Annotated[
        bool,
        typer.Option("--tree/--no-tree", rich_help_panel=_PO, help=h.HELP_TREE),
    ] = False,
    table_style: Annotated[
        str | None,
        typer.Option("--table-style", rich_help_panel=_PO, help=h.HELP_TABLE_STYLE),
    ] = None,
    pager: Annotated[
        bool | None,
        typer.Option("--pager/--no-pager", rich_help_panel=_PO, help=h.HELP_PAGER),
    ] = None,
    no_indent: Annotated[
        bool,
        typer.Option("-i", "--no-indent/--indent", rich_help_panel=_PO, help=h.HELP_NO_INDENT),
    ] = False,
    ansi_lines: Annotated[
        bool,
        typer.Option(
            "-A",
            "--ansi-lines/--no-ansi-lines",
            rich_help_panel=_PO,
            help=h.HELP_ANSI_LINES,
        ),
    ] = False,
    cp437: Annotated[
        bool,
        typer.Option("-S", "--cp437/--no-cp437", rich_help_panel=_PO, help=h.HELP_CP437),
    ] = False,
    color: Annotated[
        bool | None,
        typer.Option("-C/-n", "--color/--no-color", rich_help_panel=_PO, help=h.HELP_COLOR),
    ] = None,
    absolute: Annotated[
        bool,
        typer.Option(
            "--absolute/--no-absolute",
            "--full-path/--no-full-path",
            rich_help_panel=_PO,
            help=h.HELP_ABSOLUTE,
        ),
    ] = False,
    relative: Annotated[
        bool,
        typer.Option(
            "--relative/--no-relative",
            "--relative-path/--no-relative-path",
            rich_help_panel=_PO,
            help=h.HELP_RELATIVE,
        ),
    ] = False,
    print0: Annotated[
        bool,
        typer.Option("-0", "--print0/--no-print0", rich_help_panel=_PO, help=h.HELP_PRINT0),
    ] = False,
    list_tags: Annotated[
        bool,
        typer.Option("--list-tags/--no-list-tags", rich_help_panel=_PO, help=h.HELP_LIST_TAGS),
    ] = False,
    summary: Annotated[
        bool,
        typer.Option("-s", "--summary/--no-summary", rich_help_panel=_PO, help=h.HELP_SUMMARY),
    ] = False,
    known_tags: Annotated[
        bool,
        typer.Option(
            "--known-tags",
            is_eager=True,
            callback=known_tags_callback,
            help=h.HELP_KNOWN_TAGS,
        ),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help=h.HELP_VERBOSE)] = False,
    diagnostics: Annotated[
        bool,
        typer.Option(
            "--diagnostics",
            is_eager=True,
            callback=diagnostics_callback,
            help=h.HELP_DIAGNOSTICS,
        ),
    ] = False,
    version: Annotated[
        bool | None,
        typer.Option(
            "-v",
            "-V",
            "--version",
            is_eager=True,
            callback=version_callback,
            help=h.HELP_VERSION,
        ),
    ] = None,
    help_all: Annotated[
        bool,
        typer.Option("--help-all", is_eager=True, callback=help_all_callback, help=h.HELP_HELP_ALL),
    ] = False,
) -> None:
    """Execute file discovery and classification matching."""
    params = {
        k: v
        for k, v in locals().items()
        if k not in {"known_tags", "verbose", "diagnostics", "version", "help_all"}
    }
    execute_findfmt(**params)


if __name__ == "__main__":  # pragma: no cover
    app()
