"""Command-line interface for findfmt."""

from __future__ import annotations

import typer

from findfmt.cli import help as h
from findfmt.cli import runner
from findfmt.cli.options import (
    OptAbsolute,
    OptAllTags,
    OptAnsiLines,
    OptClassify,
    OptColor,
    OptConfig,
    OptCp437,
    OptCtime,
    OptDevice,
    OptDiagnostics,
    OptDirsFirst,
    OptDirsOnly,
    OptDu,
    OptExcludePattern,
    OptExcludeTags,
    OptFileLimit,
    OptFilesFirst,
    OptFollowSymlinks,
    OptFromFile,
    OptGitignoreFile,
    OptGroup,
    OptHelpAll,
    OptHidden,
    OptHideControlChars,
    OptHtml,
    OptHumanReadable,
    OptHyperlink,
    OptHyperlinkAuthority,
    OptHyperlinkSchema,
    OptIgnoreCase,
    OptInodes,
    OptIntro,
    OptJson,
    OptKnownTags,
    OptListTags,
    OptLiteral,
    OptLocale,
    OptMatchDirs,
    OptMaxDepth,
    OptMtime,
    OptNoConfig,
    OptNoIgnore,
    OptNoIndent,
    OptNoLinks,
    OptOffline,
    OptOneFileSystem,
    OptOutput,
    OptOutputFormat,
    OptOutro,
    OptPager,
    OptPaths,
    OptPattern,
    OptPermissions,
    OptPrint0,
    OptPrune,
    OptQuoteName,
    OptRelative,
    OptReverse,
    OptShebang,
    OptShowConfig,
    OptSi,
    OptSize,
    OptSort,
    OptSummary,
    OptTableStyle,
    OptTags,
    OptTimeFormat,
    OptTitle,
    OptTree,
    OptUnsorted,
    OptUser,
    OptVerbose,
    OptVersion,
    OptXml,
    show_config_callback,
)
from findfmt.cli.pager import FindfmtCommand
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
    "show_config_callback",
    "version_callback",
]

app = typer.Typer(
    name="findfmt",
    help=h.APP_HELP,
    add_completion=False,
    no_args_is_help=False,
    context_settings={"help_option_names": ["--help"]},
)


@app.command(name="findfmt", cls=FindfmtCommand, help=h.APP_HELP, epilog=h.CLI_EPILOG)
def findfmt(
    paths: OptPaths = None,
    tags: OptTags = None,
    exclude_tags: OptExcludeTags = None,
    all_tags: OptAllTags = False,
    pattern: OptPattern = None,
    exclude_pattern: OptExcludePattern = None,
    ignore_case: OptIgnoreCase = False,
    match_dirs: OptMatchDirs = False,
    shebang: OptShebang = None,
    no_ignore: OptNoIgnore = False,
    gitignore_file: OptGitignoreFile = None,
    from_file: OptFromFile = None,
    offline: OptOffline = False,
    hidden: OptHidden = False,
    follow_symlinks: OptFollowSymlinks = False,
    dirs_only: OptDirsOnly = False,
    one_file_system: OptOneFileSystem = False,
    max_depth: OptMaxDepth = None,
    file_limit: OptFileLimit = None,
    prune: OptPrune = False,
    sort: OptSort = None,
    reverse: OptReverse = False,
    unsorted: OptUnsorted = False,
    dirs_first: OptDirsFirst = False,
    files_first: OptFilesFirst = False,
    output_format: OptOutputFormat = OutputFormat.TEXT,
    output: OptOutput = None,
    tree: OptTree = False,
    json: OptJson = False,
    xml: OptXml = False,
    html: OptHtml = None,
    intro: OptIntro = None,
    outro: OptOutro = None,
    title: OptTitle = None,
    no_links: OptNoLinks = False,
    hyperlink: OptHyperlink = False,
    hyperlink_schema: OptHyperlinkSchema = "file://",
    hyperlink_authority: OptHyperlinkAuthority = None,
    table_style: OptTableStyle = None,
    pager: OptPager = None,
    no_indent: OptNoIndent = False,
    ansi_lines: OptAnsiLines = False,
    cp437: OptCp437 = False,
    color: OptColor = None,
    absolute: OptAbsolute = False,
    relative: OptRelative = False,
    permissions: OptPermissions = False,
    user: OptUser = False,
    group: OptGroup = False,
    size: OptSize = False,
    human_readable: OptHumanReadable = False,
    si: OptSi = False,
    du: OptDu = False,
    inodes: OptInodes = False,
    device: OptDevice = False,
    mtime: OptMtime = False,
    ctime: OptCtime = False,
    time_format: OptTimeFormat = None,
    classify: OptClassify = False,
    hide_control_chars: OptHideControlChars = False,
    literal: OptLiteral = False,
    quote_name: OptQuoteName = False,
    print0: OptPrint0 = False,
    list_tags: OptListTags = False,
    summary: OptSummary = False,
    known_tags: OptKnownTags = False,
    verbose: OptVerbose = False,
    diagnostics: OptDiagnostics = False,
    version: OptVersion = None,
    help_all: OptHelpAll = False,
    locale: OptLocale = None,
    config: OptConfig = None,
    no_config: OptNoConfig = False,
    show_config: OptShowConfig = False,
) -> None:
    """Execute file discovery and classification matching."""
    params = {
        k: v
        for k, v in locals().items()
        if k
        not in {
            "known_tags",
            "verbose",
            "diagnostics",
            "version",
            "help_all",
            "config",
            "no_config",
            "show_config",
        }
    }
    runner.execute_findfmt(**params)


if __name__ == "__main__":  # pragma: no cover
    app()
