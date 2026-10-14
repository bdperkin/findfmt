"""CLI execution and orchestration engine for findfmt."""

from __future__ import annotations

import io
import sys
from collections import Counter
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, TextIO, cast

import typer

from findfmt.cli.config import build_traversal_config
from findfmt.formatters import OutputFormat, get_formatter
from findfmt.summary import write_summary
from findfmt.terminal import PagerController, is_color_enabled
from findfmt.traversal import find_files

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from findfmt.formatters.base import Formatter
    from findfmt.models import FileInfo, TraversalConfig

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


def _open_output_sink(
    output: Path | None,
    fallback: TextIO | None,
) -> tuple[TextIO, TextIO | None]:
    """Open destination output file if specified or return fallback stream."""
    if output is None:
        target = fallback if fallback is not None else cast("TextIO", sys.stdout)
        return target, None

    try:
        out_file = output.open("w", encoding="utf-8")
    except OSError as e:
        typer.echo(f"Error opening output file '{output}': {e}", err=True)
        raise typer.Exit(code=1) from e
    else:
        return out_file, out_file


def _resolve_effective_format(
    output_format: OutputFormat,
    *,
    xml: bool,
    html: str | None,
    tree: bool,
) -> OutputFormat:
    """Resolve effective serialization format taking precedence rules into account."""
    if xml:
        return OutputFormat.XML

    if html is not None:
        return OutputFormat.HTML

    if tree:
        return OutputFormat.TREE

    return output_format


def _append_html_kwargs(  # noqa: PLR0913
    kwargs: dict[str, object],
    config: TraversalConfig,
    *,
    html: str | None,
    title: str | None,
    intro: Path | None,
    outro: Path | None,
    no_links: bool,
) -> None:
    """Populate HTML-specific template and hyperlink arguments."""
    kwargs["base_href"] = html if html is not None else config.base_href
    kwargs["title"] = title if title is not None else config.html_title
    kwargs["intro_file"] = intro if intro is not None else config.intro_file
    kwargs["outro_file"] = outro if outro is not None else config.outro_file
    kwargs["no_links"] = no_links or config.no_links


def _build_formatter_kwargs(  # noqa: PLR0913
    config: TraversalConfig,
    *,
    effective_format: OutputFormat,
    no_indent: bool,
    ansi_lines: bool,
    cp437: bool,
    table_style: str | None,
    target_stream: TextIO,
    color: bool | None,
    html: str | None,
    title: str | None,
    intro: Path | None,
    outro: Path | None,
    no_links: bool,
) -> dict[str, object]:
    """Assemble keyword arguments dictionary for target output formatter."""
    kwargs: dict[str, object] = {
        "no_indent": no_indent,
        "ansi_lines": ansi_lines,
        "cp437": cp437,
        "show_permissions": config.show_permissions,
        "show_user": config.show_user,
        "show_group": config.show_group,
        "show_inodes": config.show_inodes,
        "show_device": config.show_device,
        "show_size": config.show_size,
        "human_readable": config.human_readable,
        "show_si": config.show_si,
        "accumulate_size": config.accumulate_size,
        "show_mtime": config.show_mtime,
        "show_ctime": config.show_ctime,
        "time_format": config.time_format,
        "classify": config.classify,
        "hide_control_chars": config.hide_control_chars,
        "literal": config.literal,
        "quote_name": config.quote_name,
        "hyperlink": config.hyperlink,
        "hyperlink_schema": config.hyperlink_schema,
        "hyperlink_authority": config.hyperlink_authority,
    }
    if effective_format == OutputFormat.HTML:
        _append_html_kwargs(
            kwargs,
            config,
            html=html,
            title=title,
            intro=intro,
            outro=outro,
            no_links=no_links,
        )

    if table_style is not None:
        kwargs["table_style"] = table_style

    color_on = is_color_enabled(target_stream, force_color=color)
    if effective_format in (OutputFormat.TABLE, OutputFormat.TREE, OutputFormat.CSV_TABLE):
        kwargs["force_color"] = color_on

    return kwargs


