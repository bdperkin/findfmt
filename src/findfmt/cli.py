"""Command-line interface for findfmt."""

from __future__ import annotations

import copy
import inspect
import platform
import shutil
import subprocess
import sys
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

from findfmt.classifier import get_known_tags
from findfmt.models import TraversalConfig
from findfmt.traversal import find_files

if TYPE_CHECKING:
    from collections.abc import Sequence

    from findfmt.models import FileInfo

__all__ = [
    "app",
    "get_diagnostics",
    "get_git_version",
    "get_help_all",
    "get_version",
    "main",
    "main_findfilefmt",
    "main_findfilemime",
    "main_findfiles",
    "main_findfmt0",
    "main_findshebang",
    "main_findsummary",
]


def get_version() -> str:
    """Retrieve package version or fallback string.

    Returns:
        Version string.
    """
    try:
        return version("findfmt")
    except PackageNotFoundError:
        return "0.1.1.dev0"


def get_git_version() -> str | None:
    """Retrieve git executable version string if git is available.

    Returns:
        Git version string or None if git is not detected.
    """
    git_path = shutil.which("git")
    if not git_path:
        return None

    try:
        proc = subprocess.run(  # noqa: S603
            [git_path, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    return None


def get_diagnostics() -> str:
    """Compile runtime environment diagnostics.

    Returns:
        Formatted multi-line diagnostics string ending in a newline.
    """
    lines: list[str] = [f"findfmt {get_version()}"]
    py_ver = sys.version.split()[0]
    plat = platform.platform()
    lines.append(f"Python: {py_ver} ({plat})")

    try:
        identify_ver = version("identify")
    except PackageNotFoundError:
        identify_ver = "not installed"

    lines.append(f"identify: {identify_ver}")

    git_ver = get_git_version()
    lines.append(f"Git: {git_ver or 'not found'}")

    return "\n".join(lines) + "\n"


def _is_in_context(ctx: object) -> bool:
    """Check if verbose output or diagnostics was requested in context.

    Args:
        ctx: Click/Typer context, if available.

    Returns:
        True if requested in context, False otherwise.
    """
    params = getattr(ctx, "params", {})
    if params.get("verbose") or params.get("diagnostics"):
        return True

    ctx_obj = getattr(ctx, "obj", None)
    if isinstance(ctx_obj, dict):
        raw_argv = ctx_obj.get("argv", [])
        return "--verbose" in raw_argv or "--diagnostics" in raw_argv

    return False


def _is_in_frames() -> bool:
    """Check if verbose output or diagnostics was requested in caller frames.

    Returns:
        True if requested in caller frames, False otherwise.
    """
    frame = inspect.currentframe()
    while frame:
        opts = frame.f_locals.get("opts")
        if isinstance(opts, dict) and (opts.get("verbose") or opts.get("diagnostics")):
            return True

        frame = frame.f_back

    return False


def _is_verbose_requested(ctx: object = None) -> bool:
    """Check if verbose output or diagnostics was requested.

    Args:
        ctx: Click/Typer context, if available.

    Returns:
        True if verbose or diagnostics is requested, False otherwise.
    """
    if ctx is not None and _is_in_context(ctx):
        return True

    if _is_in_frames():
        return True

    return "--verbose" in sys.argv or "--diagnostics" in sys.argv


def version_callback(
    ctx: typer.Context | bool | None = None,
    value: bool = False,
) -> None:
    """Display the version of findfmt and exit.

    Args:
        ctx: Typer context, if provided by Click callback.
        value: Boolean flag indicating if version flag was passed.

    Raises:
        typer.Exit: Upon printing version.
    """
    if isinstance(ctx, bool):
        value = ctx
        ctx = None

    if value:
        if _is_verbose_requested(ctx):
            sys.stdout.write(get_diagnostics())
        else:
            sys.stdout.write(f"findfmt {get_version()}\n")

        raise typer.Exit(code=0)


def diagnostics_callback(value: bool) -> None:
    """Display runtime environment diagnostics and exit.

    Args:
        value: Boolean flag indicating if diagnostics flag was passed.

    Raises:
        typer.Exit: Upon printing diagnostics.
    """
    if value:
        sys.stdout.write(get_diagnostics())
        raise typer.Exit(code=0)


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


def parse_tag_arguments(tag_args: Sequence[str] | None) -> frozenset[str]:
    """Parse repeatable or comma-delimited tag arguments into a normalized frozenset.

    Args:
        tag_args: Raw arguments provided to tag filter flags.

    Returns:
        frozenset of lowercase tag strings.
    """
    if not tag_args:
        return frozenset[str]()

    result: set[str] = set()
    for arg in tag_args:
        for tag in arg.split(","):
            cleaned = tag.strip().lower()
            if cleaned:
                result.add(cleaned)

    return frozenset(result)


def _format_match(file_info: FileInfo, *, absolute: bool, show_tags: bool, delimiter: str) -> str:
    """Format matching file information for stdout output.

    Args:
        file_info: Classified file information.
        absolute: Whether to format using absolute path.
        show_tags: Whether to append comma-separated tags.
        delimiter: End of line delimiter string.

    Returns:
        Formatted string for output.
    """
    path_str = str(file_info.path if absolute else file_info.relative_path)
    if show_tags:
        tags_repr = ", ".join(sorted(file_info.tags))
        return f"{path_str} [{tags_repr}]{delimiter}"

    return f"{path_str}{delimiter}"


def _write_summary(match_count: int, tag_counter: Counter[str]) -> None:
    """Write execution summary to stderr.

    Args:
        match_count: Total number of files matched.
        tag_counter: Frequency counter of tags matched.
    """
    sys.stderr.write(f"\n--- findfmt summary ---\nMatched files: {match_count}\n")
    if tag_counter:
        sys.stderr.write("Top tags:\n")
        for tag, count in tag_counter.most_common(10):
            sys.stderr.write(f"  {tag}: {count}\n")


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
    root_paths = tuple(paths) if paths else (Path(),)
    config = TraversalConfig(
        root_paths=root_paths,
        include_tags=parse_tag_arguments(tags),
        exclude_tags=parse_tag_arguments(exclude_tags),
        all_tags=all_tags,
        shebang_filter=shebang,
        respect_gitignore=not no_ignore,
        include_hidden=hidden,
        follow_symlinks=follow_symlinks,
        relative_paths=not absolute,
        null_delimited=print0,
        show_tags=list_tags,
        show_summary=summary,
    )

    tag_counter: Counter[str] = Counter()
    match_count = 0
    delimiter = "\0" if config.null_delimited else "\n"

    for file_info in find_files(config):
        match_count += 1
        if config.show_summary:
            tag_counter.update(file_info.tags)

        formatted = _format_match(
            file_info,
            absolute=absolute,
            show_tags=config.show_tags,
            delimiter=delimiter,
        )
        sys.stdout.write(formatted)

    if config.show_summary:
        _write_summary(match_count, tag_counter)


_OPTIONS_WITH_VALUE: frozenset[str] = frozenset(
    {
        "-t",
        "--type",
        "--tag",
        "-e",
        "--exclude",
        "--exclude-tag",
        "--shebang",
    },
)


def _has_option(args: Sequence[str], option_names: set[str] | frozenset[str]) -> bool:
    """Check if any option name or prefix is present in args.

    Args:
        args: Sequence of command-line arguments.
        option_names: Set of option flag names to check.

    Returns:
        True if any option matches, False otherwise.
    """
    return any(
        arg in option_names or any(arg.startswith(f"{opt}=") for opt in option_names)
        for arg in args
    )


def _consume_option(arg: str, next_arg: str | None) -> int:
    """Return number of arguments consumed by this option flag.

    Args:
        arg: Current argument string.
        next_arg: Subsequent argument string, if available.

    Returns:
        Number of arguments consumed (1 or 2).
    """
    if "=" in arg or arg not in _OPTIONS_WITH_VALUE:
        return 1

    return 2 if next_arg is not None else 1


def _extract_first_positional(args: Sequence[str]) -> tuple[str | None, list[str]]:
    """Extract the first positional argument from args, preserving option structure.

    Args:
        args: Sequence of raw command-line tokens.

    Returns:
        Tuple of (first positional argument or None, remaining arguments).
    """
    first_pos: str | None = None
    remaining: list[str] = []
    i = 0
    passthrough = False

    while i < len(args):
        arg = args[i]
        if not passthrough and arg.startswith("-") and arg != "-":
            if arg == "--":
                passthrough = True
                remaining.append(arg)
                i += 1
            else:
                next_arg = args[i + 1] if i + 1 < len(args) else None
                count = _consume_option(arg, next_arg)
                remaining.extend(args[i : i + count])
                i += count

            continue

        if first_pos is None:
            first_pos = arg
        else:
            remaining.append(arg)

        i += 1

    return first_pos, remaining


def _invoke_with_defaults(
    info_name: str,
    defaults: dict[str, Any],
    argv: Sequence[str] | None = None,
    help_text: str | None = None,
) -> int:
    """Helper to invoke the main Typer command with injected default options.

    Args:
        info_name: Command name to display in usage and help.
        defaults: Default options to inject into Click context.
        argv: Optional command-line arguments (defaults to sys.argv[1:]).
        help_text: Optional custom help text for the command.

    Returns:
        Integer exit code (0 for success, non-zero on error).
    """
    cmd = typer.main.get_command(app)
    if help_text is not None:
        cmd = copy.copy(cmd)
        cmd.help = help_text

    args_list = list(argv) if argv is not None else None
    try:
        cmd.main(
            args=args_list,
            prog_name=info_name,
            default_map=defaults,
            obj={"argv": args_list if args_list is not None else list(sys.argv[1:])},
        )
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0

    return 0  # pragma: no cover


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entrypoint for findfmt.

    Args:
        argv: Optional command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Integer exit code (0 for success, non-zero on error).
    """
    return _invoke_with_defaults("findfmt", {}, argv=argv)


def main_findfiles(argv: Sequence[str] | None = None) -> int:
    """Entry point for 'findfiles' (findfmt --hidden).

    Args:
        argv: Optional command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Integer exit code (0 for success, non-zero on error).
    """
    return _invoke_with_defaults(
        "findfiles",
        {"hidden": True},
        argv=argv,
        help_text="Find all files and directories, including hidden files respecting .gitignore.",
    )


def main_findfilemime(argv: Sequence[str] | None = None) -> int:
    """Entry point for 'findfilemime' (findfmt --hidden --list-tags).

    Args:
        argv: Optional command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Integer exit code (0 for success, non-zero on error).
    """
    return _invoke_with_defaults(
        "findfilemime",
        {"hidden": True, "list_tags": True},
        argv=argv,
        help_text=(
            "Find files and list detected format and MIME tags, "
            "including hidden files respecting .gitignore."
        ),
    )


def main_findfilefmt(argv: Sequence[str] | None = None) -> int:
    """Entry point for 'findfilefmt' (findfmt --hidden [--tag TAG]).

    Args:
        argv: Optional command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Integer exit code (0 for success, non-zero on error).
    """
    raw_args = list(argv) if argv is not None else list(sys.argv[1:])
    defaults: dict[str, Any] = {"hidden": True}

    if not _has_option(raw_args, {"-t", "--type", "--tag"}):
        first_pos, remaining = _extract_first_positional(raw_args)

        if first_pos is not None:
            raw_args = ["--tag", first_pos, *remaining]

    return _invoke_with_defaults(
        "findfilefmt",
        defaults,
        argv=raw_args,
        help_text=(
            "Find files by format tag, including hidden files respecting .gitignore.\n\n"
            "Optionally provide TAG as the first positional argument (e.g. 'findfilefmt python')."
        ),
    )


def main_findshebang(argv: Sequence[str] | None = None) -> int:
    """Entry point for 'findshebang' (findfmt --hidden [--shebang INTERPRETER]).

    Args:
        argv: Optional command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Integer exit code (0 for success, non-zero on error).
    """
    raw_args = list(argv) if argv is not None else list(sys.argv[1:])
    defaults: dict[str, Any] = {"hidden": True}

    if not _has_option(raw_args, {"--shebang"}):
        first_pos, remaining = _extract_first_positional(raw_args)

        if first_pos is not None:
            raw_args = ["--shebang", first_pos, *remaining]

    return _invoke_with_defaults(
        "findshebang",
        defaults,
        argv=raw_args,
        help_text=(
            "Find files by shebang interpreter pattern, including hidden files respecting "
            ".gitignore.\n\n"
            "Optionally provide INTERPRETER as the first positional argument "
            "(e.g. 'findshebang bash')."
        ),
    )


def main_findfmt0(argv: Sequence[str] | None = None) -> int:
    """Entry point for 'findfmt0' (findfmt --hidden --print0).

    Args:
        argv: Optional command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Integer exit code (0 for success, non-zero on error).
    """
    return _invoke_with_defaults(
        "findfmt0",
        {"hidden": True, "print0": True},
        argv=argv,
        help_text=(
            "Find files and output NUL-delimited paths (--print0), "
            "including hidden files respecting .gitignore."
        ),
    )


def main_findsummary(argv: Sequence[str] | None = None) -> int:
    """Entry point for 'findsummary' (findfmt --hidden --summary).

    Args:
        argv: Optional command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Integer exit code (0 for success, non-zero on error).
    """
    return _invoke_with_defaults(
        "findsummary",
        {"hidden": True, "summary": True},
        argv=argv,
        help_text=(
            "Find files and print summary statistics to stderr, "
            "including hidden files respecting .gitignore."
        ),
    )


if __name__ == "__main__":  # pragma: no cover
    app()
