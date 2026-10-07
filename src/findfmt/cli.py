"""Command-line interface for findfmt."""

from __future__ import annotations

import copy
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


def version_callback(value: bool) -> None:
    """Display the version of findfmt and exit.

    Args:
        value: Boolean flag indicating if version flag was passed.

    Raises:
        typer.Exit: Upon printing version.
    """
    if value:
        sys.stdout.write(f"findfmt {get_version()}\n")
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
            help="Tag or comma-separated tags to match (e.g. 'python', 'yaml,json', 'executable').",
        ),
    ] = None,
    exclude_tags: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude",
            "-e",
            "--exclude-tag",
            help="Tag or comma-separated tags to exclude.",
        ),
    ] = None,
    all_tags: Annotated[
        bool,
        typer.Option(
            "--all-tags",
            help="Require matching files to have ALL specified tags rather than ANY tag.",
        ),
    ] = False,
    shebang: Annotated[
        str | None,
        typer.Option(
            "--shebang",
            help="Filter files whose shebang contains this interpreter or pattern.",
        ),
    ] = None,
    no_ignore: Annotated[
        bool,
        typer.Option(
            "--no-ignore",
            help="Do not respect .gitignore rules during traversal.",
        ),
    ] = False,
    hidden: Annotated[
        bool,
        typer.Option(
            "--hidden",
            help="Include hidden files and directories.",
        ),
    ] = False,
    follow_symlinks: Annotated[
        bool,
        typer.Option(
            "--follow-symlinks",
            "-L",
            help="Follow symbolic links during traversal.",
        ),
    ] = False,
    absolute: Annotated[
        bool,
        typer.Option(
            "--absolute",
            help="Output absolute paths rather than paths relative to the traversal root.",
        ),
    ] = False,
    print0: Annotated[
        bool,
        typer.Option(
            "--print0",
            "-0",
            help=r"Delimit path outputs with a NUL (\0) character instead of a newline.",
        ),
    ] = False,
    list_tags: Annotated[
        bool,
        typer.Option(
            "--list-tags",
            "-l",
            help="Display identified tags alongside each matched path.",
        ),
    ] = False,
    summary: Annotated[
        bool,
        typer.Option(
            "--summary",
            "-s",
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
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            is_eager=True,
            callback=version_callback,
            help="Display the version of findfmt and exit.",
        ),
    ] = None,
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

    try:
        cmd.main(
            args=list(argv) if argv is not None else None,
            prog_name=info_name,
            default_map=defaults,
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
