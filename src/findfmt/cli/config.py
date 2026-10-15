"""Traversal configuration builder and CLI argument validation engine."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer

from findfmt.i18n import _
from findfmt.models import SortKey, TraversalConfig
from findfmt.summary import parse_tag_arguments
from findfmt.traversal.sorting import resolve_sort_key

if TYPE_CHECKING:
    from findfmt.formatters import OutputFormat

__all__ = ["build_traversal_config", "validate_cli_options"]


def _validate_file_exists(file_path: Path | None, label: str) -> None:
    """Validate that specified file exists if provided."""
    if file_path is not None and not file_path.is_file():
        msg = _("Error: {label} '{path}' not found.").format(label=_(label), path=file_path)
        typer.echo(msg, err=True)
        raise typer.Exit(code=2)


def _validate_format_conflicts(
    *,
    tree: bool,
    xml: bool,
    html: str | None,
    json: bool = False,
) -> None:
    """Ensure mutually exclusive output format flags are not combined."""
    active = [
        opt
        for opt, flag in (
            ("--tree", tree),
            ("-J/--json", json),
            ("-X/--xml", xml),
            ("-H/--html", html is not None),
        )
        if flag
    ]
    if len(active) > 1:
        typer.echo(
            _("Error: Conflicting format options: {options}.").format(options=", ".join(active)),
            err=True,
        )
        raise typer.Exit(code=2)


def _validate_from_file(from_file: str | None) -> None:
    """Validate from-file path existence if not standard input."""
    if from_file is not None and from_file != "-":
        from_file_path = Path(from_file)
        if not from_file_path.is_file():
            typer.echo(_("Error: Input file '{path}' not found.").format(path=from_file), err=True)
            raise typer.Exit(code=2)


def _validate_ordering(*, dirs_first: bool, files_first: bool) -> None:
    """Ensure mutually exclusive directory/file ordering flags are not combined."""
    if dirs_first and files_first:
        typer.echo(_("Error: Cannot specify both --dirsfirst and --filesfirst."), err=True)
        raise typer.Exit(code=2)


def validate_cli_options(  # noqa: PLR0913
    *,
    gitignore_file: Path | None,
    sort: str | None,
    unsorted: bool,
    dirs_first: bool,
    files_first: bool,
    from_file: str | None = None,
    intro: Path | None = None,
    outro: Path | None = None,
    tree: bool = False,
    xml: bool = False,
    html: str | None = None,
    json: bool = False,
) -> SortKey:
    """Validate CLI flag combinations and return resolved canonical SortKey.

    Args:
        gitignore_file: Optional external gitignore file path.
        sort: Optional sort criterion name string.
        unsorted: Whether raw unsorted mode flag is set.
        dirs_first: Whether directories first grouping is requested.
        files_first: Whether files first grouping is requested.
        from_file: Optional input file path or '-' for stdin.
        intro: Optional HTML template intro header fragment path.
        outro: Optional HTML template outro footer fragment path.
        tree: Whether tree format flag is active.
        xml: Whether XML format flag is active.
        html: Optional HTML base HREF string if active.
        json: Whether JSON format flag is active.

    Returns:
        Resolved canonical SortKey enum value.

    Raises:
        typer.Exit: On invalid argument values or conflicting options.
    """
    _validate_file_exists(gitignore_file, "Gitignore file")
    _validate_file_exists(intro, "Intro file")
    _validate_file_exists(outro, "Outro file")
    _validate_format_conflicts(tree=tree, xml=xml, html=html, json=json)
    _validate_from_file(from_file)
    _validate_ordering(dirs_first=dirs_first, files_first=files_first)

    try:
        return resolve_sort_key(sort, unsorted=unsorted)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=2) from e


def build_traversal_config(  # noqa: PLR0913
    paths: list[Path] | None,
    tags: list[str] | None,
    exclude_tags: list[str] | None,
    *,
    all_tags: bool,
    shebang: str | None,
    no_ignore: bool,
    gitignore_file: Path | None = None,
    hidden: bool,
    follow_symlinks: bool,
    dirs_only: bool,
    one_file_system: bool,
    max_depth: int | None,
    file_limit: int | None,
    prune: bool,
    pattern: list[str] | None,
    exclude_pattern: list[str] | None,
    ignore_case: bool,
    match_dirs: bool,
    absolute: bool,
    relative: bool,
    print0: bool,
    list_tags: bool,
    summary: bool,
    output_format: OutputFormat | str,
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
    inodes: bool = False,
    device: bool = False,
    size: bool = False,
    human_readable: bool = False,
    si: bool = False,
    du: bool = False,
    mtime: bool = False,
    ctime: bool = False,
    time_format: str | None = None,
    classify: bool = False,
    hide_control_chars: bool = False,
    literal: bool = False,
    quote_name: bool = False,
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
    locale: str | None = None,
) -> TraversalConfig:
    """Build and validate TraversalConfig from CLI options.

    Args:
        paths: Target root paths.
        tags: Included tag filters.
        exclude_tags: Excluded tag filters.
        all_tags: Whether all tags are required.
        shebang: Interpreter shebang filter pattern.
        no_ignore: Whether gitignore rules are ignored.
        gitignore_file: External gitignore file path.
        hidden: Whether hidden entries are included.
        follow_symlinks: Whether directory symlinks are traversed.
        dirs_only: Whether to emit directories only.
        one_file_system: Whether traversal is restricted to root device.
        max_depth: Maximum descent depth level.
        file_limit: Directory entry count limit threshold.
        prune: Whether empty directories are pruned.
        pattern: Include glob patterns.
        exclude_pattern: Exclude glob patterns.
        ignore_case: Whether pattern comparisons ignore case.
        match_dirs: Whether directory matches inherit to descendants.
        absolute: Whether to emit absolute paths.
        relative: Whether to prepend relative path search prefix.
        print0: Whether output is NUL-delimited.
        list_tags: Whether tags are printed in output.
        summary: Whether summary statistics are generated.
        output_format: Output format identifier.
        sort: Sort criteria option.
        reverse: Whether sort direction is inverted.
        unsorted: Whether to disable sorting.
        dirs_first: Whether directories precede files.
        files_first: Whether files precede directories.
        from_file: Input file or '-' for stdin.
        offline: Whether to enforce offline classification.
        permissions: Whether to display permissions in ls -l format.
        user: Whether to display file owner username or UID.
        group: Whether to display file owner group name or GID.
        inodes: Whether to display filesystem inode number.
        device: Whether to display filesystem device number.
        size: Whether to display file size in bytes.
        human_readable: Whether to format sizes using binary units.
        si: Whether to format sizes using SI metric units.
        du: Whether to accumulate recursive directory disk usage.
        mtime: Whether to display file modification date/time.
        ctime: Whether to display last status change date/time.
        time_format: Optional strftime syntax format string for dates/times.
        classify: Whether to append file classification indicator characters.
        hide_control_chars: Whether to mask non-printable characters with '?'.
        literal: Whether to emit literal control characters.
        quote_name: Whether to enclose filenames in double quotes.
        tree: Whether tree format flag is active.
        xml: Whether XML format flag is active.
        html: Optional HTML base HREF string.
        json: Whether JSON format flag is active.
        intro: Optional HTML template intro header fragment path.
        outro: Optional HTML template outro footer fragment path.
        title: Optional custom HTML document title.
        no_links: Whether to suppress hyperlinks in HTML mode.
        hyperlink: Whether to emit OSC 8 terminal hyperlinks for paths.
        hyperlink_schema: URI schema for terminal hyperlinks.
        hyperlink_authority: Optional URI authority component for terminal hyperlinks.
        locale: Optional display locale override string.

    Returns:
        Configured TraversalConfig instance.
    """
    resolved_sort = validate_cli_options(
        gitignore_file=gitignore_file,
        sort=sort,
        unsorted=unsorted,
        dirs_first=dirs_first,
        files_first=files_first,
        from_file=from_file,
        intro=intro,
        outro=outro,
        tree=tree,
        xml=xml,
        html=html,
        json=json,
    )

    root_paths = tuple(paths) if paths else (Path(),)
    format_val = str(
        output_format.value if hasattr(output_format, "value") else output_format,
    )
    effective_dirs_only = dirs_only or (du and format_val not in {"tree", "xml", "html"})
    show_mtime = mtime or (time_format is not None and not ctime)
    show_ctime = ctime

    return TraversalConfig(
        root_paths=root_paths,
        include_tags=parse_tag_arguments(tags),
        exclude_tags=parse_tag_arguments(exclude_tags),
        all_tags=all_tags,
        shebang_filter=shebang,
        respect_gitignore=not no_ignore,
        gitignore_file=gitignore_file,
        include_hidden=hidden,
        follow_symlinks=follow_symlinks,
        dirs_only=effective_dirs_only,
        one_file_system=one_file_system,
        max_depth=max_depth,
        file_limit=file_limit,
        prune_empty=prune,
        include_patterns=tuple(pattern) if pattern else (),
        exclude_patterns=tuple(exclude_pattern) if exclude_pattern else (),
        ignore_case=ignore_case,
        match_dirs=match_dirs,
        relative_paths=not absolute,
        relative_prefix=relative,
        null_delimited=print0,
        show_tags=list_tags,
        show_summary=summary,
        output_format=format_val,
        sort_by=resolved_sort,
        reverse_sort=reverse,
        dirs_first=dirs_first,
        files_first=files_first,
        from_file=from_file,
        offline=offline,
        show_permissions=permissions,
        show_user=user,
        show_group=group,
        show_inodes=inodes,
        show_device=device,
        show_size=size or du,
        human_readable=human_readable,
        show_si=si,
        accumulate_size=du,
        show_mtime=show_mtime,
        show_ctime=show_ctime,
        time_format=time_format,
        classify=classify,
        hide_control_chars=hide_control_chars,
        literal=literal,
        quote_name=quote_name,
        base_href=html,
        intro_file=intro,
        outro_file=outro,
        html_title=title,
        no_links=no_links,
        xml=xml,
        hyperlink=hyperlink,
        hyperlink_schema=hyperlink_schema,
        hyperlink_authority=hyperlink_authority,
        locale=locale,
    )
