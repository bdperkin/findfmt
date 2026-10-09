"""CLI execution and orchestration engine for findfmt."""

from __future__ import annotations

import io
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from findfmt.formatters import OutputFormat, get_formatter
from findfmt.models import TraversalConfig
from findfmt.summary import parse_tag_arguments, write_summary
from findfmt.terminal import PagerController, is_color_enabled
from findfmt.traversal import find_files

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from findfmt.formatters.base import Formatter
    from findfmt.models import FileInfo

__all__ = ["execute_findfmt"]


def _deliver_output(  # noqa: PLR0913
    formatter: Formatter,
    files: Iterable[FileInfo],
    pager_ctrl: PagerController,
    target_stream: TextIO,
    *,
    pager: bool | None,
    custom_controller: bool,
) -> None:
    """Deliver formatted output directly or via interactive pager controller.

    Args:
        formatter: Configured output formatter.
        files: Iterable of matched file objects.
        pager_ctrl: Active PagerController instance.
        target_stream: Destination text stream.
        pager: Explicit pager override flag.
        custom_controller: Whether a custom controller was injected.
    """
    is_tty = bool(getattr(target_stream, "isatty", lambda: False)())
    if custom_controller or (is_tty and pager is not False):
        buf = io.StringIO()
        formatter.stream(files, buf)
        pager_ctrl.display(buf.getvalue())
    else:
        formatter.stream(files, target_stream)


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
    pager: bool | None = None,
    stream: TextIO | None = None,
    pager_controller: PagerController | None = None,
    no_indent: bool = False,
    ansi_lines: bool = False,
    cp437: bool = False,
    color: bool | None = None,
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
        pager: Optional interactive pager override flag.
        stream: Target output text stream (defaults to sys.stdout).
        pager_controller: Optional injected PagerController instance.
        no_indent: Whether to suppress branch indentation and whitespace padding.
        ansi_lines: Whether to use ANSI/VT100 alternate line drawing escapes.
        cp437: Whether to use CP437 console graphics line drawing characters.
        color: Explicit color enable override flag.
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

    target_stream = stream if stream is not None else sys.stdout
    pager_ctrl = pager_controller or PagerController(
        pager=pager,
        stream=target_stream,
        force_color=color,
    )

    formatter_kwargs: dict[str, object] = {
        "no_indent": no_indent,
        "ansi_lines": ansi_lines,
        "cp437": cp437,
    }
    if table_style is not None:
        formatter_kwargs["table_style"] = table_style

    color_on = is_color_enabled(target_stream, force_color=color)
    if effective_format in (OutputFormat.TABLE, OutputFormat.TREE, OutputFormat.CSV_TABLE):
        formatter_kwargs["force_color"] = color_on

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

    _deliver_output(
        formatter,
        _matched_files(),
        pager_ctrl,
        target_stream,
        pager=pager,
        custom_controller=pager_controller is not None,
    )

    if config.show_summary:
        write_summary(match_count, tag_counter, force_color=color)
