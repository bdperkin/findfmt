"""Differential fuzz target for findfmt Rust (_rust_ext) and pure-Python file classification."""

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

try:
    from findfmt import _rust_ext
except ImportError:
    _rust_ext = None

if atheris is not None:
    with atheris.instrument_imports():
        from findfmt import _fallback, core
        from findfmt.classifier import extract_shebang, get_known_tags
else:
    from findfmt import _fallback, core
    from findfmt.classifier import extract_shebang, get_known_tags


def _build_candidate_path(tmpdir: str, ext: str, selector: int) -> Path:
    """Construct a fuzz candidate path including optional POSIX surrogateescape bytes."""
    clean_ext = "".join(c for c in ext if c.isalnum() or c in ".-_")[:15]
    base_dir = Path(tmpdir)
    if os.name == "posix" and (selector & 1) == 1:
        raw_base = os.fsencode(base_dir)
        suffix = os.fsencode(clean_ext or ".py")
        raw_name = b"/fuzz_raw_\xff_" + suffix
        return Path(os.fsdecode(raw_base + raw_name))

    filename = f"fuzz_input_{os.getpid()}_{clean_ext}" if clean_ext else f"fuzz_input_{os.getpid()}"
    return base_dir / filename


def TestOneInput(data: bytes) -> None:  # noqa: N802 - Atheris TestOneInput contract
    """Fuzz classify_file_rs, classify_batch_rs, core, and _fallback against arbitrary byte inputs.

    Args:
        data: Raw randomized bytes supplied by the fuzz engine.
    """
    if len(data) < 2:
        return

    known = get_known_tags()
    assert isinstance(known, frozenset)

    if atheris is not None:
        fdp = atheris.FuzzedDataProvider(data)
        selector = fdp.ConsumeIntInRange(0, 7)
        ext_len = fdp.ConsumeIntInRange(0, 12)
        ext = fdp.ConsumeUnicodeNoSurrogates(ext_len)
        content = fdp.ConsumeBytes(fdp.remaining_bytes())
    else:
        selector = data[0]
        ext = ".py" if len(data) % 2 == 0 else ""
        content = data

    with tempfile.TemporaryDirectory() as tmpdir:
        target_path = _build_candidate_path(tmpdir, ext, selector)
        with contextlib.suppress(OSError):
            target_path.write_bytes(content)
            if (selector & 2) != 0:
                target_path.chmod(0o755)

        if not target_path.exists():
            return

        with contextlib.suppress(OSError, ValueError, UnicodeDecodeError):
            py_info = _fallback.classify_file(target_path)
            core_info = core.classify_file(target_path)
            assert core_info == py_info
            assert py_info.path == target_path.resolve()
            assert isinstance(py_info.tags, frozenset)
            assert isinstance(py_info.is_executable, bool)
            assert isinstance(py_info.is_symlink, bool)
            assert isinstance(py_info.size_bytes, int)

            if _rust_ext is not None:
                rs_info = _rust_ext.classify_file_rs(target_path)
                assert rs_info == py_info
                batch_info = _rust_ext.classify_batch_rs([(target_path, None, None)])
                assert batch_info == [py_info]

            _ = extract_shebang(target_path)


def main() -> None:
    """Main fuzzing entry point for Atheris."""
    if atheris is not None:
        atheris.Setup(sys.argv, TestOneInput)
        atheris.Fuzz()
    else:
        sys.stderr.write("Atheris not installed; standalone execution complete.\n")


if __name__ == "__main__":
    main()
