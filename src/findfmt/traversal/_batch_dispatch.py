"""Bounded-chunk candidate classification and streaming emission helpers (#583)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from findfmt.traversal._pruning import ACTIVE_RUST_BATCH_HOOKS
from findfmt.traversal.filters import matches_filter
from findfmt.traversal.patterns import matches_pattern_criteria

if TYPE_CHECKING:
    import os
    from collections.abc import Callable, Iterable, Iterator, Sequence
    from pathlib import Path

    from findfmt.models import FileInfo, TraversalConfig
    from findfmt.traversal.patterns import PatternMatcher

RUST_BATCH_CHUNK_SIZE = 256

__all__ = [
    "RUST_BATCH_CHUNK_SIZE",
    "BatchEmitContext",
    "emit_classified_chunk",
    "stream_classified_candidates",
]


@dataclass(frozen=True, slots=True)
class BatchEmitContext:
    """Execution parameters for bounded-chunk candidate classification."""

    config: TraversalConfig
    base_root: Path
    prefix: Path | None
    matcher: PatternMatcher | None
    inherited_match: bool
    classify_fn: Callable[..., FileInfo]
    use_batch_hooks: bool


def emit_classified_chunk(
    chunk: Sequence[tuple[Path, os.DirEntry[str] | None, int | None]],
    ctx: BatchEmitContext,
) -> Iterator[FileInfo]:
    """Classify one bounded chunk via native batch hooks or per-file fallback."""
    hooks = ACTIVE_RUST_BATCH_HOOKS.get() if ctx.use_batch_hooks else None
    batch_infos = hooks[1](chunk, ctx.config, ctx.base_root, ctx.prefix) if hooks is not None else None
    if batch_infos is not None:
        for info in batch_infos:
            if matches_pattern_criteria(
                info,
                ctx.config,
                matcher=ctx.matcher,
                inherited_match=ctx.inherited_match,
            ):
                yield info

        return

    for path, entry, accum_size in chunk:
        info = ctx.classify_fn(
            path,
            root_path=ctx.base_root,
            prefix=ctx.prefix,
            accumulated_size=accum_size,
            entry=entry,
            follow_symlinks=ctx.config.follow_symlinks,
        )
        if matches_filter(
            info,
            ctx.config,
            matcher=ctx.matcher,
            inherited_match=ctx.inherited_match,
        ):
            yield info


def stream_classified_candidates(
    candidates: Iterable[tuple[Path, os.DirEntry[str] | None, int | None]],
    ctx: BatchEmitContext,
) -> Iterator[FileInfo]:
    """Classify and yield matching FileInfo records in ordered, bounded chunks."""
    chunk: list[tuple[Path, os.DirEntry[str] | None, int | None]] = []
    for candidate in candidates:
        chunk.append(candidate)
        if len(chunk) >= RUST_BATCH_CHUNK_SIZE:
            yield from emit_classified_chunk(chunk, ctx)
            chunk = []

    if chunk:
        yield from emit_classified_chunk(chunk, ctx)
