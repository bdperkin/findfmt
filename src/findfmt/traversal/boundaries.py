"""Directory traversal boundaries and pruning evaluation engine."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from findfmt.classifier import classify_file as _py_classify_file
from findfmt.traversal._batch_dispatch import BatchEmitContext, stream_classified_candidates
from findfmt.traversal._descendants import (
    DescendantSearchState,
    PruneStepTarget,
    inspect_entries_for_match,
    search_matching_descendants,
)
from findfmt.traversal._pruning import (
    ACTIVE_RUST_BATCH_HOOKS,
    _can_skip_candidate_file,
    check_depth_limit,
    check_file_limit,
    is_candidate_file_entry,
    should_skip_dir,
)
from findfmt.traversal.devices import check_device_boundary, resolve_device
from findfmt.traversal.filters import matches_filter
from findfmt.traversal.ignore import (
    is_path_ignored,
    load_child_specs,
    resolve_active_specs,
)
from findfmt.traversal.symlinks import init_visited_dirs, should_skip_symlink_dir
from findfmt.traversal.tags import can_skip_file_by_tags

if TYPE_CHECKING:
    import os
    import sys
    from collections.abc import Callable, Iterator, MutableMapping, Sequence

    import pathspec

    if sys.version_info >= (3, 12):
        from typing import Unpack
    else:
        from typing_extensions import Unpack

    from findfmt.models import FileInfo, TraversalConfig
    from findfmt.traversal._pruning import ClassifyKwargs
    from findfmt.traversal.patterns import PatternMatcher

    PathSpecType = pathspec.PathSpec[Any]
else:
    PathSpecType = Any


def classify_file(
    path: Path,
    root_path: Path | None = None,
    prefix: Path | None = None,
    accumulated_size: int | None = None,
    **kwargs: Unpack[ClassifyKwargs],
) -> FileInfo:
    """Classify a traversal item via the active runtime gateway or pure-Python classifier."""
    hooks = ACTIVE_RUST_BATCH_HOOKS.get()
    target = hooks[0] if hooks is not None else _py_classify_file
    return target(path, root_path, prefix, accumulated_size, **kwargs)


_DEFAULT_CLASSIFY: Callable[..., FileInfo] = classify_file

__all__ = [
    "can_skip_file_by_tags",
    "check_depth_limit",
    "check_device_boundary",
    "check_file_limit",
    "filter_directory_entry",
    "has_matching_descendants",
    "init_visited_dirs",
    "is_candidate_file_entry",
    "matches_filter",
    "resolve_active_specs",
    "resolve_device",
    "should_skip_dir",
    "should_skip_symlink_dir",
    "yield_matching_items",
]


def _is_entry_excluded(  # noqa: PLR0913 - wide CLI/config signature
    entry_path: Path,
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    is_dir: bool,
    matcher: PatternMatcher | None,
    base_root: Path | None,
) -> bool:
    """Check if entry path is ignored by gitignore or excluded by pattern matcher."""
    if (config.respect_gitignore or specs) and is_path_ignored(
        entry_path,
        is_dir=is_dir,
        specs=specs,
    ):
        return True

    return bool(matcher and matcher.should_exclude(entry_path, is_dir=is_dir, base_root=base_root))


def filter_directory_entry(  # noqa: PLR0913 - wide CLI/config signature
    entry: os.DirEntry[str],
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    root_dev: int | None,
    *,
    matcher: PatternMatcher | None = None,
    base_root: Path | None = None,
) -> tuple[Path, bool] | None:
    """Filter an entry based on hidden status, device boundary, and gitignore."""
    if not config.include_hidden and entry.name.startswith("."):
        return None

    entry_path = Path(entry.path)
    if root_dev is not None and not check_device_boundary(
        entry_path,
        root_dev,
        entry=entry,
        follow_symlinks=config.follow_symlinks,
    ):
        return None

    try:
        is_dir = entry.is_dir(follow_symlinks=config.follow_symlinks)
    except (OSError, RuntimeError):
        return None

    if _is_entry_excluded(
        entry_path,
        config,
        specs,
        is_dir=is_dir,
        matcher=matcher,
        base_root=base_root,
    ):
        return None

    return entry_path, is_dir


def _inspect_entries(  # noqa: PLR0913 - wide CLI/config signature
    entries: Sequence[os.DirEntry[str]],
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    root_dev: int | None,
    *,
    matcher: PatternMatcher | None = None,
    inherited_match: bool = False,
    base_root: Path | None = None,
) -> tuple[list[Path], bool]:
    """Inspect directory entries and return discovered subdirs or match flag."""
    state = DescendantSearchState(
        config=config,
        root_dev=root_dev,
        matcher=matcher,
        filter_entry_fn=filter_directory_entry,
        classify_fn=classify_file,
        active_visited=set(),
        active_memo={},
        frames=[],
        on_error=None,
    )
    return inspect_entries_for_match(
        entries,
        specs,
        inherited_match=inherited_match,
        base_root=base_root,
        state=state,
    )


def has_matching_descendants(  # noqa: PLR0913 - wide CLI/config signature
    directory: Path,
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    root_dev: int | None = None,
    current_depth: int = 1,
    matcher: PatternMatcher | None = None,
    inherited_match: bool = False,
    base_root: Path | None = None,
    visited: set[tuple[int, int]] | None = None,
    memo: dict[tuple[int, int], bool] | None = None,
    on_error: Callable[[OSError], None] | None = None,
) -> bool:
    """Determine whether a directory or any subtrees contain matching files."""
    resolved_memo: MutableMapping[Any, bool] = (
        cast("MutableMapping[Any, bool]", memo) if memo is not None else {}
    )
    state = DescendantSearchState(
        config=config,
        root_dev=root_dev,
        matcher=matcher,
        filter_entry_fn=filter_directory_entry,
        classify_fn=classify_file,
        active_visited=visited if visited is not None else set(),
        active_memo=resolved_memo,
        frames=[],
        on_error=on_error,
    )
    target = PruneStepTarget(
        directory=directory,
        specs=specs,
        current_depth=current_depth,
        inherited_match=inherited_match,
        base_root=base_root,
    )
    return search_matching_descendants(target, state)


def _should_skip_dir_prune(  # noqa: PLR0913 - wide CLI/config signature
    path: Path,
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    base_root: Path,
    root_dev: int | None,
    current_depth: int,
    matcher: PatternMatcher | None,
    inherited_match: bool,
    prune_memo: dict[tuple[int, int], bool] | None = None,
    on_error: Callable[[OSError], None] | None = None,
) -> bool:
    """Determine if a directory should be skipped due to empty pruning."""
    if not (config.dirs_only and config.prune_empty):
        return False

    child_specs = load_child_specs(path, specs) if config.respect_gitignore else specs
    return not has_matching_descendants(
        path,
        config,
        child_specs,
        root_dev=root_dev,
        current_depth=current_depth + 1,
        matcher=matcher,
        inherited_match=inherited_match,
        base_root=base_root,
        memo=prune_memo,
        on_error=on_error,
    )


def _iter_eligible_candidates(  # noqa: PLR0913 - wide CLI/config signature
    targets: Sequence[Path | tuple[Path, os.DirEntry[str]]],
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    base_root: Path,
    prefix: Path | None,
    root_dev: int | None,
    current_depth: int,
    matcher: PatternMatcher | None,
    inherited_match: bool,
    accumulated_sizes: dict[Path, int] | None,
    prune_memo: dict[tuple[int, int], bool] | None,
    on_error: Callable[[OSError], None] | None,
) -> Iterator[tuple[Path, os.DirEntry[str] | None, int | None]]:
    """Yield eligible candidate tuples lazily before bounded-chunk classification."""
    for item in targets:
        path, entry = item if isinstance(item, tuple) else (item, None)
        if _should_skip_dir_prune(
            path,
            config,
            specs,
            base_root=base_root,
            root_dev=root_dev,
            current_depth=current_depth,
            matcher=matcher,
            inherited_match=inherited_match,
            prune_memo=prune_memo,
            on_error=on_error,
        ):
            continue

        if not config.dirs_only and _can_skip_candidate_file(
            path,
            entry,
            config,
            base_root=base_root,
            prefix=prefix,
            matcher=matcher,
            inherited_match=inherited_match,
        ):
            continue

        accum_size = accumulated_sizes.get(path) if accumulated_sizes is not None else None
        yield path, entry, accum_size


def yield_matching_items(  # noqa: PLR0913 - wide CLI/config signature
    targets: Sequence[Path | tuple[Path, os.DirEntry[str]]],
    config: TraversalConfig,
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    base_root: Path,
    prefix: Path | None,
    root_dev: int | None,
    current_depth: int,
    matcher: PatternMatcher | None = None,
    inherited_match: bool = False,
    accumulated_sizes: dict[Path, int] | None = None,
    prune_memo: dict[tuple[int, int], bool] | None = None,
    on_error: Callable[[OSError], None] | None = None,
) -> Iterator[FileInfo]:
    """Yield FileInfo records for candidate paths that satisfy filters and pruning."""
    eligible = _iter_eligible_candidates(
        targets,
        config,
        specs,
        base_root=base_root,
        prefix=prefix,
        root_dev=root_dev,
        current_depth=current_depth,
        matcher=matcher,
        inherited_match=inherited_match,
        accumulated_sizes=accumulated_sizes,
        prune_memo=prune_memo,
        on_error=on_error,
    )
    emit_ctx = BatchEmitContext(
        config=config,
        base_root=base_root,
        prefix=prefix,
        matcher=matcher,
        inherited_match=inherited_match,
        classify_fn=classify_file,
        use_batch_hooks=classify_file is _DEFAULT_CLASSIFY,
    )
    yield from stream_classified_candidates(eligible, emit_ctx)
