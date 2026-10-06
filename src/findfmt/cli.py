"""Command-line interface for findfmt."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING

from findfmt.classifier import get_known_tags
from findfmt.models import TraversalConfig
from findfmt.traversal import find_files

if TYPE_CHECKING:
    from collections.abc import Sequence


def get_version() -> str:
    """Retrieve package version or fallback string.

    Returns:
        Version string.
    """
    try:
        return version("findfmt")
    except PackageNotFoundError:
        return "0.1.0.dev0"


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="findfmt",
        description=(
            "A .gitignore-aware file discovery and classification suite that locates "
            "files by content format, shebang, and MIME tag."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="One or more directory or file paths to inspect (default: current directory).",
    )

    parser.add_argument(
        "-t",
        "--type",
        "--tag",
        dest="tags",
        action="append",
        help="Tag or comma-separated tags to match (e.g. 'python', 'yaml,json', 'executable').",
    )

    parser.add_argument(
        "-e",
        "--exclude",
        "--exclude-tag",
        dest="exclude_tags",
        action="append",
        help="Tag or comma-separated tags to exclude.",
    )

    parser.add_argument(
        "--all-tags",
        action="store_true",
        help="Require matching files to have ALL specified tags rather than ANY tag.",
    )

    parser.add_argument(
        "--shebang",
        dest="shebang",
        help="Filter files whose shebang contains this interpreter or pattern.",
    )

    parser.add_argument(
        "--no-ignore",
        action="store_true",
        help="Do not respect .gitignore rules during traversal.",
    )

    parser.add_argument(
        "--hidden",
        action="store_true",
        help="Include hidden files and directories.",
    )

    parser.add_argument(
        "-L",
        "--follow-symlinks",
        action="store_true",
        help="Follow symbolic links during traversal.",
    )

    parser.add_argument(
        "--absolute",
        action="store_true",
        help="Output absolute paths rather than paths relative to the traversal root.",
    )

    parser.add_argument(
        "-0",
        "--print0",
        action="store_true",
        help=r"Delimit path outputs with a NUL (\0) character instead of a newline.",
    )

    parser.add_argument(
        "-l",
        "--list-tags",
        action="store_true",
        help="Display identified tags alongside each matched path.",
    )

    parser.add_argument(
        "-s",
        "--summary",
        action="store_true",
        help="Print summary match statistics to stderr.",
    )

    parser.add_argument(
        "--known-tags",
        action="store_true",
        help="List all known classification tags supported by the engine and exit.",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
    )

    return parser


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


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entrypoint.

    Args:
        argv: Optional command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Integer exit code (0 for success, 1 on error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.known_tags:
        for tag in sorted(get_known_tags()):
            sys.stdout.write(f"{tag}\n")
        return 0

    root_paths = tuple(Path(p) for p in args.paths)
    include_tags = parse_tag_arguments(args.tags)
    exclude_tags = parse_tag_arguments(args.exclude_tags)

    config = TraversalConfig(
        root_paths=root_paths,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        all_tags=args.all_tags,
        shebang_filter=args.shebang,
        respect_gitignore=not args.no_ignore,
        include_hidden=args.hidden,
        follow_symlinks=args.follow_symlinks,
        relative_paths=not args.absolute,
        null_delimited=args.print0,
        show_tags=args.list_tags,
        show_summary=args.summary,
    )

    tag_counter: Counter[str] = Counter()
    match_count = 0
    delimiter = "\0" if config.null_delimited else "\n"

    for file_info in find_files(config):
        match_count += 1
        path_str = str(file_info.path if args.absolute else file_info.relative_path)

        if config.show_summary:
            tag_counter.update(file_info.tags)

        if config.show_tags:
            tags_repr = ", ".join(sorted(file_info.tags))
            sys.stdout.write(f"{path_str} [{tags_repr}]{delimiter}")
        else:
            sys.stdout.write(f"{path_str}{delimiter}")

    if config.show_summary:
        sys.stderr.write(f"\n--- findfmt summary ---\nMatched files: {match_count}\n")
        if tag_counter:
            sys.stderr.write("Top tags:\n")
            for tag, count in tag_counter.most_common(10):
                sys.stderr.write(f"  {tag}: {count}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
