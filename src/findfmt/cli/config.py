"""Traversal configuration builder and CLI argument validation engine."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer

from findfmt.models import SortKey, TraversalConfig
from findfmt.summary import parse_tag_arguments
from findfmt.traversal.sorting import resolve_sort_key

if TYPE_CHECKING:
    from findfmt.formatters import OutputFormat

__all__ = ["build_traversal_config", "validate_cli_options"]


def validate_cli_options(  # noqa: PLR0913
    *,
    gitignore_file: Path | None,
    sort: str | None,
    unsorted: bool,
    dirs_first: bool,
    files_first: bool,
    from_file: str | None = None,
) -> SortKey:
    """Validate CLI flag combinations and return resolved canonical SortKey.

    Args:
        gitignore_file: Optional external gitignore file path.
        sort: Optional sort criterion name string.
        unsorted: Whether raw unsorted mode flag is set.
        dirs_first: Whether directories first grouping is requested.
        files_first: Whether files first grouping is requested.
        from_file: Optional input file path or '-' for stdin.

    Returns:
        Resolved canonical SortKey enum value.

    Raises:
        typer.Exit: On invalid argument values or conflicting options.
    """
    if gitignore_file is not None and not gitignore_file.is_file():
        typer.echo(f"Error: Gitignore file '{gitignore_file}' not found.", err=True)
        raise typer.Exit(code=2)

    if from_file is not None and from_file != "-":
        from_file_path = Path(from_file)
        if not from_file_path.is_file():
            typer.echo(f"Error: Input file '{from_file}' not found.", err=True)
            raise typer.Exit(code=2)

    if dirs_first and files_first:
        typer.echo("Error: Cannot specify both --dirsfirst and --filesfirst.", err=True)
        raise typer.Exit(code=2)

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
    )

    root_paths = tuple(paths) if paths else (Path(),)
    format_val = str(
        output_format.value if hasattr(output_format, "value") else output_format,
    )

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
        dirs_only=dirs_only,
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
    )
