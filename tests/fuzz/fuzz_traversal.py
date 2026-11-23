"""Differential fuzz target for findfmt Rust-accelerated and fallback directory traversal."""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
from pathlib import Path

try:
    import atheris  # ty: ignore[import-not-found]
except ImportError:
    atheris = None

if atheris is not None:
    with atheris.instrument_imports():
        from findfmt import _fallback, core
        from findfmt.models import FileInfo, SortKey, TraversalConfig
        from findfmt.traversal import (
            load_git_exclude_spec,
            load_gitignore_spec,
            matches_filter,
        )

        try:
            from findfmt import _rust_ext
        except ImportError:
            _rust_ext = None
else:
    from findfmt import _fallback, core
    from findfmt.models import FileInfo, SortKey, TraversalConfig
    from findfmt.traversal import (
        load_git_exclude_spec,
        load_gitignore_spec,
        matches_filter,
    )

    try:
        from findfmt import _rust_ext
    except ImportError:
        _rust_ext = None

_SORT_KEYS: tuple[SortKey, ...] = (
    SortKey.NAME,
    SortKey.VERSION,
    SortKey.SIZE,
    SortKey.MTIME,
    SortKey.CTIME,
)


def _setup_synthetic_tree(
    root: Path,
    gitignore_text: str,
    file_payloads: list[bytes],
) -> tuple[Path, Path]:
    """Create a synthetic directory tree with deterministic timestamps, gitignore, and symlinks."""
    base_ts = 1_700_000_000
    gitignore_path = root / ".gitignore"
    with contextlib.suppress(OSError):
        gitignore_path.write_text(gitignore_text, encoding="utf-8", errors="replace")
        os.utime(gitignore_path, (base_ts, base_ts))

    git_dir = root / ".git" / "info"
    git_dir.mkdir(parents=True, exist_ok=True)
    exclude_path = git_dir / "exclude"
    with contextlib.suppress(OSError):
        exclude_path.write_text(gitignore_text, encoding="utf-8", errors="replace")
        os.utime(exclude_path, (base_ts + 1, base_ts + 1))

    sub_dir = root / "v2_subdir"
    sub_dir.mkdir(exist_ok=True)

    for idx, payload in enumerate(file_payloads):
        parent = sub_dir if idx % 2 == 0 else root
        ext = ".py" if idx % 2 == 0 else ".dat"
        fpath = parent / f"fuzz_{os.getpid()}_v{idx + 1}{ext}"
        with contextlib.suppress(OSError):
            fpath.write_bytes(payload)
            file_ts = base_ts + 10 + idx * 10
            os.utime(fpath, (file_ts, file_ts))

    link_path = root / "symlink_dir"
    with contextlib.suppress(OSError):
        link_path.symlink_to(sub_dir, target_is_directory=True)

    with contextlib.suppress(OSError):
        os.utime(sub_dir, (base_ts + 100, base_ts + 100))
        os.utime(git_dir, (base_ts + 110, base_ts + 110))

    return sub_dir, link_path


def TestOneInput(data: bytes) -> None:  # noqa: N802 - Atheris TestOneInput contract
    """Fuzz directory traversal, sorting, symlinks, and gitignore across core and _fallback.

    Args:
        data: Raw randomized bytes supplied by the fuzz engine.
    """
    if len(data) < 4:
        return

    _ = _rust_ext  # Preserve top-level reference so PyInstaller bundles findfmt._rust_ext

    if atheris is not None:
        fdp = atheris.FuzzedDataProvider(data)
        flags = fdp.ConsumeIntInRange(0, 31)
        sort_idx = fdp.ConsumeIntInRange(0, len(_SORT_KEYS) - 1)
        gitignore_text = fdp.ConsumeUnicodeNoSurrogates(120)
        filter_tag = fdp.ConsumeUnicodeNoSurrogates(24)
        num_files = fdp.ConsumeIntInRange(1, 4)
        file_payloads = [fdp.ConsumeBytes(min(48, fdp.remaining_bytes())) for _ in range(num_files)]
    else:
        flags = data[0]
        sort_idx = data[1] % len(_SORT_KEYS)
        gitignore_text = data[:40].decode("utf-8", errors="replace")
        filter_tag = "file" if (data[2] & 1) == 0 else ""
        file_payloads = [data[:24], data[24:48]]

    clean_tag = filter_tag.strip().lower()[:20]
    candidate_tags = frozenset([clean_tag]) if clean_tag else frozenset()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        with contextlib.suppress(OSError, ValueError):
            _setup_synthetic_tree(root, gitignore_text, file_payloads)

            _ = load_gitignore_spec(root)
            _ = load_git_exclude_spec(root)

            config = TraversalConfig(
                root_paths=(root,),
                include_tags=candidate_tags,
                respect_gitignore=True,
                include_hidden=(flags & 1) == 0,
                follow_symlinks=(flags & 2) != 0,
                dirs_first=(flags & 4) != 0,
                reverse_sort=(flags & 8) != 0,
                sort_by=_SORT_KEYS[sort_idx],
            )

            sample_info = FileInfo(
                path=root / "sample.py",
                relative_path=Path("sample.py"),
                tags=candidate_tags or frozenset({"file", "python", "text"}),
                shebang="#!/usr/bin/env python3",
                mime_type="text/x-python",
                is_executable=True,
                is_symlink=False,
                size_bytes=100,
            )
            _ = matches_filter(sample_info, config)

            py_items = list(_fallback.find_files(config))
            rs_items = list(core.find_files(config))
            assert rs_items == py_items

            if _rust_ext is not None:
                direct_walker = getattr(_rust_ext, "find_files", None)
                if callable(direct_walker):
                    assert list(direct_walker(config)) == py_items

                file_candidates = [item.path for item in py_items if "directory" not in item.tags]
                if file_candidates:
                    direct_batch = _rust_ext.classify_batch_rs(
                        [(p, None, None) for p in file_candidates],
                        root_path=root,
                        follow_symlinks=config.follow_symlinks,
                    )
                    expected_batch = [
                        _fallback.classify_file(p, root_path=root, follow_symlinks=config.follow_symlinks)
                        for p in file_candidates
                    ]
                    assert direct_batch == expected_batch

            for item in rs_items:
                assert item.path.exists() or item.is_symlink


def main() -> None:
    """Main fuzzing entry point for Atheris."""
    if atheris is not None:
        atheris.Setup(sys.argv, TestOneInput)
        atheris.Fuzz()
    else:
        sys.stderr.write("Atheris not installed; standalone execution complete.\n")


if __name__ == "__main__":
    main()
