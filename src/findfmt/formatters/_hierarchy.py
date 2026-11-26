"""Shared hierarchical directory/file tree nodes and size aggregation for HTML and XML formatters."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from findfmt.models import FileInfo

__all__ = [
    "HierarchyNode",
    "build_hierarchy_tree",
    "compute_accumulated_dir_sizes",
    "ensure_dir_path",
]


class HierarchyNode:
    """Internal hierarchical node representing a directory or file entry."""

    __slots__ = ("children", "file_info", "is_dir", "name", "path")

    def __init__(
        self,
        name: str,
        path: Path,
        *,
        is_dir: bool,
        file_info: FileInfo | None = None,
    ) -> None:
        """Initialize a hierarchical directory or file node."""
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.file_info = file_info
        self.children: dict[str, HierarchyNode] = {}


def ensure_dir_path(
    root_node: HierarchyNode,
    dir_parts: tuple[str, ...],
    *,
    is_abs: bool,
) -> tuple[HierarchyNode, Path]:
    """Descend or create intermediate directory nodes along path parts."""
    curr = root_node
    accum_path = Path(dir_parts[0]) if (is_abs and dir_parts) else Path()
    for part in dir_parts:
        accum_path = accum_path / part
        if part not in curr.children:
            curr.children[part] = HierarchyNode(part, accum_path, is_dir=True)

        curr = curr.children[part]

    return curr, accum_path


def build_hierarchy_tree(
    sorted_files: list[FileInfo],
    *,
    absolute: bool,
) -> HierarchyNode:
    """Construct a hierarchical node tree from classified file records."""
    root_name = "/" if absolute else "."
    root_node = HierarchyNode(root_name, Path(root_name), is_dir=True)

    for file_info in sorted_files:
        target_path = file_info.path if absolute else file_info.relative_path
        is_abs = target_path.is_absolute()
        parts = target_path.parts
        dir_parts = tuple(parts[1:-1] if is_abs else parts[:-1])

        curr, accum_path = ensure_dir_path(root_node, dir_parts, is_abs=is_abs)
        filename = parts[-1] if parts else str(target_path)
        leaf_path = accum_path / filename if len(parts) > 1 else target_path
        is_dir = file_info.indicator == "/" or "directory" in file_info.tags
        if filename in curr.children:
            curr.children[filename].file_info = file_info
            curr.children[filename].is_dir = is_dir
        else:
            curr.children[filename] = HierarchyNode(
                filename,
                leaf_path,
                is_dir=is_dir,
                file_info=file_info,
            )

    return root_node


def _populate_node_sizes(node: HierarchyNode, dir_sizes: dict[int, int]) -> int:
    """Compute accumulated byte size for a node and record directory totals."""
    size = node.file_info.size_bytes if (node.file_info and not node.is_dir) else 0
    for child in node.children.values():
        size += _populate_node_sizes(child, dir_sizes)

    if node.is_dir:
        dir_sizes[id(node)] = size

    return size


def compute_accumulated_dir_sizes(root_node: HierarchyNode) -> dict[int, int]:
    """Return mapping of directory node object id to recursive accumulated byte size."""
    dir_sizes: dict[int, int] = {}
    _populate_node_sizes(root_node, dir_sizes)
    return dir_sizes
