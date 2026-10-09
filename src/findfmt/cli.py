"""Command-line interface for findfmt."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import Annotated

import typer

from findfmt.cli_help import get_help_all, help_all_callback, known_tags_callback
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
from findfmt.traversal import find_files

__all__ = [
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

app = typer.Typer(
    name="findfmt",
    help=(
        "A .gitignore-aware file discovery and classification suite that locates "
        "files by content format, shebang, and MIME tag."
    ),
    add_completion=False,
    no_args_is_help=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.command(
    name="findfmt",
    help=(
        "A .gitignore-aware file discovery and classification suite that locates "
        "files by content format, shebang, and MIME tag."
    ),
    epilog=(
        "Common Examples:\n"
        "  findfmt -t python                        # Find Python files\n"
        "  findfmt --shebang bash scripts/          # Find bash scripts in scripts/\n"
        "  findfmt -t python -t executable --all-tags # Files matching both tags\n"
        "  findfiles --no-hidden                    # Wrapper: exclude hidden files\n"
        "  findfmt -- -weird-name                   # Path starting with a dash\n\n"
        "Run 'findfmt --help-all' for the comprehensive manual, environment variables, "
        "and exit codes."
    ),
)
def findfmt(
    paths: Annotated[
        list[Path] | None,
        typer.Argument(
            help="One or more directory or file paths to inspect (default: current directory).",
        ),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option(
            "--type",
            "-t",
            "--tag",
            rich_help_panel="Tag Filtering",
            help="Tag or comma-separated tags to match (e.g. 'python', 'yaml,json', 'executable').",
        ),
    ] = None,
    exclude_tags: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude",
            "-e",
            "--exclude-tag",
            rich_help_panel="Tag Filtering",
            help="Tag or comma-separated tags to exclude.",
        ),
    ] = None,
    all_tags: Annotated[
        bool,
        typer.Option(
            "--all-tags/--no-all-tags",
            rich_help_panel="Tag Filtering",
            help="Require matching files to have ALL specified tags rather than ANY tag.",
        ),
    ] = False,
    shebang: Annotated[
        str | None,
        typer.Option(
            "--shebang",
            rich_help_panel="Traversal Controls",
            help="Filter files whose shebang contains this interpreter or pattern.",
        ),
    ] = None,
    no_ignore: Annotated[
        bool,
        typer.Option(
            "--no-ignore/--ignore",
            rich_help_panel="Traversal Controls",
            help="Do not respect .gitignore rules during traversal.",
        ),
    ] = False,
    hidden: Annotated[
        bool,
        typer.Option(
            "--hidden/--no-hidden",
            rich_help_panel="Traversal Controls",
            help="Include hidden files and directories.",
        ),
    ] = False,
    follow_symlinks: Annotated[
        bool,
        typer.Option(
            "--follow-symlinks/--no-follow-symlinks",
            "--symlinks/--no-symlinks",
            "-L",
            rich_help_panel="Traversal Controls",
            help="Follow symbolic links during traversal.",
        ),
    ] = False,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            case_sensitive=False,
            rich_help_panel="Output Formatting",
            help=(
                "Output format (text, json, jsonl, yaml, ipynb, csv, tsv, "
                "markdown, md, rst, table, tree)."
            ),
        ),
    ] = OutputFormat.TEXT,
    tree: Annotated[
        bool,
        typer.Option(
            "--tree/--no-tree",
            rich_help_panel="Output Formatting",
            help="Render output in a hierarchical directory tree (equivalent to --format tree).",
        ),
    ] = False,
    table_style: Annotated[
        str | None,
        typer.Option(
            "--table-style",
            rich_help_panel="Output Formatting",
            help=(
                "Border style for table or rst output (e.g. rounded, simple, minimal, "
                "double, heavy, markdown, ascii, square, grid)."
            ),
        ),
    ] = None,
    absolute: Annotated[
        bool,
        typer.Option(
            "--absolute/--no-absolute",
            rich_help_panel="Output Formatting",
            help="Output absolute paths rather than paths relative to the traversal root.",
        ),
    ] = False,
    print0: Annotated[
        bool,
        typer.Option(
            "--print0/--no-print0",
            "-0",
            rich_help_panel="Output Formatting",
            help=r"Delimit path outputs with a NUL (\0) character instead of a newline.",
        ),
    ] = False,
    list_tags: Annotated[
        bool,
        typer.Option(
            "--list-tags/--no-list-tags",
            "-l",
            rich_help_panel="Output Formatting",
            help="Display identified tags alongside each matched path.",
        ),
    ] = False,
    summary: Annotated[
        bool,
        typer.Option(
            "--summary/--no-summary",
            "-s",
            rich_help_panel="Output Formatting",
            help="Print summary match statistics to stderr.",
        ),
    ] = False,
    known_tags: Annotated[
        bool,
        typer.Option(
            "--known-tags",
            is_eager=True,
            callback=known_tags_callback,
            help="List all known classification tags supported by the engine and exit.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Enable verbose output or extended runtime diagnostics with --version.",
        ),
    ] = False,
    diagnostics: Annotated[
        bool,
        typer.Option(
            "--diagnostics",
            is_eager=True,
            callback=diagnostics_callback,
            help="Display runtime environment diagnostics and exit.",
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
            help="Display the version of findfmt and exit.",
        ),
    ] = None,
    help_all: Annotated[
        bool,
        typer.Option(
            "--help-all",
            is_eager=True,
            callback=help_all_callback,
            help=(
                "Display comprehensive help reference including environment variables, "
                "exit codes, and examples."
            ),
        ),
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
        find_files_func=find_files,
    )


if __name__ == "__main__":  # pragma: no cover
    app()
