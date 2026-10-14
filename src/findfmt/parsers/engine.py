"""Ingestion coordinator and classification engine for external listings."""

from __future__ import annotations

import mimetypes
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import identify.identify as identify_engine

from findfmt.classifier import _adjust_nt_tags, classify_file
from findfmt.models import FileInfo, SortKey
from findfmt.parsers.flat_parser import parse_flat_listing
from findfmt.parsers.tab_parser import parse_tab_outline
from findfmt.traversal.boundaries import matches_filter
from findfmt.traversal.patterns import create_pattern_matcher
from findfmt.traversal.sorting import is_reverse_sort, natural_sort_key

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import TextIO

    from findfmt.models import TraversalConfig
    from findfmt.parsers.flat_parser import ParsedEntry

__all__ = [
    "classify_file_offline",
    "detect_input_format",
    "ingest_from_file",
]


def detect_input_format(lines: list[str]) -> str:
    """Auto-detect whether input lines represent an outline or flat path listing.

    Args:
        lines: List of raw input string lines.

    Returns:
        'outline' if indented hierarchical structure is detected, else 'flat'.
    """
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if line[0] in (" ", "\t") or stripped.startswith(("├──", "└──", "|--", "\\--")):
            return "outline"

    return "flat"


def classify_file_offline(
    path: Path,
    *,
    relative_path: Path,
    is_symlink: bool = False,
    symlink_target: str | None = None,
) -> FileInfo:
    """Classify a file based solely on filename heuristics without filesystem IO.

    Args:
        path: Representative path for the file.
        relative_path: Relative path representation.
        is_symlink: Flag indicating whether entry represents a symbolic link.
        symlink_target: Optional target path destination of the symlink.

    Returns:
        Populated FileInfo instance.
    """
    str_path = str(path)
    tags = set(identify_engine.tags_from_filename(path.name))
    if is_symlink:
        tags.add("symlink")

    mime_type, _ = mimetypes.guess_type(str_path)
    if mime_type:
        tags.add(f"mime:{mime_type}")
        tags.add(mime_type.split("/", 1)[0])

    is_executable = False
    if os.name == "nt":
        pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD;.VBS;.JS;.WS;.MSC").split(";")
        is_executable = any(path.name.upper().endswith(ext.upper()) for ext in pathext if ext)

    _adjust_nt_tags(tags, is_executable=is_executable)
    indicator = "@" if is_symlink else ("*" if is_executable else None)

    return FileInfo(
        path=path,
        relative_path=relative_path,
        tags=frozenset(tags),
        shebang=None,
        mime_type=mime_type,
        is_executable=is_executable,
        is_symlink=is_symlink,
        symlink_target=symlink_target,
        size_bytes=0,
        indicator=indicator,
    )


def _resolve_and_classify(
    entry: ParsedEntry,
    root: Path,
    config: TraversalConfig,
) -> FileInfo:
    """Resolve target path and classify entry via online or offline mechanisms."""
    raw_path = Path(entry.path_str)
    if raw_path.is_absolute():
        target_path = raw_path
        rel_path = raw_path.relative_to(root) if raw_path.is_relative_to(root) else raw_path
    else:
        rel_target = root / raw_path
        target_path = rel_target.resolve() if rel_target.exists() else rel_target
        rel_path = raw_path

    if config.offline:
        return classify_file_offline(
            target_path,
            relative_path=rel_path,
            is_symlink=entry.is_symlink,
            symlink_target=entry.symlink_target,
        )

    if target_path.exists():
        info = classify_file(target_path, root_path=root)
        if entry.is_symlink or entry.symlink_target is not None:
            new_tags = info.tags | frozenset({"symlink"})
            return replace(
                info,
                is_symlink=True,
                symlink_target=entry.symlink_target,
                tags=new_tags,
            )

        return info

    return classify_file_offline(
        target_path,
        relative_path=rel_path,
        is_symlink=entry.is_symlink,
        symlink_target=entry.symlink_target,
    )


def _read_lines(from_file: str | None, stream: TextIO | None = None) -> list[str]:
    """Read input lines from standard input or external file."""
    if from_file == "-":
        target_stream = stream or sys.stdin
        raw_text = target_stream.read()
        return [str(line) for line in raw_text.splitlines()]

    if from_file is not None:
        with Path(from_file).open(encoding="utf-8", errors="replace") as f:
            return [str(line) for line in f.read().splitlines()]

    return []


def _sort_file_infos(files: list[FileInfo], config: TraversalConfig) -> list[FileInfo]:
    """Sort FileInfo objects according to TraversalConfig criteria and grouping."""
    if config.sort_by == SortKey.NONE:
        return files

    sort_reverse = is_reverse_sort(config)

    def _key_fn(f: FileInfo) -> tuple[object, ...]:
        """Compute comparison key for FileInfo instance."""
        name = f.relative_path.name
        if config.sort_by == SortKey.VERSION:
            return (natural_sort_key(name, ignore_case=config.ignore_case),)

        if config.sort_by in (SortKey.TIME, SortKey.MTIME, SortKey.CTIME):
            try:
                mtime = f.path.stat().st_mtime if f.path.exists() else 0.0
            except OSError:
                mtime = 0.0

            return (mtime, name)

        if config.sort_by == SortKey.SIZE:
            return (f.size_bytes, name)

        return (name.lower() if config.ignore_case else name,)

    if config.dirs_first or config.files_first:
        dirs = [f for f in files if "directory" in f.tags or f.path.is_dir()]
        regular = [f for f in files if f not in dirs]
        dirs.sort(key=_key_fn, reverse=sort_reverse)
        regular.sort(key=_key_fn, reverse=sort_reverse)
        return dirs + regular if config.dirs_first else regular + dirs

    sorted_files = list(files)
    sorted_files.sort(key=_key_fn, reverse=sort_reverse)
    return sorted_files


def ingest_from_file(
    config: TraversalConfig,
    input_stream: TextIO | None = None,
) -> Iterator[FileInfo]:
    """Ingest path listings from an external file or standard input stream.

    Bypasses standard filesystem traversal, parses directory hierarchy
    or flat paths, classifies entries with online or offline fallback,
    and applies active filter criteria and sorting.

    Args:
        config: Traversal configuration containing from_file and offline flags.
        input_stream: Optional input text stream override for testing.

    Yields:
        Classified and filtered FileInfo instances.
    """
    lines = _read_lines(config.from_file, stream=input_stream)
    fmt = detect_input_format(lines)
    entries = parse_tab_outline(lines) if fmt == "outline" else parse_flat_listing(lines)

    root = config.root_paths[0] if config.root_paths else Path()
    matcher = create_pattern_matcher(config)
    matched: list[FileInfo] = []

    for entry in entries:
        if config.dirs_only and not entry.is_dir:
            continue

        if not config.dirs_only and entry.is_dir:
            continue

        info = _resolve_and_classify(entry, root, config)
        if matches_filter(info, config, matcher=matcher):
            matched.append(info)

    yield from _sort_file_infos(matched, config)
