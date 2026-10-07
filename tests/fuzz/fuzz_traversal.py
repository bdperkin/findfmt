"""Fuzz target for findfmt directory traversal and gitignore filtering."""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
from pathlib import Path

try:
    import atheris  # ty: ignore[unresolved-import]
except ImportError:
    atheris = None

if atheris is not None:
    with atheris.instrument_imports():
        from findfmt.models import FileInfo, TraversalConfig
        from findfmt.traversal import (
            load_git_exclude_spec,
            load_gitignore_spec,
            matches_filter,
            traverse_directory,
        )
else:
    from findfmt.models import FileInfo, TraversalConfig
    from findfmt.traversal import (
        load_git_exclude_spec,
        load_gitignore_spec,
        matches_filter,
        traverse_directory,
    )


def _setup_synthetic_tree(
    root: Path,
    gitignore_text: str,
    file_payloads: list[bytes],
) -> tuple[Path, Path]:
    """Create a synthetic directory tree with gitignore and symlinks."""
    gitignore_path = root / ".gitignore"
    with contextlib.suppress(OSError):
        gitignore_path.write_text(gitignore_text, encoding="utf-8", errors="replace")

    git_dir = root / ".git" / "info"
    git_dir.mkdir(parents=True, exist_ok=True)
    exclude_path = git_dir / "exclude"
    with contextlib.suppress(OSError):
        exclude_path.write_text(gitignore_text, encoding="utf-8", errors="replace")

    sub_dir = root / "subdir_alpha"
    sub_dir.mkdir(exist_ok=True)

    for idx, payload in enumerate(file_payloads):
        parent = sub_dir if idx % 2 == 0 else root
        fpath = parent / f"fuzz_file_{os.getpid()}_{idx}.dat"
        with contextlib.suppress(OSError):
            fpath.write_bytes(payload)

    link_path = root / "symlink_dir"
    with contextlib.suppress(OSError):
        link_path.symlink_to(sub_dir)

    return sub_dir, link_path


def TestOneInput(data: bytes) -> None:  # noqa: N802
    """Fuzz directory traversal, symlink resolution, and gitignore filtering.

    Args:
        data: Raw randomized bytes supplied by the fuzz engine.
    """
    if len(data) < 4:
        return

    if atheris is not None:
        fdp = atheris.FuzzedDataProvider(data)
        gitignore_text = fdp.ConsumeUnicodeNoSurrogates(100)
        filter_tag = fdp.ConsumeUnicodeNoSurrogates(30)
        num_files = fdp.ConsumeIntInRange(1, 4)
        file_payloads = [fdp.ConsumeBytes(min(40, fdp.remaining_bytes())) for _ in range(num_files)]
    else:
        gitignore_text = "*.tmp\nbuild/\n!build/keep.txt\n"
        filter_tag = "python"
        file_payloads = [data[:20], data[20:40]]

    clean_tag = filter_tag.strip().lower()[:20]
    candidate_tags = frozenset([clean_tag]) if clean_tag else frozenset(["text"])

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _setup_synthetic_tree(root, gitignore_text, file_payloads)

        _ = load_gitignore_spec(root)
        _ = load_git_exclude_spec(root)

        config = TraversalConfig(
            root_paths=(root,),
            include_tags=candidate_tags,
            respect_gitignore=True,
            include_hidden=True,
        )

        sample_info = FileInfo(
            path=root / "sample.py",
            relative_path=Path("sample.py"),
            tags=candidate_tags,
            shebang="#!/usr/bin/env python3",
            mime_type="text/x-python",
            is_executable=True,
            is_symlink=False,
            size_bytes=100,
        )
        _ = matches_filter(sample_info, config)

        with contextlib.suppress(OSError, ValueError):
            for item in traverse_directory(root, config):
                assert item.path.exists() or item.is_symlink
                _ = matches_filter(item, config)


def main() -> None:
    """Main fuzzing entry point for Atheris."""
    if atheris is not None:
        atheris.Setup(sys.argv, TestOneInput)
        atheris.Fuzz()
    else:
        sys.stderr.write("Atheris not installed; standalone execution complete.\n")


if __name__ == "__main__":
    main()
