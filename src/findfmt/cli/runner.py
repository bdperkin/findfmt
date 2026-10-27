"""CLI execution and orchestration engine for findfmt."""

from __future__ import annotations

import io
import sys
from collections import Counter
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, TextIO

import typer

from findfmt.cli.config import build_traversal_config
from findfmt.cli.output_sink import OutputSink, open_output_sink, reconfigure_surrogateescape
from findfmt.cli.signals import handle_broken_pipe, install_signal_handlers, trap_cli_signals
from findfmt.formatters import OutputFormat, get_formatter
from findfmt.i18n import set_locale
from findfmt.summary import write_summary
from findfmt.terminal import PagerController, is_color_enabled
from findfmt.traversal import find_files

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from findfmt.formatters.base import Formatter
    from findfmt.models import FileInfo, TraversalConfig

__all__ = ["execute_findfmt"]


def _is_stream_tty(stream: TextIO) -> bool:
    """Determine whether stream behaves as an interactive terminal."""
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False


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
    try:
        is_tty = _is_stream_tty(target_stream)
        if custom_controller or (is_tty and pager is not False):
            buf = io.StringIO()
            formatter.stream(files, buf)
            pager_ctrl.display(buf.getvalue())
        else:
            formatter.stream(files, target_stream)
    except BrokenPipeError:
        handle_broken_pipe(target_stream)


def _reconfigure_surrogateescape(stream: TextIO) -> None:
    """Ensure text stream uses surrogateescape to avoid UnicodeEncodeError on raw POSIX paths."""
    reconfigure_surrogateescape(stream)


def _open_output_sink(
    output: Path | None,
    fallback: TextIO | None,
) -> tuple[TextIO, OutputSink | None]:
    """Open destination output sink or return fallback stream."""
    sink = open_output_sink(output, fallback)
    return sink.stream, sink if output is not None else None


def _resolve_effective_format(
    output_format: OutputFormat,
    *,
    xml: bool,
    html: str | None,
    tree: bool,
    json: bool = False,
) -> OutputFormat:
    """Resolve effective serialization format taking precedence rules into account."""
    if xml:
        return OutputFormat.XML

    if html is not None:
        return OutputFormat.HTML

    if json:
        return OutputFormat.JSON

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
    is_tty = _is_stream_tty(target_stream)
    if config.null_delimited or (effective_format == OutputFormat.TEXT and config.literal):
        effective_literal, effective_hide_control_chars = True, False
    elif effective_format == OutputFormat.TEXT and config.hide_control_chars:
        effective_literal, effective_hide_control_chars = False, True
    elif effective_format == OutputFormat.TEXT:
        effective_literal, effective_hide_control_chars = not is_tty, is_tty
    else:
        effective_literal, effective_hide_control_chars = config.literal, config.hide_control_chars

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
        "hide_control_chars": effective_hide_control_chars,
        "literal": effective_literal,
        "quote_name": config.quote_name,
        "hyperlink": config.hyperlink,
        "hyperlink_schema": config.hyperlink_schema,
        "hyperlink_authority": config.hyperlink_authority,
        "csv_safe": config.csv_safe,
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
    json: bool = False,
    intro: Path | None = None,
    outro: Path | None = None,
    title: str | None = None,
    no_links: bool = False,
    hyperlink: bool = False,
    hyperlink_schema: str = "file://",
    hyperlink_authority: str | None = None,
    table_style: str | None = None,
    csv_safe: bool = False,
    absolute: bool = False,
    relative: bool = False,
    print0: bool,
    list_tags: bool,
    summary: bool,
    exit_status: bool = False,
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
    find_files_func: Callable[[TraversalConfig], Iterable[FileInfo]] | None = None,
    pager: bool | None = None,
    stream: TextIO | None = None,
    pager_controller: PagerController | None = None,
    no_indent: bool = False,
    ansi_lines: bool = False,
    cp437: bool = False,
    color: bool | None = None,
    locale: str | None = None,
) -> None:
    """Execute file discovery, classification, formatting, and summary reporting."""
    install_signal_handlers()

    if locale is not None:
        set_locale(locale)

    effective_format = _resolve_effective_format(
        output_format,
        xml=xml,
        html=html,
        tree=tree,
        json=json,
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
        json=json,
        intro=intro,
        outro=outro,
        title=title,
        no_links=no_links,
        hyperlink=hyperlink,
        hyperlink_schema=hyperlink_schema,
        hyperlink_authority=hyperlink_authority,
        csv_safe=csv_safe,
        locale=locale,
    )

    tag_counter: Counter[str] = Counter()
    match_count = total_bytes = 0
    had_traversal_error = False
    delimiter = "\0" if config.null_delimited else "\n"

    reconfigure_surrogateescape(sys.stdout)
    sink = open_output_sink(output, stream)
    target_stream = sink.stream
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

    def _on_traversal_error(err: OSError) -> None:
        """Report missing or unreadable path to stderr and mark traversal failure."""
        nonlocal had_traversal_error
        had_traversal_error = True
        bad_path = err.filename or "<unknown>"
        reason = err.strerror or (str(err.args[0]) if err.args else str(err))
        typer.echo(f"findfmt: cannot open '{bad_path}': {reason}", err=True)

    def _matched_files() -> Iterable[FileInfo]:
        """Yield matched files while accumulating frequency statistics."""
        nonlocal match_count, total_bytes
        file_iter = (
            find_files_func(config)
            if find_files_func is not None
            else find_files(config, on_error=_on_traversal_error)
        )
        for file_info in file_iter:
            match_count += 1
            if config.show_summary:
                tag_counter.update(file_info.tags)
                total_bytes += file_info.size_bytes

            yield file_info

    with trap_cli_signals(target_stream):
        try:
            _deliver_output(
                formatter,
                _matched_files(),
                pager_ctrl,
                target_stream,
                pager=pager,
                custom_controller=pager_controller is not None,
            )
            sink.commit()
        finally:
            sink.close()

        if config.show_summary:
            write_summary(match_count, tag_counter, total_bytes=total_bytes, force_color=color)

        if had_traversal_error or (exit_status and match_count == 0):
            raise typer.Exit(code=1)
