"""Semantic HTML5 document serializer for directory traversal trees."""

from __future__ import annotations

import html
import sys
from typing import TYPE_CHECKING, TextIO

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from findfmt.formatters._hierarchy import (
    HierarchyNode,
    build_hierarchy_tree,
    compute_accumulated_dir_sizes,
)
from findfmt.formatters._html_template import (
    DEFAULT_TITLE,
    HTML_TEMPLATE,
    build_href,
    read_utf8_fragment,
)
from findfmt.formatters.base import _MetadataFormatterBase, write_stream_safe
from findfmt.sizes import format_size
from findfmt.utils.strings import format_display_path

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from findfmt.models import FileInfo

__all__ = ["HtmlFormatter"]


class HtmlFormatter(_MetadataFormatterBase):
    """Semantic, accessible HTML5 document serializer with intro/outro templating."""

    def __init__(  # noqa: PLR0913 - wide CLI/config signature
        self,
        *,
        absolute: bool = False,
        base_href: str | None = None,
        title: str | None = None,
        intro: str | None = None,
        intro_file: Path | None = None,
        outro: str | None = None,
        outro_file: Path | None = None,
        no_links: bool = False,
        no_indent: bool = False,
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
    ) -> None:
        """Initialize HtmlFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            base_href: Base URL or path prefix for clickable hyperlinks.
            title: Document title and heading text.
            intro: Custom HTML fragment string to prepend before directory listing.
            intro_file: Path to HTML file fragment to prepend.
            outro: Custom HTML fragment string to append after directory listing.
            outro_file: Path to HTML file fragment to append.
            no_links: Whether to suppress hyperlinks and render plain text paths.
            no_indent: Whether to suppress indentation lines in tree listing.
            show_permissions: Whether to include permissions string.
            show_user: Whether to include owner username or UID.
            show_group: Whether to include owner group or GID.
            show_inodes: Whether to include filesystem inode number.
            show_device: Whether to include filesystem device number.
            show_size: Whether to include exact byte size.
            human_readable: Whether to format size using binary units.
            show_si: Whether to format size using SI metric units.
            accumulate_size: Whether to accumulate recursive directory disk usage.
            show_mtime: Whether to include last modification time.
            show_ctime: Whether to include last status change time.
            time_format: Optional strftime syntax format string for dates.
            classify: Whether to append file type classification indicator.
            hide_control_chars: Whether to mask non-printable characters.
            literal: Whether to emit non-printable characters verbatim.
            quote_name: Whether to enclose filenames in double quotes.
        """
        super().__init__(absolute=absolute)
        self.base_href = base_href
        self.title = title if title is not None else DEFAULT_TITLE
        self.intro = intro
        if self.intro is None and intro_file is not None:
            self.intro = read_utf8_fragment(intro_file)

        self.outro = outro
        if self.outro is None and outro_file is not None:
            self.outro = read_utf8_fragment(outro_file)

        self.no_links = no_links
        self.no_indent = no_indent
        self._set_ownership_options(permissions=show_permissions, user=show_user, group=show_group)
        self._set_stat_options(inodes=show_inodes, device=show_device, mtime=show_mtime, ctime=show_ctime)
        self.time_format = time_format
        self._set_size_options(exact=show_size, human=human_readable, si=show_si, accum=accumulate_size)
        self._set_path_options(classify=classify, ctrl=hide_control_chars, literal=literal, quote=quote_name)

    def _format_size_val(self, size_bytes: int) -> str:
        """Format size value according to unit preferences."""
        return format_size(
            size_bytes,
            human_readable=self.human_readable,
            si=self.show_si,
            exact=self.show_size,
        )

    def _format_metadata(self, file_info: FileInfo | None) -> str:
        """Render metadata prefix badges if active."""
        if file_info is None:
            return ""

        parts = self._format_stat_parts(file_info)
        if not parts:
            return ""

        escaped_parts = html.escape(" ".join(parts))
        return f'<span class="meta">[{escaped_parts}]</span> '

    def _format_link_or_text(
        self,
        node: HierarchyNode,
        display_name: str,
    ) -> str:
        """Render clickable hyperlink or plain text span."""
        escaped_name = html.escape(display_name)
        if node.is_dir:
            cls = "dir"
        elif node.file_info and node.file_info.is_symlink:
            cls = "symlink"
        else:
            cls = "file"

        if self.no_links:
            return f'<span class="{cls}">{escaped_name}</span>'

        href = build_href(self.base_href, node.path)
        return f'<a href="{html.escape(href)}" class="{cls}">{escaped_name}</a>'

    def _format_size_part(
        self,
        node: HierarchyNode,
        dir_sizes: dict[int, int] | None,
    ) -> str:
        """Render formatted size string with span markup."""
        if node.is_dir and self.accumulate_size and dir_sizes is not None and id(node) in dir_sizes:
            accum_sz = self._format_size_val(dir_sizes[id(node)])
            return f' <span class="size">{html.escape(accum_sz)}</span>'

        if not node.is_dir and node.file_info:
            file_sz = self._format_size_val(node.file_info.size_bytes)
            return f' <span class="size">{html.escape(file_sz)}</span>'

        return ""

    def _format_tags_and_mime(self, file_info: FileInfo | None) -> str:
        """Render badge spans for tags and mime type."""
        if file_info is None:
            return ""

        tags_part = ""
        if file_info.tags:
            tags_part = "".join(
                f' <span class="badge badge-{html.escape(t)}">{html.escape(t)}</span>'
                for t in sorted(file_info.tags)
            )

        mime_part = ""
        if file_info.mime_type is not None and file_info.mime_type:
            mime_part = f' <span class="mime">{html.escape(file_info.mime_type)}</span>'

        return f"{tags_part}{mime_part}"

    def _format_entry(
        self,
        node: HierarchyNode,
        dir_sizes: dict[int, int] | None,
    ) -> str:
        """Render single directory or file entry line."""
        indicator = node.file_info.indicator if (self.classify and node.file_info) else None
        if self.classify and node.is_dir and (indicator is None or not indicator):
            indicator = "/"

        display_name = format_display_path(
            node.name,
            quote_name=self.quote_name,
            hide_control_chars=self.hide_control_chars,
            literal=self.literal,
            indicator=indicator,
        )

        is_sym = bool(node.file_info and node.file_info.is_symlink)
        icon = "📁 " if node.is_dir else ("📎 " if is_sym else "📄 ")
        meta_part = self._format_metadata(node.file_info)
        link_part = self._format_link_or_text(node, display_name)
        size_part = self._format_size_part(node, dir_sizes)
        tags_and_mime = self._format_tags_and_mime(node.file_info)

        return f"{meta_part}{icon}{link_part}{size_part}{tags_and_mime}"

    def _render_tree_lines(
        self,
        node: HierarchyNode,
        dir_sizes: dict[int, int] | None,
        lines: list[str],
        prefix: str = "",
    ) -> None:
        """Recursively traverse tree nodes and emit formatted line entries."""
        items = list(node.children.values())
        for idx, child in enumerate(items):
            is_last = idx == len(items) - 1
            guide = "" if self.no_indent else ("└── " if is_last else "├── ")
            entry_line = f"{prefix}{guide}{self._format_entry(child, dir_sizes)}"
            lines.append(entry_line)

            if child.children:
                next_prefix = "" if self.no_indent else (prefix + ("    " if is_last else "│   "))
                self._render_tree_lines(child, dir_sizes, lines, prefix=next_prefix)

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format an iterable of FileInfo instances into an HTML5 document string.

        Args:
            files: Iterable of classified file objects.

        Returns:
            Semantic HTML5 document string.
        """
        sorted_files = list(files)

        listing = ""
        if sorted_files:
            root_node = build_hierarchy_tree(sorted_files, absolute=self.absolute)
            dir_sizes = compute_accumulated_dir_sizes(root_node) if self.accumulate_size else {}
            lines = [self._format_entry(root_node, dir_sizes)]
            self._render_tree_lines(root_node, dir_sizes, lines)
            listing = "\n".join(lines)

        intro_part = f"{self.intro}\n" if self.intro is not None and self.intro else ""
        outro_part = f"{self.outro}\n" if self.outro is not None and self.outro else ""

        return HTML_TEMPLATE.format(
            title=html.escape(self.title),
            intro=intro_part,
            listing=listing,
            outro=outro_part,
        )

    @override
    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream formatted HTML output directly to a text stream.

        Args:
            files: Iterable of classified file objects.
            stream: Target text stream.
        """
        write_stream_safe(stream, self.format(files))
        stream.flush()
