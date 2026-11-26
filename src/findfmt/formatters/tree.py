"""Rich hierarchical directory tree serializer and visual node formatters."""

from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING, TextIO

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from rich.tree import Tree

from findfmt.cli.terminal import _reconfigure_cp437, get_console
from findfmt.formatters._tree_helpers import (
    compute_tree_dir_sizes,
    format_file_label,
    record_dir_disk_paths,
    traverse_tree_node,
)
from findfmt.formatters.base import _MetadataFormatterBase
from findfmt.formatters.glyphs import resolve_tree_guides
from findfmt.utils.strings import format_display_path

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from findfmt.models import FileInfo

__all__ = ["RichTreeFormatter"]


class RichTreeFormatter(_MetadataFormatterBase):
    """Hierarchical directory tree serializer using Rich."""

    def __init__(  # noqa: PLR0913 - wide CLI/config signature
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
        self._set_ownership_options(permissions=show_permissions, user=show_user, group=show_group)
        self._set_stat_options(inodes=show_inodes, device=show_device, mtime=show_mtime, ctime=show_ctime)
        self.time_format = time_format
        self._set_size_options(exact=show_size, human=human_readable, si=show_si, accum=accumulate_size)
        self._set_path_options(classify=classify, ctrl=hide_control_chars, literal=literal, quote=quote_name)
        self._set_hyperlink_options(link=hyperlink, schema=hyperlink_schema, authority=hyperlink_authority)

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
            escape_markup=True,
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
        sorted_files = list(files)
        tree = self._init_tree_root()
        dir_nodes: dict[tuple[str, ...], Tree] = {}
        dir_disk_paths: dict[tuple[str, ...], Path] = {}

        dir_sizes_formatted: dict[tuple[str, ...], str] | None = None
        if self.accumulate_size:
            dir_sizes_formatted = compute_tree_dir_sizes(
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
                record_dir_disk_paths(file_info, parts, dir_parts, dir_disk_paths)

            curr_node = traverse_tree_node(
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
                format_file_label(
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
        if self.cp437 and not self.no_indent and not self.ansi_lines:
            _reconfigure_cp437(stream)

        tree = self._build_tree(files)
        get_console(stream, width=self.console_width, force_color=self.force_color).print(tree)
