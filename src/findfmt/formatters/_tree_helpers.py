"""Directory traversal, disk-path tracking, and label helpers for RichTreeFormatter."""

from __future__ import annotations

import collections
from typing import TYPE_CHECKING

import rich.markup

from findfmt.formatters.badges import format_tag_badge
from findfmt.metadata import format_metadata_parts
from findfmt.sizes import format_size
from findfmt.utils.hyperlinks import build_file_uri
from findfmt.utils.strings import format_display_path

if TYPE_CHECKING:
    from pathlib import Path

    from rich.tree import Tree

    from findfmt.models import FileInfo

__all__ = [
    "compute_tree_dir_sizes",
    "format_file_label",
    "record_dir_disk_paths",
    "traverse_tree_node",
]


def format_file_label(  # noqa: PLR0913 - wide CLI/config signature
    file_info: FileInfo,
    filename: str,
    *,
    show_permissions: bool = False,
    show_user: bool = False,
    show_group: bool = False,
    show_inodes: bool = False,
    show_device: bool = False,
    show_size: bool = False,
    human_readable: bool = False,
    show_si: bool = False,
    show_mtime: bool = False,
    show_ctime: bool = False,
    time_format: str | None = None,
    classify: bool = False,
    hide_control_chars: bool = False,
    literal: bool = False,
    quote_name: bool = False,
    hyperlink: bool = False,
    hyperlink_schema: str = "file://",
    hyperlink_authority: str | None = None,
) -> str:
    """Format Rich leaf node label for a file with badges and optional metadata."""
    meta_parts = format_metadata_parts(
        file_info,
        show_inodes=show_inodes,
        show_device=show_device,
        show_permissions=show_permissions,
        show_user=show_user,
        show_group=show_group,
        show_mtime=show_mtime,
        show_ctime=show_ctime,
        time_format=time_format,
    )
    prefix = f"[cyan][{' '.join(meta_parts)}][/] " if meta_parts else ""
    indicator = file_info.indicator if classify else None
    uri = (
        build_file_uri(
            file_info.path,
            schema=hyperlink_schema,
            authority=hyperlink_authority,
        )
        if hyperlink
        else None
    )
    display_name = format_display_path(
        filename,
        quote_name=quote_name,
        hide_control_chars=hide_control_chars,
        literal=literal,
        indicator=indicator,
        hyperlink=hyperlink,
        uri=uri,
        escape_markup=True,
    )
    tags_list = " ".join(format_tag_badge(t) for t in sorted(file_info.tags))
    tags_part = f" {tags_list}" if file_info.tags else ""
    formatted_sz = format_size(
        file_info.size_bytes,
        human_readable=human_readable,
        si=show_si,
        exact=show_size,
    )
    size_part = f" [green]{formatted_sz}[/]"
    mime_val = rich.markup.escape(file_info.mime_type or "")
    mime_part = f" [dim]{mime_val}[/]" if mime_val else ""
    return f"{prefix}📄 {display_name}{size_part}{tags_part}{mime_part}"


def record_dir_disk_paths(
    file_info: FileInfo,
    parts: tuple[str, ...],
    dir_parts: tuple[str, ...],
    dir_disk_paths: dict[tuple[str, ...], Path],
) -> None:
    """Record filesystem disk paths for directory parts if not already registered."""
    for idx in range(1, len(dir_parts) + 1):
        sub_t = dir_parts[:idx]
        if sub_t not in dir_disk_paths:
            parent_idx = len(parts) - 1 - idx
            dir_disk_paths[sub_t] = file_info.path.parents[parent_idx]


def traverse_tree_node(  # noqa: PLR0913 - wide CLI/config signature
    tree: Tree,
    dir_nodes: dict[tuple[str, ...], Tree],
    dir_parts: tuple[str, ...],
    *,
    dir_sizes: dict[tuple[str, ...], str] | None = None,
    dir_disk_paths: dict[tuple[str, ...], Path] | None = None,
    classify: bool = False,
    hide_control_chars: bool = False,
    literal: bool = False,
    quote_name: bool = False,
    hyperlink: bool = False,
    hyperlink_schema: str = "file://",
    hyperlink_authority: str | None = None,
) -> Tree:
    """Traverse or create branch nodes in tree for directory parts."""
    curr_node = tree
    for i in range(1, len(dir_parts) + 1):
        sub_tuple = dir_parts[:i]
        if sub_tuple not in dir_nodes:
            size_suffix = (
                f" [green]{dir_sizes[sub_tuple]}[/]"
                if dir_sizes is not None and sub_tuple in dir_sizes
                else ""
            )
            raw_dir_name = dir_parts[i - 1]
            indicator = "/" if classify else None
            dir_uri = (
                build_file_uri(
                    dir_disk_paths[sub_tuple],
                    schema=hyperlink_schema,
                    authority=hyperlink_authority,
                )
                if (hyperlink and dir_disk_paths is not None and sub_tuple in dir_disk_paths)
                else None
            )
            display_dir_name = format_display_path(
                raw_dir_name,
                quote_name=quote_name,
                hide_control_chars=hide_control_chars,
                literal=literal,
                indicator=indicator,
                hyperlink=hyperlink,
                uri=dir_uri,
                escape_markup=True,
            )
            node_label = f"[bold blue]📁 {display_dir_name}[/]{size_suffix}"
            dir_nodes[sub_tuple] = curr_node.add(node_label)

        curr_node = dir_nodes[sub_tuple]

    return curr_node


def compute_tree_dir_sizes(
    sorted_files: list[FileInfo],
    *,
    absolute: bool,
    human_readable: bool,
    show_si: bool,
    show_size: bool,
) -> dict[tuple[str, ...], str]:
    """Compute formatted accumulated directory sizes for tree display."""
    dir_sizes_raw: dict[tuple[str, ...], int] = collections.defaultdict(int)
    for file_info in sorted_files:
        target_path = file_info.path if absolute else file_info.relative_path
        is_abs = target_path.is_absolute()
        parts = target_path.parts
        dir_parts = tuple(parts[1:-1] if is_abs else parts[:-1])
        for i in range(1, len(dir_parts) + 1):
            dir_sizes_raw[dir_parts[:i]] += file_info.size_bytes

    dir_sizes_formatted: dict[tuple[str, ...], str] = {}
    for sub_tup, raw_sz in dir_sizes_raw.items():
        dir_sizes_formatted[sub_tup] = format_size(
            raw_sz,
            human_readable=human_readable,
            si=show_si,
            exact=show_size,
        )

    return dir_sizes_formatted
