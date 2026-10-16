"""Typer command-line option definitions and metadata annotations."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from findfmt.cli import help as h
from findfmt.diagnostics import diagnostics_callback, show_config_callback, version_callback
from findfmt.formatters import OutputFormat
from findfmt.i18n import _, locale_callback

help_all_callback = h.help_all_callback
known_tags_callback = h.known_tags_callback

_PT = _("Tag Filtering")
_PC = _("Traversal Controls")
_PO = _("Output Formatting")

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
    typer.Option(
        "-a",
        "--all/--no-all",
        "--hidden/--no-hidden",
        rich_help_panel=_PC,
        help=h.HELP_HIDDEN,
    ),
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
OptJson = Annotated[
    bool,
    typer.Option(
        "-J",
        "--json/--no-json",
        rich_help_panel=_PO,
        help=h.HELP_JSON,
    ),
]
OptXml = Annotated[
    bool,
    typer.Option(
        "-X",
        "--xml/--no-xml",
        rich_help_panel=_PO,
        help=h.HELP_XML,
    ),
]
OptHtml = Annotated[
    str | None,
    typer.Option(
        "-H",
        "--html",
        rich_help_panel=_PO,
        help=h.HELP_HTML,
    ),
]
OptIntro = Annotated[
    Path | None,
    typer.Option(
        "--intro",
        rich_help_panel=_PO,
        help=h.HELP_INTRO,
    ),
]
OptOutro = Annotated[
    Path | None,
    typer.Option(
        "--outro",
        rich_help_panel=_PO,
        help=h.HELP_OUTRO,
    ),
]
OptTitle = Annotated[
    str | None,
    typer.Option(
        "-T",
        "--title",
        rich_help_panel=_PO,
        help=h.HELP_TITLE,
    ),
]
OptNoLinks = Annotated[
    bool,
    typer.Option(
        "--nolinks/--no-nolinks",
        rich_help_panel=_PO,
        help=h.HELP_NO_LINKS,
    ),
]
OptHyperlink = Annotated[
    bool,
    typer.Option(
        "--hyperlink/--no-hyperlink",
        rich_help_panel=_PO,
        help=h.HELP_HYPERLINK,
    ),
]
OptHyperlinkSchema = Annotated[
    str,
    typer.Option(
        "--hyperlink-schema",
        rich_help_panel=_PO,
        help=h.HELP_HYPERLINK_SCHEMA,
    ),
]
OptHyperlinkAuthority = Annotated[
    str | None,
    typer.Option(
        "--hyperlink-authority",
        rich_help_panel=_PO,
        help=h.HELP_HYPERLINK_AUTHORITY,
    ),
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
OptPermissions = Annotated[
    bool,
    typer.Option(
        "-p",
        "--permissions/--no-permissions",
        rich_help_panel=_PO,
        help=h.HELP_PERMISSIONS,
    ),
]
OptUser = Annotated[
    bool,
    typer.Option("-u", "--user/--no-user", rich_help_panel=_PO, help=h.HELP_USER),
]
OptGroup = Annotated[
    bool,
    typer.Option("-g", "--group/--no-group", rich_help_panel=_PO, help=h.HELP_GROUP),
]
OptInodes = Annotated[
    bool,
    typer.Option("--inodes/--no-inodes", rich_help_panel=_PO, help=h.HELP_INODES),
]
OptDevice = Annotated[
    bool,
    typer.Option("--device/--no-device", rich_help_panel=_PO, help=h.HELP_DEVICE),
]
OptSize = Annotated[
    bool,
    typer.Option("--size/--no-size", rich_help_panel=_PO, help=h.HELP_SIZE),
]
OptHumanReadable = Annotated[
    bool,
    typer.Option(
        "-h",
        "--human-readable/--no-human-readable",
        rich_help_panel=_PO,
        help=h.HELP_HUMAN_READABLE,
    ),
]
OptSi = Annotated[
    bool,
    typer.Option("--si/--no-si", rich_help_panel=_PO, help=h.HELP_SI),
]
OptDu = Annotated[
    bool,
    typer.Option(
        "--du/--no-du",
        "--accumulate-size/--no-accumulate-size",
        rich_help_panel=_PO,
        help=h.HELP_DU,
    ),
]
OptMtime = Annotated[
    bool,
    typer.Option("-D", "--mtime/--no-mtime", rich_help_panel=_PO, help=h.HELP_MTIME),
]
OptCtime = Annotated[
    bool,
    typer.Option("--ctime/--no-ctime", rich_help_panel=_PO, help=h.HELP_CTIME),
]
OptTimeFormat = Annotated[
    str | None,
    typer.Option(
        "--time-format",
        "--timefmt",
        rich_help_panel=_PO,
        help=h.HELP_TIME_FORMAT,
    ),
]
OptClassify = Annotated[
    bool,
    typer.Option("-F", "--classify/--no-classify", rich_help_panel=_PO, help=h.HELP_CLASSIFY),
]
OptHideControlChars = Annotated[
    bool,
    typer.Option(
        "-q",
        "--hide-control-chars/--no-hide-control-chars",
        rich_help_panel=_PO,
        help=h.HELP_HIDE_CONTROL_CHARS,
    ),
]
OptLiteral = Annotated[
    bool,
    typer.Option("-N", "--literal/--no-literal", rich_help_panel=_PO, help=h.HELP_LITERAL),
]
OptQuoteName = Annotated[
    bool,
    typer.Option("-Q", "--quote-name/--no-quote-name", rich_help_panel=_PO, help=h.HELP_QUOTE_NAME),
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
OptLocale = Annotated[
    str | None,
    typer.Option(
        "--locale",
        "--lang",
        is_eager=True,
        callback=locale_callback,
        help=h.HELP_LOCALE,
    ),
]
OptConfig = Annotated[
    Path | None,
    typer.Option(
        "--config",
        help=h.HELP_CONFIG,
    ),
]
OptNoConfig = Annotated[
    bool,
    typer.Option(
        "--no-config",
        help=h.HELP_NO_CONFIG,
    ),
]

OptShowConfig = Annotated[
    bool,
    typer.Option(
        "--show-config",
        is_eager=True,
        callback=show_config_callback,
        help=h.HELP_SHOW_CONFIG,
    ),
]
