"""Iterative descendant-pruning search engine for --prune directory evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from findfmt.classifier import _resolve_relative
from findfmt.traversal._pruning import (
    _can_skip_entry_by_tags,
    _check_visited_or_memo,
    _PruneFrame,
    _scan_sorted_entries,
    check_depth_limit,
    is_candidate_file_entry,
    should_skip_dir,
)
from findfmt.traversal.filters import matches_filter
from findfmt.traversal.ignore import load_child_specs

if TYPE_CHECKING:
    import os
    from collections.abc import Callable, MutableMapping, Sequence
    from pathlib import Path

    import pathspec

    from findfmt.models import FileInfo, TraversalConfig
    from findfmt.traversal.patterns import PatternMatcher

    PathSpecType = pathspec.PathSpec[Any]
    FilterEntryFn = Callable[..., tuple[Path, bool] | None]
else:
    PathSpecType = Any

__all__ = [
    "DescendantSearchState",
    "PruneStepTarget",
    "inspect_entries_for_match",
    "search_matching_descendants",
]


@dataclass(slots=True)
class DescendantSearchState:
    """Mutable traversal state and callbacks for iterative descendant pruning."""

    config: TraversalConfig
    root_dev: int | None
    matcher: PatternMatcher | None
    filter_entry_fn: FilterEntryFn
    classify_fn: Callable[..., FileInfo]
    active_visited: set[tuple[int, int]]
    active_memo: MutableMapping[Any, bool]
    frames: list[_PruneFrame]
    on_error: Callable[[OSError], None] | None


@dataclass(frozen=True, slots=True)
class PruneStepTarget:
    """Target directory parameters for a single descendant-pruning step."""

    directory: Path
    specs: tuple[tuple[Path, PathSpecType], ...]
    current_depth: int
    inherited_match: bool
    base_root: Path | None


def inspect_entries_for_match(
    entries: Sequence[os.DirEntry[str]],
    specs: tuple[tuple[Path, PathSpecType], ...],
    *,
    inherited_match: bool,
    base_root: Path | None,
    state: DescendantSearchState,
) -> tuple[list[Path], bool]:
    """Inspect directory entries and return discovered subdirs or immediate match flag."""
    subdirs: list[Path] = []
    config = state.config
    for entry in entries:
        filtered = state.filter_entry_fn(
            entry,
            config,
            specs,
            state.root_dev,
            matcher=state.matcher,
            base_root=base_root,
        )
        if filtered is None:
            continue

        entry_path, is_dir = filtered
        if is_dir:
            if not should_skip_dir(entry.name, include_hidden=config.include_hidden):
                subdirs.append(entry_path)
        elif is_candidate_file_entry(entry, follow_symlinks=config.follow_symlinks):
            if _can_skip_entry_by_tags(entry, config, filename=entry.name):
                continue

            info = state.classify_fn(
                entry_path,
                root_path=base_root,
                entry=entry,
                follow_symlinks=config.follow_symlinks,
            )
            if matches_filter(
                info,
                config,
                matcher=state.matcher,
                inherited_match=inherited_match,
            ):
                return [], True

    return subdirs, False


def _make_memo_key(
    dir_key: tuple[int, int],
    target: PruneStepTarget,
    state: DescendantSearchState,
) -> tuple[int, int] | tuple[int, int, Path]:
    """Build a root-relative path-scoped memo key when symlink aliases can diverge."""
    config = state.config
    matcher = state.matcher
    has_patterns = matcher is not None and (matcher.has_includes or matcher.has_excludes)
    if config.follow_symlinks and (has_patterns or bool(target.specs) or config.gitignore_file is not None):
        return (*dir_key, _resolve_relative(target.directory, target.base_root))

    return dir_key


def _step_prune_directory(target: PruneStepTarget, state: DescendantSearchState) -> bool:
    """Inspect a single directory for matching files or push its subdirs onto stack."""
    try:
        st = target.directory.stat()
        dir_key = (st.st_dev, st.st_ino)
    except (OSError, RuntimeError):
        return False

    memo_key = _make_memo_key(dir_key, target, state)
    cached, val = _check_visited_or_memo(dir_key, memo_key, state.active_visited, state.active_memo)
    if cached:
        return val

    entries = _scan_sorted_entries(
        target.directory,
        state.active_memo,
        memo_key,
        on_error=state.on_error,
    )
    if entries is None:
        return False

    subdirs, found = inspect_entries_for_match(
        entries,
        target.specs,
        inherited_match=target.inherited_match,
        base_root=target.base_root,
        state=state,
    )
    if found:
        state.active_memo[memo_key] = True
        return True

    if not subdirs or not check_depth_limit(target.current_depth, state.config.max_depth):
        if not subdirs:
            state.active_memo[memo_key] = False

        return False

    state.active_visited.add(dir_key)
    effective_root = target.base_root if target.base_root is not None else target.directory
    state.frames.append(
        _PruneFrame(
            dir_key=dir_key,
            memo_key=memo_key,
            subdirs=subdirs,
            specs=target.specs,
            depth=target.current_depth,
            inherited_match=target.inherited_match,
            effective_root=effective_root,
        ),
    )
    return False


def _step_prune_subdir(top: _PruneFrame, state: DescendantSearchState) -> bool:
    """Advance top prune frame by one subdirectory and return True on immediate match."""
    subdir = top.subdirs[top.idx]
    top.idx += 1
    child_specs = load_child_specs(subdir, top.specs) if state.config.respect_gitignore else top.specs
    child_inherit = bool(
        state.matcher
        and state.matcher.should_inherit_match(
            subdir,
            base_root=top.effective_root,
            parent_inherited=top.inherited_match,
        ),
    )
    return _step_prune_directory(
        PruneStepTarget(
            directory=subdir,
            specs=child_specs,
            current_depth=top.depth + 1,
            inherited_match=child_inherit,
            base_root=top.effective_root,
        ),
        state,
    )


def search_matching_descendants(target: PruneStepTarget, state: DescendantSearchState) -> bool:
    """Execute iterative depth-first descendant search using memoized directory keys."""
    if _step_prune_directory(target, state):
        return True

    try:
        while state.frames:
            top = state.frames[-1]
            if top.idx >= len(top.subdirs):
                state.frames.pop()
                state.active_visited.discard(top.dir_key)
                if state.config.max_depth is None:
                    state.active_memo[top.memo_key] = False
            elif _step_prune_subdir(top, state):
                if state.config.max_depth is None:
                    for frame in state.frames:
                        state.active_memo[frame.memo_key] = True

                return True
    finally:
        for frame in state.frames:
            state.active_visited.discard(frame.dir_key)

    return False
