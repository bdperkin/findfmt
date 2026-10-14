"""Comprehensive help reference manual and tag inspection callbacks."""

from __future__ import annotations

import typer

from findfmt.classifier import get_known_tags
from findfmt.cli.pager import display_with_pager
from findfmt.diagnostics import get_version

__all__ = [
    "APP_HELP",
    "CLI_EPILOG",
    "HELP_ABSOLUTE",
    "HELP_ALL_TAGS",
    "HELP_ANSI_LINES",
    "HELP_CLASSIFY",
    "HELP_COLOR",
    "HELP_CP437",
    "HELP_CTIME",
    "HELP_DEVICE",
    "HELP_DIAGNOSTICS",
    "HELP_DIRS_FIRST",
    "HELP_DIRS_ONLY",
    "HELP_DU",
    "HELP_EXCLUDE_PATTERN",
    "HELP_EXCLUDE_TAGS",
    "HELP_FILES_FIRST",
    "HELP_FILE_LIMIT",
    "HELP_FOLLOW_SYMLINKS",
    "HELP_FORMAT",
    "HELP_FROM_FILE",
    "HELP_GITIGNORE_FILE",
    "HELP_GROUP",
    "HELP_HELP_ALL",
    "HELP_HIDDEN",
    "HELP_HIDE_CONTROL_CHARS",
    "HELP_HTML",
    "HELP_HUMAN_READABLE",
    "HELP_IGNORE_CASE",
    "HELP_INODES",
    "HELP_INTRO",
    "HELP_KNOWN_TAGS",
    "HELP_LIST_TAGS",
    "HELP_LITERAL",
    "HELP_MATCH_DIRS",
    "HELP_MAX_DEPTH",
    "HELP_MTIME",
    "HELP_NO_IGNORE",
    "HELP_NO_INDENT",
    "HELP_NO_LINKS",
    "HELP_OFFLINE",
    "HELP_ONE_FILE_SYSTEM",
    "HELP_OUTPUT",
    "HELP_OUTRO",
    "HELP_PAGER",
    "HELP_PATHS",
    "HELP_PATTERN",
    "HELP_PERMISSIONS",
    "HELP_PRINT0",
    "HELP_PRUNE",
    "HELP_QUOTE_NAME",
    "HELP_RELATIVE",
    "HELP_REVERSE",
    "HELP_SHEBANG",
    "HELP_SI",
    "HELP_SIZE",
    "HELP_SORT",
    "HELP_SUMMARY",
    "HELP_TABLE_STYLE",
    "HELP_TAGS",
    "HELP_TIME_FORMAT",
    "HELP_TITLE",
    "HELP_TREE",
    "HELP_UNSORTED",
    "HELP_USER",
    "HELP_VERBOSE",
    "HELP_VERSION",
    "HELP_XML",
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
HELP_GITIGNORE_FILE = "Load and enforce an external gitignore file across the traversal scope."
HELP_FROM_FILE = (
    "Read directory listing from a file or standard input ('-') instead of scanning filesystem."
)
HELP_OFFLINE = "Enforce offline extension- and filename-only identification without disk IO."
HELP_HIDDEN = "Include hidden files and directories."
HELP_FOLLOW_SYMLINKS = "Follow symbolic links during traversal."
HELP_DIRS_ONLY = "List directories only, suppressing regular file entries."
HELP_ONE_FILE_SYSTEM = "Confine traversal to the root filesystem device."
HELP_MAX_DEPTH = "Restrict descent to a maximum directory depth level."
HELP_FILE_LIMIT = "Skip directories exceeding this entry count threshold."
HELP_PRUNE = "Omit empty directories and directories with zero matching files."
HELP_PATTERN = "Include files matching wildcard or glob pattern (supports multiple -P and '|')."
HELP_EXCLUDE_PATTERN = (
    "Exclude files matching wildcard or glob pattern (supports multiple -I and '|')."
)
HELP_IGNORE_CASE = "Apply case-insensitive matching across -P and -I patterns."
HELP_MATCH_DIRS = "Match directory names against patterns; matched dirs inherit to children."
HELP_SORT = "Sort files by criteria: name, version, time (mtime), ctime, size, none."
HELP_REVERSE = "Invert the active sort order."
HELP_UNSORTED = (
    "Do not sort entries; yield files in raw filesystem order (equivalent to --sort=none)."
)
HELP_DIRS_FIRST = "List directories before files within each directory level."
HELP_FILES_FIRST = "List files before directories within each directory level."
HELP_FORMAT = (
    "Output format (text, json, jsonl, yaml, ipynb, csv, csv-table, tsv, "
    "markdown, md, rst, table, tree, xml, html, ndjson)."
)
HELP_XML = "Output directory tree as an XML document (equivalent to --format xml)."
HELP_HTML = "Output directory tree as an HTML document with HTTP reference hyperlinks."
HELP_INTRO = "Read and insert contents of specified HTML fragment file prior to directory listing."
HELP_OUTRO = "Read and insert contents of specified HTML fragment file after directory listing."
HELP_TITLE = "Set title and <h1> heading for HTML document output (default: 'Directory Tree')."
HELP_NO_LINKS = "Suppress hyperlink anchors in HTML document output, rendering plain text paths."
HELP_HYPERLINK = "Wrap paths in standard OSC 8 clickable terminal hyperlink escape sequences."
HELP_HYPERLINK_SCHEMA = (
    "URI schema for terminal hyperlinks (defaults to 'file://', e.g. "
    "'vscode://file/', 'cursor://file/', 'subl://')."
)
HELP_HYPERLINK_AUTHORITY = (
    "URI authority component for terminal hyperlinks (e.g. 'localhost' or remote hostname)."
)
HELP_OUTPUT = "Send command output directly to a file rather than standard output."
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
HELP_RELATIVE = (
    "Prepend input search path prefix to relative output paths rather than stripping the root."
)
HELP_PRINT0 = r"Delimit path outputs with a NUL (\0) character instead of a newline."
HELP_LIST_TAGS = "Display identified tags alongside each matched path."
HELP_SUMMARY = "Print summary match statistics to stderr."
HELP_PERMISSIONS = "Print file type and permissions in standard ls -l format (e.g. -rw-r--r--)."
HELP_USER = "Print the username, or UID if username is unavailable, of the file owner."
HELP_GROUP = "Print the group name, or GID if group name is unavailable, of the file group."
HELP_INODES = "Print filesystem inode number (st_ino)."
HELP_DEVICE = "Print filesystem device number (st_dev)."
HELP_SIZE = "Print file size in bytes."
HELP_HUMAN_READABLE = "Print file sizes in human-readable binary format (e.g. 1K, 234M, 2G)."
HELP_SI = "Print file sizes in human-readable SI metric format (e.g. 1kB, 234MB, 2GB)."
HELP_DU = "Report directory size as the recursive sum of all child files and subdirectories."
HELP_MTIME = "Print the date and time of the last modification (st_mtime)."
HELP_CTIME = "Print the date and time of the last status change (st_ctime)."
HELP_TIME_FORMAT = (
    "Specify date and time output format string (strftime syntax; implies -D unless --ctime)."
)
HELP_CLASSIFY = (
    "Append file type indicator to filenames (* for executable, / for directory, "
    "@ for symlink, = for socket, | for FIFO, > for door)."
)
HELP_HIDE_CONTROL_CHARS = "Replace non-printable control characters in filenames with '?'."
HELP_LITERAL = "Print non-printable control characters literally as raw bytes without masking."
HELP_QUOTE_NAME = "Enclose filenames in double quotes, escaping embedded quotes and backslashes."
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
        "  --pattern, -P <pattern>       Include files matching wildcard or glob pattern.\n"
        "  --exclude-pattern, -I <pat>   Exclude files matching wildcard or glob pattern.\n"
        "  --ignore-case                 Case-insensitive pattern matching across -P and -I.\n"
        "  --match-dirs, --matchdirs     Match directory names; matched dirs inherit to children.\n"
        "  --shebang <str>               Filter files by shebang pattern.\n"
        "  --dirs-only, -d               List directories only, suppressing regular files.\n"
        "  --max-depth, -L <level>       Restrict descent to maximum depth level.\n"
        "  --follow-links, --follow-symlinks, -l\n"
        "                                Follow directory symlinks with loop detection.\n"
        "  --symlinks / --no-symlinks    Alias for --follow-links / --no-follow-links.\n"
        "  --one-file-system, -x         Confine traversal to root filesystem device.\n"
        "  --filelimit <limit>           Skip directories exceeding entry count threshold.\n"
        "  --prune                       Omit directories containing zero matching files.\n"
        "  --no-ignore / --ignore        Do not respect .gitignore rules [default: ignore].\n"
        "  --gitignore-file <path>       Apply custom ignore file across traversal scope.\n"
        "  --from-file, --fromfile <p>   Read paths from file or standard input ('-').\n"
        "  --offline                     Enforce offline filename identification.\n"
        "  --all, --hidden, -a           Include hidden files and dirs [default: no-hidden].\n"
        "  --sort <criteria>             Sort files (name, version, time, ctime, size, none)\n"
        "                                [default: name].\n"
        "  --reverse, -r                 Invert active sort order.\n"
        "  --unsorted, -U                Raw directory order without sorting.\n"
        "  --dirsfirst                   List directories before files within directory levels.\n"
        "  --filesfirst                  List files before directories within directory levels.\n\n"
        "Output Formatting:\n"
        "  --format, -f <fmt>            Output format (text, json, jsonl, yaml, ipynb,\n"
        "                                csv, csv-table, tsv, markdown, rst, table, tree,\n"
        "                                xml, html) [default: text].\n"
        "  --xml, -X / --no-xml          Output directory tree as an XML document.\n"
        "  --html, -H <baseHREF>         Output directory tree as an HTML document.\n"
        "  --intro <path>                Prepend custom HTML fragment before listing.\n"
        "  --outro <path>                Append custom HTML fragment after listing.\n"
        "  --title, -T <title>           Set title and <h1> heading for HTML output.\n"
        "  --nolinks / --no-nolinks      Suppress hyperlink anchors in HTML output.\n"
        "  --hyperlink / --no-hyperlink  Wrap paths in OSC 8 terminal hyperlinks.\n"
        "  --hyperlink-schema <schema>   URI schema prefix (default: file://).\n"
        "  --hyperlink-authority <auth>  URI authority override (e.g. localhost).\n"
        "  --output, -o <path>           Send command output directly to a file.\n"
        "  --tree / --no-tree            Render output in hierarchical tree view.\n"
        "  --table-style <style>         Border style (rounded, cp437, ascii, etc.).\n"
        "  --pager / --no-pager          Enable or disable interactive paging.\n"
        "  --no-indent, -i / --indent    Omit indentation lines and strip extraneous whitespace.\n"
        "  --ansi-lines, -A              Use ANSI/VT100 line drawing escapes.\n"
        "  --cp437, -S                   Use CP437 console graphics line drawing characters.\n"
        "  --color, -C / --no-color, -n  Force enable or disable ANSI color output.\n"
        "  --absolute, --full-path       Output absolute paths rather than relative paths.\n"
        "  --relative, --relative-path   Prepend input search path prefix to relative paths.\n"
        "  --permissions, -p             Format file mode in standard ls -l style.\n"
        "  --user, -u                    Display file owner username (falling back to UID).\n"
        "  --group, -g                   Display file owner group (falling back to GID).\n"
        "  --inodes                      Print filesystem inode number (st_ino).\n"
        "  --device                      Print filesystem device number (st_dev).\n"
        "  --size / --no-size            Print file size in bytes.\n"
        "  --human-readable, -h          Print sizes in human-readable binary format.\n"
        "  --si / --no-si                Print sizes in human-readable SI metric format.\n"
        "  --du, --accumulate-size       Accumulate recursive directory disk usage.\n"
        "  --mtime, -D                   Display last modification time.\n"
        "  --ctime                       Display last status change time.\n"
        "  --time-format, --timefmt <f>  Date and time format string (strftime syntax).\n"
        "  --classify, -F                Append indicator (/ @ * = | >) to filenames.\n"
        "  --hide-control-chars, -q      Mask non-printable control characters with '?'.\n"
        "  --literal, -N                 Print non-printable characters literally.\n"
        "  --quote-name, -Q              Enclose filenames in double quotes.\n"
        "  --print0, -0 / --no-print0    Delimit with NUL (\\0) byte [default: no-print0].\n"
        "  --list-tags / --no-list-tags  Display identified tags [default: no-list-tags].\n"
        "  --summary, -s / --no-summary  Print summary statistics [default: no-summary].\n\n"
        "Help & Diagnostics:\n"
        "  --known-tags                  List all known classification tags and exit.\n"
        "  --version, -v, -V             Display version (use with --verbose for diagnostics).\n"
        "  --verbose                     Enable verbose output or extended runtime diagnostics.\n"
        "  --diagnostics                 Display runtime environment diagnostics and exit.\n"
        "  --help-all                    Display this comprehensive reference and exit.\n"
        "  --help                        Display categorized help summary and exit.\n\n"
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
