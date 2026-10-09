"""CLI execution and orchestration engine for findfmt."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from findfmt.formatters import OutputFormat, get_formatter
from findfmt.models import TraversalConfig
from findfmt.summary import parse_tag_arguments, write_summary
from findfmt.traversal import find_files

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from findfmt.models import FileInfo

__all__ = ["execute_findfmt"]


def execute_findfmt(  # noqa: PLR0913
    *,
    paths: list[Path] | None,
    tags: list[str] | None,
    exclude_tags: list[str] | None,
    all_tags: bool,
    shebang: str | None,
    no_ignore: bool,
    hidden: bool,
    follow_symlinks: bool,
    output_format: OutputFormat,
    tree: bool,
    table_style: str | None,
    absolute: bool,
    print0: bool,
    list_tags: bool,
    summary: bool,
    find_files_func: Callable[[TraversalConfig], Iterable[FileInfo]] = find_files,
) -> None:
    """Execute file discovery, classification, formatting, and summary reporting.

    Args:
        paths: Directory or file paths to inspect.
        tags: Tags to match.
        exclude_tags: Tags to exclude.
        all_tags: Whether all tags must match.
        shebang: Shebang filter pattern.
        no_ignore: Whether to ignore gitignore rules.
        hidden: Whether to include hidden files.
        follow_symlinks: Whether to follow symbolic links.
        output_format: Configured output serialization format.
        tree: Whether tree view was explicitly requested.
        table_style: Optional table border style name.
        absolute: Whether to emit absolute paths.
        print0: Whether to delimit output with NUL characters.
        list_tags: Whether to display tags in output.
        summary: Whether to display execution summary.
        find_files_func: Traversal generator function to execute.
    """
    effective_format = OutputFormat.TREE if tree else output_format

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
        output_format=effective_format.value,
    )

    tag_counter: Counter[str] = Counter()
    match_count = 0
    delimiter = "\0" if config.null_delimited else "\n"

    formatter_kwargs: dict[str, object] = {}
    if table_style is not None:
        formatter_kwargs["table_style"] = table_style

    formatter = get_formatter(
        effective_format,
        absolute=absolute,
        show_tags=config.show_tags,
        delimiter=delimiter,
        **formatter_kwargs,
    )

    def _matched_files() -> Iterable[FileInfo]:
        """Yield matched files while accumulating frequency statistics."""
        nonlocal match_count
        for file_info in find_files_func(config):
            match_count += 1
            if config.show_summary:
                tag_counter.update(file_info.tags)

            yield file_info

    formatter.stream(_matched_files(), sys.stdout)

    if config.show_summary:
        write_summary(match_count, tag_counter)
