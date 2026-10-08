"""Comprehensive help reference manual and tag inspection callbacks."""

from __future__ import annotations

import sys

import typer

from findfmt.classifier import get_known_tags
from findfmt.diagnostics import get_version

__all__ = [
    "get_help_all",
    "help_all_callback",
    "known_tags_callback",
]


def get_help_all() -> str:
    """Compile comprehensive help reference manual.

    Returns:
        Formatted multi-line manual text string ending in a newline.
    """
    return (
        f"findfmt {get_version()} - Comprehensive CLI Reference\n\n"
        "Usage: findfmt [OPTIONS] [paths]...\n\n"
        "Tag Filtering:\n"
        "  --type, -t, --tag <str>       Tag or comma-separated tags to match.\n"
        "  --exclude, -e, --exclude-tag  Tag or comma-separated tags to exclude.\n"
        "  --all-tags / --no-all-tags    Require matching ALL specified tags\n"
        "                                [default: no-all-tags].\n\n"
        "Traversal Controls:\n"
        "  --shebang <str>               Filter files by shebang pattern.\n"
        "  --no-ignore / --ignore        Do not respect .gitignore rules [default: ignore].\n"
        "  --hidden / --no-hidden        Include hidden files and dirs [default: no-hidden].\n"
        "  --follow-symlinks, -L         Follow symbolic links [default: no-follow-symlinks].\n"
        "  --symlinks / --no-symlinks    Alias for --follow-symlinks / --no-follow-symlinks.\n\n"
        "Output Formatting:\n"
        "  --absolute / --no-absolute    Output absolute paths [default: no-absolute].\n"
        "  --print0, -0 / --no-print0    Delimit with NUL (\\0) byte [default: no-print0].\n"
        "  --list-tags, -l / --no-list-tags  Display identified tags [default: no-list-tags].\n"
        "  --summary, -s / --no-summary  Print summary statistics [default: no-summary].\n\n"
        "Help & Diagnostics:\n"
        "  --known-tags                  List all known classification tags and exit.\n"
        "  --version, -v, -V             Display version (use with --verbose for diagnostics).\n"
        "  --verbose                     Enable verbose output or extended runtime diagnostics.\n"
        "  --diagnostics                 Display runtime environment diagnostics and exit.\n"
        "  --help-all                    Display this comprehensive reference and exit.\n"
        "  --help, -h                    Display categorized help summary and exit.\n\n"
        "Command Wrappers:\n"
        "  findfiles [PATHS...]          Equivalent to findfmt --hidden\n"
        "  findfilemime [PATHS...]       Equivalent to findfmt --hidden --list-tags\n"
        "  findfilefmt [TAG] [PATHS...]  Equivalent to findfmt --hidden --tag TAG\n"
        "  findshebang [INTERP]...       Equivalent to findfmt --hidden --shebang INTERPRETER\n"
        "  findfmt0 [PATHS...]           Equivalent to findfmt --hidden --print0\n"
        "  findsummary [PATHS...]        Equivalent to findfmt --hidden --summary\n\n"
        "POSIX Double-Dash (--) Terminator:\n"
        "  Arguments following '--' are treated strictly as positional paths:\n"
        "  $ findfmt -- -hyphen-dir/\n"
        "  $ findfilefmt python -- -weird-name/\n\n"
        "Environment Variables:\n"
        "  NO_COLOR                      When set, suppresses colored output (https://no-color.org).\n"
        "  CLICOLOR                      When set to 0, suppresses ANSI colors; 1 enables colors.\n"
        "  CLICOLOR_FORCE                When non-zero, forces color output even when piped.\n"
        "  FINDFMT_CONFIG                Path to custom configuration file overriding defaults.\n\n"
        "Exit Codes:\n"
        "  0                             Success: matching files found, or help/version queried.\n"
        "  1                             Runtime traversal or classification error.\n"
        "  2                             Invalid command-line usage or invalid arguments.\n\n"
        "Workflow Examples:\n"
        "  $ findfmt -t python                     # Find Python files in current repository\n"
        "  $ findfmt --shebang bash scripts/       # Find bash scripts in scripts/\n"
        "  $ findfmt -t python -t executable --all-tags  # Require BOTH tags\n"
        "  $ findfiles --no-hidden                 # Traverse files without hidden files\n"
        "  $ findfilefmt json                      # Shortcut: find JSON files\n"
        "  $ findshebang python                    # Shortcut: find Python shebang scripts\n"
        "  $ findfmt0 -t python | xargs -0 flake8  # Pipe NUL-delimited paths safely\n"
        "  $ findsummary                           # Print summary match statistics to stderr\n"
    )


def help_all_callback(value: bool) -> None:
    """Display comprehensive help reference and exit.

    Args:
        value: Boolean flag indicating if help-all flag was passed.

    Raises:
        typer.Exit: Upon printing comprehensive help reference.
    """
    if value:
        sys.stdout.write(get_help_all())
        raise typer.Exit(code=0)


def known_tags_callback(value: bool) -> None:
    """List all known classification tags supported by the engine and exit.

    Args:
        value: Boolean flag indicating if known-tags flag was passed.

    Raises:
        typer.Exit: Upon printing known tags.
    """
    if value:
        for tag in sorted(get_known_tags()):
            sys.stdout.write(f"{tag}\n")

        raise typer.Exit(code=0)
