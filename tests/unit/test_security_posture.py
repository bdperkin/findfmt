"""Regression tests for ClusterFuzzLite dependency pinning, SECURITY.md policy, and FIFO safety."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

from findfmt.classifier import extract_shebang

ROOT = Path(__file__).resolve().parents[2]
IMAGE_DIGEST_RE = re.compile(r"^FROM\s+\S+@sha256:[0-9a-f]{64}(?:\s+AS\s+\S+)?$")
HASH_FLAG_RE = re.compile(r"--hash=sha256:[0-9a-f]{64}\b")


def test_extract_shebang_fifo_never_blocks(tmp_path: Path) -> None:
    """Verify standalone extract_shebang opens with O_NONBLOCK + fstat and skips FIFOs."""
    if hasattr(os, "mkfifo"):
        fifo_path = tmp_path / "shebang.pipe"
        os.mkfifo(fifo_path)
        with (
            patch("os.open", wraps=os.open) as spy_open,
            patch("os.read", wraps=os.read) as spy_read,
        ):
            assert extract_shebang(fifo_path) is None

        assert spy_open.called
        assert (spy_open.call_args.args[1] & getattr(os, "O_NONBLOCK", 0)) != 0
        spy_read.assert_not_called()

    mock_path = tmp_path / "mock_shebang.pipe"
    mock_path.write_text("#!/bin/sh\necho 1\n", encoding="utf-8")
    mock_stat = MagicMock(spec=os.stat_result)
    mock_stat.st_mode = stat.S_IFIFO | 0o600
    with (
        patch("os.open", return_value=77),
        patch("os.fstat", return_value=mock_stat),
        patch("os.read") as mock_read,
        patch("os.close") as mock_close,
    ):
        assert extract_shebang(mock_path) is None

    mock_read.assert_not_called()
    mock_close.assert_called_once_with(77)


def test_clusterfuzzlite_dockerfile_pins_all_dependencies_by_hash() -> None:
    """Verify .clusterfuzzlite/Dockerfile has no unpinned curl|sh or pip commands (#85, #86)."""
    dockerfile = (ROOT / ".clusterfuzzlite" / "Dockerfile").read_text(encoding="utf-8")
    from_lines = [
        line.strip() for line in dockerfile.splitlines() if line.strip().upper().startswith("FROM ")
    ]
    assert len(from_lines) >= 2
    for line in from_lines:
        assert IMAGE_DIGEST_RE.match(line), f"Unpinned Dockerfile stage: {line!r}"

    assert "sh.rustup.rs" not in dockerfile
    assert "curl " not in dockerfile
    assert "wget " not in dockerfile

    for line in dockerfile.splitlines():
        if "pip install" in line:
            assert "--require-hashes" in line, f"pip install missing --require-hashes: {line!r}"

    build_reqs = (ROOT / ".clusterfuzzlite" / "build-requirements.txt").read_text(encoding="utf-8")
    assert re.search(r"^maturin==\d+\.\d+\.\d+", build_reqs, re.MULTILINE)
    assert HASH_FLAG_RE.search(build_reqs)


def test_security_md_documents_disclosure_sla_and_hybrid_rust_posture() -> None:
    """Verify SECURITY.md documents coordinated disclosure timelines and hybrid Rust controls."""
    security_md = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    for required in (
        "48 hours",
        "90-day coordinated disclosure",
        "findfmt_rs",
        "#![forbid(unsafe_code)]",
        "PanicException",
        "2,048",
        "O_NONBLOCK",
        "proptest",
        "cargo-fuzz",
    ):
        assert required in security_md, (
            f"SECURITY.md missing expected security governance detail: {required!r}"
        )
