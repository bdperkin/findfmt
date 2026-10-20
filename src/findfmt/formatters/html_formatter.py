"""Semantic HTML5 document serializer for directory traversal trees."""

from __future__ import annotations

import html
import os
import sys
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

from findfmt.formatters.base import Formatter, write_stream_safe
from findfmt.metadata import format_metadata_parts
from findfmt.sizes import format_size
from findfmt.utils.strings import format_display_path

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo

__all__ = ["HtmlFormatter"]

DEFAULT_TITLE = "Directory Tree"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{
      font-family:
        ui-monospace,
        SFMono-Regular,
        Menlo,
        Monaco,
        Consolas,
        "Liberation Mono",
        "Courier New",
        monospace;
      margin: 2rem;
      background: #ffffff;
      color: #24292f;
    }}
    h1 {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 1.5rem;
      margin-bottom: 1rem;
    }}
    .tree {{
      line-height: 1.6;
      font-size: 0.95rem;
    }}
    .tree a {{
      text-decoration: none;
      color: #0969da;
    }}
    .tree a:hover {{
      text-decoration: underline;
    }}
    .tree .dir {{
      font-weight: bold;
      color: #0969da;
    }}
    .tree .file {{
      color: #24292f;
    }}
    .tree .symlink {{
      color: #8250df;
    }}
    .tree .meta {{
      color: #57606a;
      margin-right: 0.5rem;
    }}
    .tree .size {{
      color: #1a7f37;
      margin-left: 0.5rem;
    }}
    .tree .mime {{
      color: #6e7781;
      margin-left: 0.5rem;
      font-style: italic;
    }}
    .tree .badge {{
      display: inline-block;
      padding: 0.1em 0.4em;
      font-size: 0.8em;
      font-weight: 500;
      border-radius: 4px;
      background-color: #f6f8fa;
      border: 1px solid #d0d7de;
      color: #24292f;
      margin-left: 0.25rem;
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
{intro}  <pre class="tree"><code>{listing}</code></pre>
{outro}</body>
</html>
"""


class _HtmlNode:
    """Hierarchical node for HTML directory tree formatting."""

    __slots__ = ("children", "file_info", "is_dir", "name", "path")

    def __init__(
        self,
        name: str,
        path: Path,
        *,
        is_dir: bool,
        file_info: FileInfo | None = None,
    ) -> None:
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.file_info = file_info
        self.children: dict[str, _HtmlNode] = {}


def _build_href(base_href: str | None, target_path: Path) -> str:
    """Format and URL-encode path with optional base HREF prefix."""
    posix_path = target_path.as_posix()
    if posix_path in {".", ""}:
        return base_href or "."

    quoted_segments = [
        urllib.parse.quote_from_bytes(os.fsencode(seg)) for seg in posix_path.split("/") if seg
    ]
    quoted_path = "/".join(quoted_segments)

    if not base_href:
        return quoted_path

    if base_href.endswith("/"):
        return f"{base_href}{quoted_path}"

    return f"{base_href}/{quoted_path}"


def _ensure_dir_path(
    root_node: _HtmlNode,
    dir_parts: tuple[str, ...],
    *,
    is_abs: bool,
) -> tuple[_HtmlNode, Path]:
    """Descend or create directory nodes along path parts."""
    curr = root_node
    accum_path = Path(dir_parts[0]) if (is_abs and dir_parts) else Path()
    for part in dir_parts:
        accum_path = accum_path / part
        if part not in curr.children:
            curr.children[part] = _HtmlNode(part, accum_path, is_dir=True)

        curr = curr.children[part]

    return curr, accum_path


class HtmlFormatter(Formatter):
    """Semantic, accessible HTML5 document serializer with intro/outro templating."""

    def __init__(  # noqa: PLR0913
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
            self.intro = intro_file.read_text(encoding="utf-8")

        self.outro = outro
        if self.outro is None and outro_file is not None:
            self.outro = outro_file.read_text(encoding="utf-8")

        self.no_links = no_links
        self.no_indent = no_indent
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

    def _format_size_val(self, size_bytes: int) -> str:
        """Format size value according to unit preferences."""
        return format_size(
            size_bytes,
            human_readable=self.human_readable,
            si=self.show_si,
            exact=self.show_size,
        )

    def _build_node_tree(self, sorted_files: list[FileInfo]) -> _HtmlNode:
        """Construct hierarchical node tree from classified files."""
        root_name = "/" if self.absolute else "."
        root_node = _HtmlNode(root_name, Path(root_name), is_dir=True)

        for file_info in sorted_files:
            target_path = file_info.path if self.absolute else file_info.relative_path
            is_abs = target_path.is_absolute()
            parts = target_path.parts
            dir_parts = tuple(parts[1:-1] if is_abs else parts[:-1])

            curr, accum_path = _ensure_dir_path(root_node, dir_parts, is_abs=is_abs)
            filename = parts[-1] if parts else str(target_path)
            leaf_path = accum_path / filename if len(parts) > 1 else target_path
            is_dir = file_info.indicator == "/" or "directory" in file_info.tags
            if filename in curr.children:
                curr.children[filename].file_info = file_info
                curr.children[filename].is_dir = is_dir
            else:
                curr.children[filename] = _HtmlNode(
                    filename,
                    leaf_path,
                    is_dir=is_dir,
                    file_info=file_info,
                )

        return root_node

    def _calculate_node_sizes(self, node: _HtmlNode) -> int:
        """Compute accumulated size for a node and all descendants."""
        size = 0
        if node.file_info and not node.is_dir:
            size += node.file_info.size_bytes

        for child in node.children.values():
            size += self._calculate_node_sizes(child)

        return size

    def _format_metadata(self, file_info: FileInfo | None) -> str:
        """Render metadata prefix badges if active."""
        if file_info is None:
            return ""

        parts = format_metadata_parts(
            file_info,
            show_inodes=self.show_inodes,
            show_device=self.show_device,
            show_permissions=self.show_permissions,
            show_user=self.show_user,
            show_group=self.show_group,
            show_mtime=self.show_mtime,
            show_ctime=self.show_ctime,
            time_format=self.time_format,
        )
        if not parts:
            return ""

        escaped_parts = html.escape(" ".join(parts))
        return f'<span class="meta">[{escaped_parts}]</span> '

    def _format_link_or_text(
        self,
        node: _HtmlNode,
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

        href = _build_href(self.base_href, node.path)
        return f'<a href="{html.escape(href)}" class="{cls}">{escaped_name}</a>'

    def _format_size_part(
        self,
        node: _HtmlNode,
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
        if file_info.mime_type:
            mime_part = f' <span class="mime">{html.escape(file_info.mime_type)}</span>'

        return f"{tags_part}{mime_part}"

    def _format_entry(
        self,
        node: _HtmlNode,
        dir_sizes: dict[int, int] | None,
    ) -> str:
        """Render single directory or file entry line."""
        indicator = node.file_info.indicator if (self.classify and node.file_info) else None
        if self.classify and node.is_dir and not indicator:
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
        node: _HtmlNode,
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
        sorted_files = sorted(
            files,
            key=lambda f: str(f.path if self.absolute else f.relative_path),
        )

        listing = ""
        if sorted_files:
            root_node = self._build_node_tree(sorted_files)
            dir_sizes: dict[int, int] = {}
            if self.accumulate_size:
                dir_sizes[id(root_node)] = self._calculate_node_sizes(root_node)

                def _compute_sizes(n: _HtmlNode) -> None:
                    """Recursively compute directory node sizes."""
                    for c in n.children.values():
                        if c.is_dir:
                            dir_sizes[id(c)] = self._calculate_node_sizes(c)
                            _compute_sizes(c)

                _compute_sizes(root_node)

            lines = [self._format_entry(root_node, dir_sizes)]
            self._render_tree_lines(root_node, dir_sizes, lines)
            listing = "\n".join(lines)

        intro_part = f"{self.intro}\n" if self.intro else ""
        outro_part = f"{self.outro}\n" if self.outro else ""

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
