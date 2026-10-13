"""Typer command-line option definitions and metadata annotations."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from findfmt.cli import help as h
from findfmt.diagnostics import diagnostics_callback, version_callback
from findfmt.formatters import OutputFormat

help_all_callback = h.help_all_callback
known_tags_callback = h.known_tags_callback

_PT = "Tag Filtering"
_PC = "Traversal Controls"
_PO = "Output Formatting"

OptPaths = Annotated[list[Path] | None, typer.Argument(help=h.HELP_PATHS)]
OptTags = Annotated[
    list[str] | None,
    typer.Option("-t", "--type", "--tag", rich_help_panel=_PT, help=h.HELP_TAGS),
]
OptExcludeTags = Annotated[
    list[str] | None,
    typer.Option(
        "-e",
        "--exclude",
        "--exclude-tag",
        rich_help_panel=_PT,
        help=h.HELP_EXCLUDE_TAGS,
    ),
]
OptAllTags = Annotated[
    bool,
    typer.Option("--all-tags/--no-all-tags", rich_help_panel=_PT, help=h.HELP_ALL_TAGS),
]
OptPattern = Annotated[
    list[str] | None,
    typer.Option(
        "-P",
        "--pattern",
        "--include-pattern",
        rich_help_panel=_PC,
        help=h.HELP_PATTERN,
    ),
]
OptExcludePattern = Annotated[
    list[str] | None,
    typer.Option("-I", "--exclude-pattern", rich_help_panel=_PC, help=h.HELP_EXCLUDE_PATTERN),
]
OptIgnoreCase = Annotated[
    bool,
    typer.Option(
        "--ignore-case/--no-ignore-case",
        rich_help_panel=_PC,
        help=h.HELP_IGNORE_CASE,
    ),
]
OptMatchDirs = Annotated[
    bool,
    typer.Option(
        "--match-dirs/--no-match-dirs",
        "--matchdirs/--no-matchdirs",
        rich_help_panel=_PC,
        help=h.HELP_MATCH_DIRS,
    ),
]
OptShebang = Annotated[
    str | None,
    typer.Option("--shebang", rich_help_panel=_PC, help=h.HELP_SHEBANG),
]
OptNoIgnore = Annotated[
    bool,
    typer.Option("--no-ignore/--ignore", rich_help_panel=_PC, help=h.HELP_NO_IGNORE),
]
OptGitignoreFile = Annotated[
    Path | None,
    typer.Option("--gitignore-file", rich_help_panel=_PC, help=h.HELP_GITIGNORE_FILE),
]
OptFromFile = Annotated[
    str | None,
    typer.Option("--from-file", "--fromfile", rich_help_panel=_PC, help=h.HELP_FROM_FILE),
]
OptOffline = Annotated[
    bool,
    typer.Option("--offline", rich_help_panel=_PC, help=h.HELP_OFFLINE),
]
OptHidden = Annotated[
    bool,
    typer.Option("--hidden/--no-hidden", rich_help_panel=_PC, help=h.HELP_HIDDEN),
]
OptFollowSymlinks = Annotated[
    bool,
    typer.Option(
        "-l",
        "--follow-links/--no-follow-links",
        "--follow-symlinks/--no-follow-symlinks",
        "--symlinks/--no-symlinks",
        rich_help_panel=_PC,
        help=h.HELP_FOLLOW_SYMLINKS,
    ),
]
OptDirsOnly = Annotated[
    bool,
    typer.Option("-d", "--dirs-only", rich_help_panel=_PC, help=h.HELP_DIRS_ONLY),
]
OptOneFileSystem = Annotated[
    bool,
    typer.Option("-x", "--one-file-system", rich_help_panel=_PC, help=h.HELP_ONE_FILE_SYSTEM),
]
OptMaxDepth = Annotated[
    int | None,
    typer.Option("-L", "--max-depth", rich_help_panel=_PC, help=h.HELP_MAX_DEPTH),
]
OptFileLimit = Annotated[
    int | None,
    typer.Option("--filelimit", rich_help_panel=_PC, help=h.HELP_FILE_LIMIT),
]
OptPrune = Annotated[
    bool,
    typer.Option("--prune", rich_help_panel=_PC, help=h.HELP_PRUNE),
]
OptSort = Annotated[
    str | None,
    typer.Option("--sort", rich_help_panel=_PC, help=h.HELP_SORT),
]
OptReverse = Annotated[
    bool,
    typer.Option("-r", "--reverse", rich_help_panel=_PC, help=h.HELP_REVERSE),
]
OptUnsorted = Annotated[
    bool,
    typer.Option("-U", "--unsorted", rich_help_panel=_PC, help=h.HELP_UNSORTED),
]
OptDirsFirst = Annotated[
    bool,
    typer.Option(
        "--dirsfirst",
        "--group-directories-first",
        rich_help_panel=_PC,
        help=h.HELP_DIRS_FIRST,
    ),
]
OptFilesFirst = Annotated[
    bool,
    typer.Option("--filesfirst", rich_help_panel=_PC, help=h.HELP_FILES_FIRST),
]
OptOutputFormat = Annotated[
    OutputFormat,
    typer.Option(
        "-f",
        "--format",
        case_sensitive=False,
        rich_help_panel=_PO,
        help=h.HELP_FORMAT,
    ),
]
OptOutput = Annotated[
    Path | None,
    typer.Option("-o", "--output", rich_help_panel=_PO, help=h.HELP_OUTPUT),
]
OptTree = Annotated[
    bool,
    typer.Option("--tree/--no-tree", rich_help_panel=_PO, help=h.HELP_TREE),
]
OptTableStyle = Annotated[
    str | None,
    typer.Option("--table-style", rich_help_panel=_PO, help=h.HELP_TABLE_STYLE),
]
OptPager = Annotated[
    bool | None,
    typer.Option("--pager/--no-pager", rich_help_panel=_PO, help=h.HELP_PAGER),
]
OptNoIndent = Annotated[
    bool,
    typer.Option("-i", "--no-indent/--indent", rich_help_panel=_PO, help=h.HELP_NO_INDENT),
]
OptAnsiLines = Annotated[
    bool,
    typer.Option(
        "-A",
        "--ansi-lines/--no-ansi-lines",
        rich_help_panel=_PO,
        help=h.HELP_ANSI_LINES,
    ),
]
OptCp437 = Annotated[
    bool,
    typer.Option("-S", "--cp437/--no-cp437", rich_help_panel=_PO, help=h.HELP_CP437),
]
OptColor = Annotated[
    bool | None,
    typer.Option("-C/-n", "--color/--no-color", rich_help_panel=_PO, help=h.HELP_COLOR),
]
OptAbsolute = Annotated[
    bool,
    typer.Option(
        "--absolute/--no-absolute",
        "--full-path/--no-full-path",
        rich_help_panel=_PO,
        help=h.HELP_ABSOLUTE,
    ),
]
OptRelative = Annotated[
    bool,
    typer.Option(
        "--relative/--no-relative",
        "--relative-path/--no-relative-path",
        rich_help_panel=_PO,
        help=h.HELP_RELATIVE,
    ),
]
OptPrint0 = Annotated[
    bool,
    typer.Option("-0", "--print0/--no-print0", rich_help_panel=_PO, help=h.HELP_PRINT0),
]
OptListTags = Annotated[
    bool,
    typer.Option("--list-tags/--no-list-tags", rich_help_panel=_PO, help=h.HELP_LIST_TAGS),
]
OptSummary = Annotated[
    bool,
    typer.Option("-s", "--summary/--no-summary", rich_help_panel=_PO, help=h.HELP_SUMMARY),
]
OptKnownTags = Annotated[
    bool,
    typer.Option(
        "--known-tags",
        is_eager=True,
        callback=known_tags_callback,
        help=h.HELP_KNOWN_TAGS,
    ),
]
OptVerbose = Annotated[bool, typer.Option("--verbose", help=h.HELP_VERBOSE)]
OptDiagnostics = Annotated[
    bool,
    typer.Option(
        "--diagnostics",
        is_eager=True,
        callback=diagnostics_callback,
        help=h.HELP_DIAGNOSTICS,
    ),
]
OptVersion = Annotated[
    bool | None,
    typer.Option(
        "-v",
        "-V",
        "--version",
        is_eager=True,
        callback=version_callback,
        help=h.HELP_VERSION,
    ),
]
OptHelpAll = Annotated[
    bool,
    typer.Option("--help-all", is_eager=True, callback=help_all_callback, help=h.HELP_HELP_ALL),
]
