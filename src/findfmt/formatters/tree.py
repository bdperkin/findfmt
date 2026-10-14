"""Rich hierarchical directory tree serializer and visual node formatters."""

from __future__ import annotations

import collections
import io
import sys
from typing import TYPE_CHECKING, TextIO

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

from rich.tree import Tree

from findfmt.formatters.badges import format_tag_badge
from findfmt.formatters.base import Formatter
from findfmt.formatters.glyphs import resolve_tree_guides
from findfmt.metadata import format_metadata_parts
from findfmt.sizes import format_size
from findfmt.terminal import get_console
from findfmt.utils.hyperlinks import build_file_uri
from findfmt.utils.strings import format_display_path

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from findfmt.models import FileInfo

__all__ = ["RichTreeFormatter"]


def _format_file_label(  # noqa: PLR0913
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
    mime_part = f" [dim]{file_info.mime_type}[/]" if file_info.mime_type else ""
    return f"{prefix}📄 {display_name}{size_part}{tags_part}{mime_part}"


def _record_dir_disk_paths(
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


def _traverse_tree_node(  # noqa: PLR0913
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
            )
            node_label = f"[bold blue]📁 {display_dir_name}[/]{size_suffix}"
            dir_nodes[sub_tuple] = curr_node.add(node_label)

        curr_node = dir_nodes[sub_tuple]

    return curr_node


def _compute_tree_dir_sizes(
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


class RichTreeFormatter(Formatter):
    """Hierarchical directory tree serializer using Rich."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        absolute: bool = False,
        console_width: int | None = None,
        force_color: bool | None = None,
        no_indent: bool = False,
        ansi_lines: bool = False,
        cp437: bool = False,
        show_permissions: bool = False,
        show_user: bool = False,
        show_group: bool = False,
        show_inodes: bool = False,
        show_device: bool = False,
        show_size: bool = False,
        human_readable: bool = False,
        show_si: bool = False,
        accumulate_size: bool = False,
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
    ) -> None:
        """Initialize RichTreeFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            console_width: Optional terminal output column width override.
            force_color: Explicit color enable override flag.
            no_indent: Whether to suppress branch indentation lines.
            ansi_lines: Whether to use ANSI/VT100 escape sequences.
            cp437: Whether to use CP437 console characters.
            show_permissions: Whether to display permissions string in labels.
            show_user: Whether to display file owner user in labels.
            show_group: Whether to display file owner group in labels.
            show_inodes: Whether to display filesystem inode in labels.
            show_device: Whether to display filesystem device in labels.
            show_size: Whether to display exact byte size.
            human_readable: Whether to format sizes using binary units.
            show_si: Whether to format sizes using SI metric units.
            accumulate_size: Whether to accumulate recursive directory disk usage.
            show_mtime: Whether to display file modification date/time in labels.
            show_ctime: Whether to display last status change date/time in labels.
            time_format: Optional strftime syntax format string for dates/times.
            classify: Whether to append file classification indicator characters.
            hide_control_chars: Whether to mask non-printable characters with '?'.
            literal: Whether to emit literal control characters.
            quote_name: Whether to enclose filenames in double quotes.
            hyperlink: Whether to wrap paths in OSC 8 terminal hyperlink escapes.
            hyperlink_schema: URI schema for terminal hyperlinks.
            hyperlink_authority: Optional URI authority component for terminal hyperlinks.
        """
        super().__init__(absolute=absolute)
        self.console_width = console_width
        self.force_color = force_color
        self.no_indent = no_indent
        self.ansi_lines = ansi_lines
        self.cp437 = cp437
        self.show_permissions = show_permissions
        self.show_user = show_user
        self.show_group = show_group
        self.show_inodes = show_inodes
        self.show_device = show_device
        self.show_size = show_size
        self.human_readable = human_readable
        self.show_si = show_si
        self.accumulate_size = accumulate_size
        self.show_mtime = show_mtime
        self.show_ctime = show_ctime
        self.time_format = time_format
        self.classify = classify
        self.hide_control_chars = hide_control_chars
        self.literal = literal
        self.quote_name = quote_name
        self.hyperlink = hyperlink
        self.hyperlink_schema = hyperlink_schema
        self.hyperlink_authority = hyperlink_authority

    def _init_tree_root(self) -> Tree:
        """Initialize the root Tree node with guides and styling."""
        root_name = "/" if self.absolute else "."
        root_indicator = "/" if (self.classify and not self.absolute) else None
        display_root = format_display_path(
            root_name,
            quote_name=self.quote_name,
            hide_control_chars=self.hide_control_chars,
            literal=self.literal,
            indicator=root_indicator,
        )
        tree = Tree(f"[bold]{display_root}[/]")
        guides = resolve_tree_guides(
            no_indent=self.no_indent,
            ansi_lines=self.ansi_lines,
            cp437=self.cp437,
        )
        tree.TREE_GUIDES = [guides, guides, guides]
        tree.ASCII_GUIDES = guides
        return tree

    def _build_tree(self, files: Iterable[FileInfo]) -> Tree:
        """Construct a nested Rich Tree populated with directory branches and files."""
        sorted_files = sorted(
            files,
            key=lambda f: str(f.path if self.absolute else f.relative_path),
        )
        tree = self._init_tree_root()
        dir_nodes: dict[tuple[str, ...], Tree] = {}
        dir_disk_paths: dict[tuple[str, ...], Path] = {}

        dir_sizes_formatted: dict[tuple[str, ...], str] | None = None
        if self.accumulate_size:
            dir_sizes_formatted = _compute_tree_dir_sizes(
                sorted_files,
                absolute=self.absolute,
                human_readable=self.human_readable,
                show_si=self.show_si,
                show_size=self.show_size,
            )

        for file_info in sorted_files:
            target_path = file_info.path if self.absolute else file_info.relative_path
            is_abs = target_path.is_absolute()
            parts = target_path.parts
            dir_parts = tuple(parts[1:-1] if is_abs else parts[:-1])
            if self.hyperlink:
                _record_dir_disk_paths(file_info, parts, dir_parts, dir_disk_paths)

            curr_node = _traverse_tree_node(
                tree,
                dir_nodes,
                dir_parts,
                dir_sizes=dir_sizes_formatted,
                dir_disk_paths=dir_disk_paths,
                classify=self.classify,
                hide_control_chars=self.hide_control_chars,
                literal=self.literal,
                quote_name=self.quote_name,
                hyperlink=self.hyperlink,
                hyperlink_schema=self.hyperlink_schema,
                hyperlink_authority=self.hyperlink_authority,
            )
            filename = parts[-1] if parts else str(target_path)
            curr_node.add(
                _format_file_label(
                    file_info,
                    filename,
                    show_permissions=self.show_permissions,
                    show_user=self.show_user,
                    show_group=self.show_group,
                    show_inodes=self.show_inodes,
                    show_device=self.show_device,
                    show_size=self.show_size,
                    human_readable=self.human_readable,
                    show_si=self.show_si,
                    show_mtime=self.show_mtime,
                    show_ctime=self.show_ctime,
                    time_format=self.time_format,
                    classify=self.classify,
                    hide_control_chars=self.hide_control_chars,
                    literal=self.literal,
                    quote_name=self.quote_name,
                    hyperlink=self.hyperlink,
                    hyperlink_schema=self.hyperlink_schema,
                    hyperlink_authority=self.hyperlink_authority,
                ),
            )

        return tree

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Render files into a formatted string tree."""
        tree = self._build_tree(files)
        buf = io.StringIO()
        width = self.console_width if self.console_width is not None else 120
        get_console(buf, width=width, force_color=self.force_color).print(tree)
        return buf.getvalue()

    @override
    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream formatted tree directly to a text stream."""
        tree = self._build_tree(files)
        get_console(stream, width=self.console_width, force_color=self.force_color).print(tree)
