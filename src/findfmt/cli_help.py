"""Comprehensive help reference manual and tag inspection callbacks."""

from __future__ import annotations

import typer

from findfmt.classifier import get_known_tags
from findfmt.cli_pager import display_with_pager
from findfmt.diagnostics import get_version

__all__ = [
    "APP_HELP",
    "CLI_EPILOG",
    "HELP_ABSOLUTE",
    "HELP_ALL_TAGS",
    "HELP_ANSI_LINES",
    "HELP_COLOR",
    "HELP_CP437",
    "HELP_DIAGNOSTICS",
    "HELP_EXCLUDE_TAGS",
    "HELP_FOLLOW_SYMLINKS",
    "HELP_FORMAT",
    "HELP_HELP_ALL",
    "HELP_HIDDEN",
    "HELP_KNOWN_TAGS",
    "HELP_LIST_TAGS",
    "HELP_NO_IGNORE",
    "HELP_NO_INDENT",
    "HELP_PAGER",
    "HELP_PATHS",
    "HELP_PRINT0",
    "HELP_SHEBANG",
    "HELP_SUMMARY",
    "HELP_TABLE_STYLE",
    "HELP_TAGS",
    "HELP_TREE",
    "HELP_VERBOSE",
    "HELP_VERSION",
    "get_help_all",
    "help_all_callback",
    "known_tags_callback",
]

APP_HELP: str = (
    "A .gitignore-aware file discovery and classification suite that locates "
    "files by content format, shebang, and MIME tag."
)

CLI_EPILOG: str = (
    "Common Examples:\n"
    "  findfmt -t python                        # Find Python files\n"
    "  findfmt --shebang bash scripts/          # Find bash scripts in scripts/\n"
    "  findfmt -t python -t executable --all-tags # Files matching both tags\n"
    "  findfiles --no-hidden                    # Wrapper: exclude hidden files\n"
    "  findfmt -- -weird-name                   # Path starting with a dash\n\n"
    "Run 'findfmt --help-all' for the comprehensive manual, environment variables, "
    "and exit codes."
)


HELP_PATHS = "One or more directory or file paths to inspect (default: current directory)."
HELP_TAGS = "Tag or comma-separated tags to match (e.g. 'python', 'yaml,json', 'executable')."
HELP_EXCLUDE_TAGS = "Tag or comma-separated tags to exclude."
HELP_ALL_TAGS = "Require matching files to have ALL specified tags rather than ANY tag."
HELP_SHEBANG = "Filter files whose shebang contains this interpreter or pattern."
HELP_NO_IGNORE = "Do not respect .gitignore rules during traversal."
HELP_HIDDEN = "Include hidden files and directories."
HELP_FOLLOW_SYMLINKS = "Follow symbolic links during traversal."
HELP_FORMAT = (
    "Output format (text, json, jsonl, yaml, ipynb, csv, csv-table, tsv, "
    "markdown, md, rst, table, tree, ndjson)."
)
HELP_TREE = "Render output in a hierarchical directory tree (equivalent to --format tree)."
HELP_TABLE_STYLE = (
    "Border style for table, csv-table, or rst output (e.g. rounded, simple, "
    "minimal, double, heavy, markdown, ascii, cp437, square, grid)."
)
HELP_PAGER = "Enable or disable interactive paging (defaults to auto-paging on TTY)."
HELP_NO_INDENT = (
    "Do not print indentation lines in tree format and strip extraneous "
    "whitespace in structured formats."
)
HELP_ANSI_LINES = (
    "Use ANSI/VT100 alternate character set line drawing escapes for tree indentation lines."
)
HELP_CP437 = "Use CP437 (IBM-PC) console graphics characters for tree indentation lines."
HELP_COLOR = (
    "Force enable or disable ANSI color output "
    "(defaults to auto-detection with NO_COLOR compliance)."
)
HELP_ABSOLUTE = "Output absolute paths rather than paths relative to the traversal root."
HELP_PRINT0 = r"Delimit path outputs with a NUL (\0) character instead of a newline."
HELP_LIST_TAGS = "Display identified tags alongside each matched path."
HELP_SUMMARY = "Print summary match statistics to stderr."
HELP_KNOWN_TAGS = "List all known classification tags supported by the engine and exit."
HELP_VERBOSE = "Enable verbose output or extended runtime diagnostics with --version."
HELP_DIAGNOSTICS = "Display runtime environment diagnostics and exit."
HELP_VERSION = "Display the version of findfmt and exit."
HELP_HELP_ALL = (
    "Display comprehensive help reference including environment variables, "
    "exit codes, and examples."
)


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
        "  --format, -f <fmt>            Output format (text, json, jsonl, yaml, ipynb,\n"
        "                                csv, csv-table, tsv, markdown, rst, table, tree)\n"
        "                                [default: text].\n"
        "  --tree / --no-tree            Render output in hierarchical tree view.\n"
        "  --table-style <style>         Border style (rounded, cp437, ascii, etc.).\n"
        "  --pager, -P / --no-pager      Enable or disable interactive paging.\n"
        "  --no-indent, -i / --indent    Omit indentation lines and strip extraneous whitespace.\n"
        "  --ansi-lines, -A              Use ANSI/VT100 line drawing escapes.\n"
        "  --cp437, -S                   Use CP437 console graphics line drawing characters.\n"
        "  --color, -C / --no-color, -n  Force enable or disable ANSI color output.\n"
        "  --absolute, --full-path       Output absolute paths rather than relative paths.\n"
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


def help_all_callback(
    ctx: typer.Context | bool | None = None,
    value: bool = False,
) -> None:
    """Display comprehensive help reference and exit.

    Args:
        ctx: Typer context, if provided by Click callback.
        value: Boolean flag indicating if help-all flag was passed.

    Raises:
        typer.Exit: Upon printing comprehensive help reference.
    """
    if isinstance(ctx, bool):
        value = ctx
        ctx = None

    if value:
        display_with_pager(get_help_all(), ctx=ctx)
        raise typer.Exit(code=0)


def known_tags_callback(
    ctx: typer.Context | bool | None = None,
    value: bool = False,
) -> None:
    """List all known classification tags supported by the engine and exit.

    Args:
        ctx: Typer context, if provided by Click callback.
        value: Boolean flag indicating if known-tags flag was passed.

    Raises:
        typer.Exit: Upon printing known tags.
    """
    if isinstance(ctx, bool):
        value = ctx
        ctx = None

    if value:
        content = "".join(f"{tag}\n" for tag in sorted(get_known_tags()))
        display_with_pager(content, ctx=ctx)
        raise typer.Exit(code=0)
