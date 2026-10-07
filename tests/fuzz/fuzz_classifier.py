"""Fuzz target for findfmt file classification and shebang extraction."""

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
        from findfmt.classifier import classify_file, extract_shebang, get_known_tags
else:
    from findfmt.classifier import classify_file, extract_shebang, get_known_tags


def TestOneInput(data: bytes) -> None:  # noqa: N802
    """Fuzz classify_file and extract_shebang against arbitrary byte inputs.

    Args:
        data: Raw randomized bytes supplied by the fuzz engine.
    """
    if len(data) < 2:
        return

    known = get_known_tags()
    assert isinstance(known, frozenset)

    if atheris is not None:
        fdp = atheris.FuzzedDataProvider(data)
        ext_len = fdp.ConsumeIntInRange(0, 10)
        ext = fdp.ConsumeUnicodeNoSurrogates(ext_len)
        content = fdp.ConsumeBytes(fdp.remaining_bytes())
    else:
        ext = ".txt" if len(data) % 2 == 0 else ""
        content = data

    clean_ext = "".join(c for c in ext if c.isalnum() or c in ".-_")[:15]
    filename = f"fuzz_input_{os.getpid()}_{clean_ext}" if clean_ext else f"fuzz_input_{os.getpid()}"

    with tempfile.TemporaryDirectory() as tmpdir:
        target_path = Path(tmpdir) / filename
        with contextlib.suppress(OSError):
            target_path.write_bytes(content)

        if not target_path.exists():
            return

        with contextlib.suppress(OSError, ValueError, UnicodeDecodeError):
            info = classify_file(target_path)
            assert info.path == target_path.resolve()
            assert isinstance(info.tags, frozenset)
            assert isinstance(info.is_executable, bool)
            assert isinstance(info.is_symlink, bool)
            assert isinstance(info.size_bytes, int)

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
