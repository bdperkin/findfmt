"""CLI command wrappers and entry points for specialized aliases."""

from __future__ import annotations

import copy
import sys
from typing import TYPE_CHECKING, Any

import typer

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "main",
    "main_findfilefmt",
    "main_findfilemime",
    "main_findfiles",
    "main_findfmt0",
    "main_findshebang",
    "main_findsummary",
]

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
    from findfmt.cli import app

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
