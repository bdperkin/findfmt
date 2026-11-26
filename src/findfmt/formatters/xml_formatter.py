"""Hierarchical XML document serializer for directory traversal trees."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, TextIO, cast

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from findfmt.formatters._hierarchy import (
    HierarchyNode,
    build_hierarchy_tree,
    compute_accumulated_dir_sizes,
)
from findfmt.formatters._xml_sanitize import clean_xml_text
from findfmt.formatters.base import _MetadataFormatterBase, write_stream_safe
from findfmt.sizes import format_size
from findfmt.utils.strings import format_display_path, format_timestamp

if TYPE_CHECKING:
    from collections.abc import Iterable

    from findfmt.models import FileInfo

__all__ = ["XmlFormatter"]


class XmlFormatter(_MetadataFormatterBase):
    """Hierarchical XML document serializer utilizing ElementTree."""

    def __init__(  # noqa: PLR0913 - wide CLI/config signature
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
        self._set_ownership_options(permissions=show_permissions, user=show_user, group=show_group)
        self._set_stat_options(inodes=show_inodes, device=show_device, mtime=show_mtime, ctime=show_ctime)
        self.time_format = time_format
        self._set_size_options(exact=show_size, human=human_readable, si=show_si, accum=accumulate_size)
        self._set_path_options(classify=classify, ctrl=hide_control_chars, literal=literal, quote=quote_name)

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
        return clean_xml_text(val, literal=self.literal)

    def _apply_metadata_attrs(self, file_info: FileInfo, elem: ET.Element) -> None:
        """Populate optional metadata attributes on target XML element."""
        mt = format_timestamp(file_info.mtime, self.time_format) if file_info.mtime is not None else None
        ct = format_timestamp(file_info.ctime, self.time_format) if file_info.ctime is not None else None
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
        if file_info.symlink_target is not None and file_info.symlink_target:
            elem.set("symlink_target", str(self._clean_val(file_info.symlink_target)))

        self._apply_metadata_attrs(file_info, elem)

        for tag in sorted(file_info.tags):
            tag_elem = ET.SubElement(elem, "tag")
            tag_elem.text = self._clean_val(tag)

        if file_info.mime_type is not None and file_info.mime_type:
            mime_elem = ET.SubElement(elem, "mime")
            mime_elem.text = self._clean_val(file_info.mime_type)

        if file_info.shebang is not None and file_info.shebang:
            shebang_elem = ET.SubElement(elem, "shebang")
            shebang_elem.text = self._clean_val(file_info.shebang)

    def _convert_dir_node(
        self,
        node: HierarchyNode,
        parent: ET.Element,
        dir_sizes: dict[int, int] | None,
        display_name: str,
    ) -> None:
        """Serialize a directory node and recurse for children."""
        path_str = str(self._clean_val(str(node.path)))
        elem = ET.SubElement(
            parent,
            "directory",
            name=str(self._clean_val(display_name) or ""),
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
        node: HierarchyNode,
        parent: ET.Element,
        display_name: str,
    ) -> None:
        """Serialize a regular file leaf element."""
        path_str = str(self._clean_val(str(node.path)))
        elem = ET.SubElement(
            parent,
            "file",
            name=str(self._clean_val(display_name) or ""),
            path=path_str,
        )
        file_info = cast("FileInfo", node.file_info)
        self._apply_file_info(file_info, elem)

    def _convert_node_to_xml(
        self,
        node: HierarchyNode,
        parent: ET.Element,
        dir_sizes: dict[int, int] | None = None,
    ) -> None:
        """Recursively serialize HierarchyNode hierarchy into ElementTree elements."""
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
        sorted_files = list(files)

        root = ET.Element("tree")
        if sorted_files:
            root_node = build_hierarchy_tree(sorted_files, absolute=self.absolute)
            dir_sizes = compute_accumulated_dir_sizes(root_node) if self.accumulate_size else {}
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
        write_stream_safe(stream, self.format(files))
        stream.flush()
