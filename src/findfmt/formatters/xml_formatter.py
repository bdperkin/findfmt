"""Hierarchical XML document serializer for directory traversal trees."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING, TextIO, cast

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

from findfmt.formatters.base import Formatter
from findfmt.sizes import format_size
from findfmt.utils.strings import format_display_path, format_timestamp, strip_ansi_escapes

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo

__all__ = ["XmlFormatter"]


_MIN_PRINTABLE_ASCII = 0x20
_DEL_ASCII = 0x7F
_VALID_UNICODE_MIN = 0xA0


def _sanitize_xml_text(text: str) -> str:
    """Sanitize string for XML 1.0 validity.

    Strips ANSI escapes and masks invalid control characters.
    """
    clean = strip_ansi_escapes(text)
    return "".join(
        c
        if c in ("\t", "\n", "\r")
        or (_MIN_PRINTABLE_ASCII <= ord(c) < _DEL_ASCII)
        or (ord(c) >= _VALID_UNICODE_MIN)
        else "?"
        for c in clean
    )


class _XmlNode:
    """Internal hierarchical node for XML document building."""

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
        self.children: dict[str, _XmlNode] = {}


def _ensure_dir_path(
    root_node: _XmlNode,
    dir_parts: tuple[str, ...],
    *,
    is_abs: bool,
) -> tuple[_XmlNode, Path]:
    """Descend or create directory nodes along path parts."""
    curr = root_node
    accum_path = Path(dir_parts[0]) if (is_abs and dir_parts) else Path()
    for part in dir_parts:
        accum_path = accum_path / part
        if part not in curr.children:
            curr.children[part] = _XmlNode(part, accum_path, is_dir=True)

        curr = curr.children[part]

    return curr, accum_path


class XmlFormatter(Formatter):
    """Hierarchical XML document serializer utilizing ElementTree."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        absolute: bool = False,
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
        """Initialize XmlFormatter.

        Args:
            absolute: Whether to emit absolute paths.
            no_indent: Whether to suppress pretty-printing indentation.
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
        if self.human_readable or self.show_si:
            return format_size(
                size_bytes,
                human_readable=self.human_readable,
                si=self.show_si,
                exact=self.show_size,
            )

        return str(size_bytes)

    def _clean_val(self, val: str | None) -> str | None:
        """Sanitize text for XML compatibility unless literal output is active."""
        if val is None or self.literal:
            return val

        return _sanitize_xml_text(val)

    def _apply_metadata_attrs(self, file_info: FileInfo, elem: ET.Element) -> None:
        """Populate optional metadata attributes on target XML element."""
        mt = format_timestamp(file_info.mtime, self.time_format) if file_info.mtime else None
        ct = format_timestamp(file_info.ctime, self.time_format) if file_info.ctime else None
        du = (
            self._format_size_val(file_info.accumulated_size)
            if file_info.accumulated_size is not None
            else None
        )
        ino = str(file_info.inode) if file_info.inode is not None else None
        dev = str(file_info.device) if file_info.device is not None else None
        pairs: tuple[tuple[str, object | None], ...] = (
            ("permissions", file_info.permissions_str),
            ("user", file_info.owner_user),
            ("group", file_info.owner_group),
            ("inode", ino),
            ("device", dev),
            ("mtime", mt),
            ("ctime", ct),
            ("accumulated_size", du),
            ("indicator", file_info.indicator),
        )
        for attr, val in pairs:
            if val is not None:
                elem.set(attr, str(self._clean_val(str(val))))

    def _apply_file_info(self, file_info: FileInfo, elem: ET.Element) -> None:
        """Populate file metadata attributes and child elements."""
        elem.set("size", self._format_size_val(file_info.size_bytes))
        elem.set("executable", "true" if file_info.is_executable else "false")
        elem.set("symlink", "true" if file_info.is_symlink else "false")
        if file_info.symlink_target:
            elem.set("symlink_target", str(self._clean_val(file_info.symlink_target)))

        self._apply_metadata_attrs(file_info, elem)

        for tag in sorted(file_info.tags):
            tag_elem = ET.SubElement(elem, "tag")
            tag_elem.text = self._clean_val(tag)

        if file_info.mime_type:
            mime_elem = ET.SubElement(elem, "mime")
            mime_elem.text = self._clean_val(file_info.mime_type)

        if file_info.shebang:
            shebang_elem = ET.SubElement(elem, "shebang")
            shebang_elem.text = self._clean_val(file_info.shebang)

    def _add_leaf_to_tree(
        self,
        curr: _XmlNode,
        parts: tuple[str, ...],
        accum_path: Path,
        file_info: FileInfo,
        target_path: Path,
    ) -> None:
        """Add file or directory leaf to parent directory node."""
        filename = parts[-1] if parts else str(target_path)
        leaf_path = accum_path / filename if len(parts) > 1 else target_path
        is_dir = file_info.indicator == "/" or "directory" in file_info.tags
        if filename in curr.children:
            curr.children[filename].file_info = file_info
            curr.children[filename].is_dir = is_dir
        else:
            curr.children[filename] = _XmlNode(
                filename,
                leaf_path,
                is_dir=is_dir,
                file_info=file_info,
            )

    def _build_node_tree(self, sorted_files: list[FileInfo]) -> _XmlNode:
        """Construct hierarchical node tree from classified files."""
        root_name = "/" if self.absolute else "."
        root_node = _XmlNode(root_name, Path(root_name), is_dir=True)

        for file_info in sorted_files:
            target_path = file_info.path if self.absolute else file_info.relative_path
            is_abs = target_path.is_absolute()
            parts = target_path.parts
            dir_parts = tuple(parts[1:-1] if is_abs else parts[:-1])

            curr, accum_path = _ensure_dir_path(root_node, dir_parts, is_abs=is_abs)
            self._add_leaf_to_tree(curr, parts, accum_path, file_info, target_path)

        return root_node

    def _calculate_node_sizes(self, node: _XmlNode) -> int:
        """Compute accumulated size for a node and all descendants."""
        size = 0
        if node.file_info and not node.is_dir:
            size += node.file_info.size_bytes

        for child in node.children.values():
            size += self._calculate_node_sizes(child)

        return size

    def _convert_dir_node(
        self,
        node: _XmlNode,
        parent: ET.Element,
        dir_sizes: dict[int, int] | None,
        display_name: str,
    ) -> None:
        """Serialize a directory node and recurse for children."""
        path_str = str(self._clean_val(str(node.path)))
        elem = ET.SubElement(
            parent,
            "directory",
            name=display_name,
            path=path_str,
        )
        if self.accumulate_size and dir_sizes is not None and id(node) in dir_sizes:
            elem.set("accumulated_size", self._format_size_val(dir_sizes[id(node)]))

        if node.file_info:
            self._apply_metadata_attrs(node.file_info, elem)
            for tag in sorted(node.file_info.tags):
                tag_elem = ET.SubElement(elem, "tag")
                tag_elem.text = self._clean_val(tag)

        for child in node.children.values():
            self._convert_node_to_xml(child, elem, dir_sizes)

    def _convert_file_node(
        self,
        node: _XmlNode,
        parent: ET.Element,
        display_name: str,
    ) -> None:
        """Serialize a regular file leaf element."""
        path_str = str(self._clean_val(str(node.path)))
        elem = ET.SubElement(
            parent,
            "file",
            name=display_name,
            path=path_str,
        )
        file_info = cast("FileInfo", node.file_info)
        self._apply_file_info(file_info, elem)

    def _convert_node_to_xml(
        self,
        node: _XmlNode,
        parent: ET.Element,
        dir_sizes: dict[int, int] | None = None,
    ) -> None:
        """Recursively serialize _XmlNode hierarchy into ElementTree elements."""
        indicator = node.file_info.indicator if (self.classify and node.file_info) else None
        display_name = format_display_path(
            node.name,
            quote_name=self.quote_name,
            hide_control_chars=self.hide_control_chars,
            literal=self.literal,
            indicator=indicator,
        )

        if node.is_dir:
            self._convert_dir_node(node, parent, dir_sizes, display_name)
        else:
            self._convert_file_node(node, parent, display_name)

    @override
    def format(self, files: Iterable[FileInfo]) -> str:
        """Format an iterable of FileInfo instances into an XML document string.

        Args:
            files: Iterable of classified file objects.

        Returns:
            Well-formed XML document string ending with a newline.
        """
        sorted_files = sorted(
            files,
            key=lambda f: str(f.path if self.absolute else f.relative_path),
        )

        root = ET.Element("tree")
        if sorted_files:
            root_node = self._build_node_tree(sorted_files)
            dir_sizes: dict[int, int] = {}
            if self.accumulate_size:
                dir_sizes[id(root_node)] = self._calculate_node_sizes(root_node)

                def _compute_sizes(n: _XmlNode) -> None:
                    """Recursively compute directory node sizes."""
                    for c in n.children.values():
                        if c.is_dir:
                            dir_sizes[id(c)] = self._calculate_node_sizes(c)
                            _compute_sizes(c)

                _compute_sizes(root_node)

            self._convert_node_to_xml(root_node, root, dir_sizes)

        if not self.no_indent:
            ET.indent(root, space="  ")

        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        xml_text = cast("str", xml_bytes.decode("utf-8"))
        return xml_text + "\n"

    @override
    def stream(self, files: Iterable[FileInfo], stream: TextIO) -> None:
        """Stream formatted XML output directly to a text stream.

        Args:
            files: Iterable of classified file objects.
            stream: Target text stream.
        """
        stream.write(self.format(files))
        stream.flush()