def execute_findfmt(  # noqa: PLR0913
    *,
    paths: list[Path] | None,
    tags: list[str] | None,
    exclude_tags: list[str] | None,
    all_tags: bool,
    shebang: str | None,
    no_ignore: bool,
    gitignore_file: Path | None = None,
    hidden: bool,
    follow_symlinks: bool,
    dirs_only: bool = False,
    one_file_system: bool = False,
    max_depth: int | None = None,
    file_limit: int | None = None,
    prune: bool = False,
    pattern: list[str] | None = None,
    exclude_pattern: list[str] | None = None,
    ignore_case: bool = False,
    match_dirs: bool = False,
    output_format: OutputFormat,
    output: Path | None = None,
    tree: bool = False,
    xml: bool = False,
    html: str | None = None,
    intro: Path | None = None,
    outro: Path | None = None,
    title: str | None = None,
    no_links: bool = False,
    hyperlink: bool = False,
    hyperlink_schema: str = "file://",
    hyperlink_authority: str | None = None,
    table_style: str | None = None,
    absolute: bool = False,
    relative: bool = False,
    print0: bool,
    list_tags: bool,
    summary: bool,
    sort: str | None = None,
    reverse: bool = False,
    unsorted: bool = False,
    dirs_first: bool = False,
    files_first: bool = False,
    from_file: str | None = None,
    offline: bool = False,
    permissions: bool = False,
    user: bool = False,
    group: bool = False,
    size: bool = False,
    human_readable: bool = False,
    si: bool = False,
    du: bool = False,
    inodes: bool = False,
    device: bool = False,
    mtime: bool = False,
    ctime: bool = False,
    time_format: str | None = None,
    classify: bool = False,
    hide_control_chars: bool = False,
    literal: bool = False,
    quote_name: bool = False,
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
        gitignore_file: External gitignore file to apply across traversal scope.
        hidden: Whether to include hidden files.
        follow_symlinks: Whether to follow symbolic links.
        dirs_only: Whether to list directories only and suppress files.
        one_file_system: Whether to confine traversal to the root filesystem device.
        max_depth: Maximum directory depth level.
        file_limit: Entry count threshold to skip directories.
        prune: Whether to omit directories with zero matching files.
        pattern: Include wildcard/glob pattern list.
        exclude_pattern: Exclude wildcard/glob pattern list.
        ignore_case: Whether pattern comparisons are case-insensitive.
        match_dirs: Whether directory matches inherit to descendants.
        output_format: Configured output serialization format.
        output: Destination file path for redirected output.
        tree: Whether tree view was explicitly requested.
        table_style: Optional table border style name.
        absolute: Whether to emit absolute paths.
        relative: Whether to prepend input search path prefix to relative paths.
        print0: Whether to delimit output with NUL characters.
        list_tags: Whether to display tags in output.
        summary: Whether to display execution summary.
        sort: Sort criteria identifier.
        reverse: Whether to reverse sort order.
        unsorted: Whether to disable sorting.
        dirs_first: Whether to group directories first.
        files_first: Whether to group files first.
        from_file: Optional input file or '-' for stdin to ingest directory structure.
        offline: Whether to enforce offline classification without disk access.
        permissions: Whether to display permissions in ls -l format.
        user: Whether to display file owner username or UID.
        group: Whether to display file owner group name or GID.
        size: Whether to display file size in bytes.
        human_readable: Whether to format sizes using binary units.
        si: Whether to format sizes using SI metric units.
        du: Whether to accumulate recursive directory disk usage.
        inodes: Whether to display filesystem inode number.
        device: Whether to display filesystem device number.
        mtime: Whether to display file modification date/time.
        ctime: Whether to display last status change date/time.
        time_format: Optional strftime syntax format string for dates/times.
        classify: Whether to append file classification indicator characters.
        hide_control_chars: Whether to mask non-printable characters with '?'.
        literal: Whether to emit literal control characters.
        quote_name: Whether to enclose filenames in double quotes.
        find_files_func: Traversal generator function to execute.
        pager: Optional interactive pager override flag.
        stream: Target output text stream (defaults to sys.stdout).
        pager_controller: Optional injected PagerController instance.
        no_indent: Whether to suppress branch indentation and whitespace padding.
        ansi_lines: Whether to use ANSI/VT100 alternate line drawing escapes.
        cp437: Whether to use CP437 console graphics line drawing characters.
        xml: Whether XML document output format flag is active.
        html: Optional HTML base HREF string if active.
        intro: Optional HTML template intro header fragment path.
        outro: Optional HTML template outro footer fragment path.
        title: Optional custom HTML document title.
        no_links: Whether to suppress hyperlinks in HTML mode.
        hyperlink: Whether to wrap paths in OSC 8 terminal hyperlink escapes.
        hyperlink_schema: URI schema for terminal hyperlinks.
        hyperlink_authority: Optional URI authority component for terminal hyperlinks.
        color: Explicit color enable override flag.
    """
    effective_format = _resolve_effective_format(
        output_format,
        xml=xml,
        html=html,
        tree=tree,
    )

    config = build_traversal_config(
        paths,
        tags,
        exclude_tags,
        all_tags=all_tags,
        shebang=shebang,
        no_ignore=no_ignore,
        gitignore_file=gitignore_file,
        hidden=hidden,
        follow_symlinks=follow_symlinks,
        dirs_only=dirs_only,
        one_file_system=one_file_system,
        max_depth=max_depth,
        file_limit=file_limit,
        prune=prune,
        pattern=pattern,
        exclude_pattern=exclude_pattern,
        ignore_case=ignore_case,
        match_dirs=match_dirs,
        absolute=absolute,
        relative=relative,
        print0=print0,
        list_tags=list_tags,
        summary=summary,
        output_format=effective_format,
        sort=sort,
        reverse=reverse,
        unsorted=unsorted,
        dirs_first=dirs_first,
        files_first=files_first,
        from_file=from_file,
        offline=offline,
        permissions=permissions,
        user=user,
        group=group,
        inodes=inodes,
        device=device,
        size=size,
        human_readable=human_readable,
        si=si,
        du=du,
        mtime=mtime,
        ctime=ctime,
        time_format=time_format,
        classify=classify,
        hide_control_chars=hide_control_chars,
        literal=literal,
        quote_name=quote_name,
        tree=tree,
        xml=xml,
        html=html,
        intro=intro,
        outro=outro,
        title=title,
        no_links=no_links,
        hyperlink=hyperlink,
        hyperlink_schema=hyperlink_schema,
        hyperlink_authority=hyperlink_authority,
    )

    tag_counter: Counter[str] = Counter()
    match_count = 0
    delimiter = "\0" if config.null_delimited else "\n"

    target_stream, out_file = _open_output_sink(output, stream)
    pager_ctrl = pager_controller or PagerController(
        pager=pager,
        stream=target_stream,
        force_color=color,
    )

    formatter_kwargs = _build_formatter_kwargs(
        config,
        effective_format=effective_format,
        no_indent=no_indent,
        ansi_lines=ansi_lines,
        cp437=cp437,
        table_style=table_style,
        target_stream=target_stream,
        color=color,
        html=html,
        title=title,
        intro=intro,
        outro=outro,
        no_links=no_links,
    )

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

    try:
        _deliver_output(
            formatter,
            _matched_files(),
            pager_ctrl,
            target_stream,
            pager=pager,
            custom_controller=pager_controller is not None,
        )
    finally:
        if out_file is not None:
            out_file.close()

    if config.show_summary:
        write_summary(match_count, tag_counter, force_color=color)
