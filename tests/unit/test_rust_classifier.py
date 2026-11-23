"""Unit and parity tests for native Rust single-file classification in findfmt._rust_ext (#583)."""

from __future__ import annotations

import importlib
import os
import socket
import stat
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from findfmt import _fallback, classifier, core
from findfmt.models import TraversalConfig

if TYPE_CHECKING:
    import types


def _load_rust_ext() -> types.ModuleType:
    """Import compiled findfmt._rust_ext or skip when built with HATCH_MATURIN_DISABLE=1."""
    try:
        return importlib.import_module("findfmt._rust_ext")
    except ModuleNotFoundError:
        pytest.skip("findfmt._rust_ext is not compiled in this environment")


def test_classify_file_rs_exact_parity_across_formats_and_shebangs(tmp_path: Path) -> None:
    """Verify classify_file_rs matches classifier.classify_file across formats, MIME, and shebangs."""
    rust_ext = _load_rust_ext()

    cases: list[tuple[str, bytes, bool]] = [
        ("app.py", b"import sys\n", False),
        ("Dockerfile.prod", b"FROM alpine:3.20\n", False),
        (".bashrc", b"export PATH=/usr/bin\n", False),
        (".hidden.py", b"x = 1\n", False),
        ("bundle.tgz", b"\x1f\x8b\x08\x00\x00\x00\x00\x00", False),
        ("empty_extless", b"", False),
        ("binary_extless", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", False),
        ("nul_after_1kb", (b"a" * 1024) + b"\x00tail", False),
        ("env_py", b"#!/usr/bin/env python3\nprint(1)\n", True),
        ("env_s_py", b"#!/usr/bin/env -S python3 -u\nprint(1)\n", True),
        ("quoted_sh", b'#!"/bin/bash" -e\necho ok\n', True),
        ("unclosed_quote", b"#!/bin/sh 'unclosed\necho ok\n", True),
        ("non_utf8_sb", b"#!/usr/bin/python3 \xff\nprint(1)\n", True),
        ("non_exec_sb", b"#!/usr/bin/env ruby\nputs 1\n", False),
        (
            "nix_script",
            b"#! /usr/bin/env nix-shell\n#! nix-shell -i bash -p bash\necho nix\n",
            True,
        ),
    ]

    for name, payload, executable in cases:
        file_path = tmp_path / name
        file_path.write_bytes(payload)
        if executable:
            file_path.chmod(file_path.stat().st_mode | stat.S_IXUSR)

        expected = classifier.classify_file(file_path, root_path=tmp_path)
        actual_rs = rust_ext.classify_file_rs(file_path, root_path=tmp_path)
        actual_alias = rust_ext.classify_file(file_path, root_path=tmp_path)
        assert actual_rs == expected, f"Mismatch on {name}"
        assert actual_alias == expected, f"Alias mismatch on {name}"

    rel_target = Path("pyproject.toml")
    assert rust_ext.classify_file_rs(rel_target) == classifier.classify_file(rel_target)

    sample = tmp_path / "app.py"
    assert rust_ext.classify_file_rs(
        sample,
        root_path=tmp_path,
        prefix=Path("pref"),
        accumulated_size=4096,
    ) == classifier.classify_file(
        sample,
        root_path=tmp_path,
        prefix=Path("pref"),
        accumulated_size=4096,
    )
    unrelated = Path("/unrelated/nonexistent/root")
    assert rust_ext.classify_file_rs(sample, root_path=unrelated) == classifier.classify_file(
        sample,
        root_path=unrelated,
    )
    missing = tmp_path / "does_not_exist.rs"
    assert rust_ext.classify_file_rs(missing, root_path=tmp_path) == classifier.classify_file(
        missing,
        root_path=tmp_path,
    )


def test_classify_file_rs_symlinks_direntry_and_surrogateescape(tmp_path: Path) -> None:
    """Verify symlink, DirEntry, directory, and non-UTF-8 filename/target parity in classify_file_rs."""
    rust_ext = _load_rust_ext()

    target = tmp_path / "target.py"
    target.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    target.chmod(target.stat().st_mode | stat.S_IXUSR)

    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()

    link_file = tmp_path / "link_to_target"
    link_file.symlink_to(target)
    link_dir = tmp_path / "link_to_dir"
    link_dir.symlink_to(sub_dir)
    dangling = tmp_path / "dangling.py"
    dangling.symlink_to(tmp_path / "gone.py")

    for p in (sub_dir, link_file, link_dir, dangling):
        for follow in (False, True):
            assert rust_ext.classify_file_rs(
                p,
                root_path=tmp_path,
                follow_symlinks=follow,
            ) == classifier.classify_file(
                p,
                root_path=tmp_path,
                follow_symlinks=follow,
            )

    with os.scandir(tmp_path) as it:
        for entry in it:
            ep = Path(entry.path)
            assert rust_ext.classify_file_rs(
                ep,
                root_path=tmp_path,
                entry=entry,
            ) == classifier.classify_file(
                ep,
                root_path=tmp_path,
                entry=entry,
            )

    if os.name == "posix":
        raw_dir = os.fsencode(tmp_path)
        bad_bytes = raw_dir + b"/surrogate_\xff.py"
        bad_path = Path(os.fsdecode(bad_bytes))
        try:
            bad_path.write_bytes(b"x = 1\n")
        except OSError:
            pytest.skip("Filesystem rejected non-UTF-8 filename")

        assert rust_ext.classify_file_rs(bad_path, root_path=tmp_path) == classifier.classify_file(
            bad_path,
            root_path=tmp_path,
        )

        bad_link = tmp_path / "bad_target_link.py"
        try:
            bad_link.symlink_to(os.fsdecode(b"undecodable_target_\xff.py"))
        except OSError:
            pytest.skip("Filesystem rejected non-UTF-8 symlink target")

        assert rust_ext.classify_file_rs(bad_link, root_path=tmp_path) == classifier.classify_file(
            bad_link,
            root_path=tmp_path,
        )
        batch_cfg = TraversalConfig(root_paths=(tmp_path,))
        assert list(core.find_files(batch_cfg)) == list(_fallback.find_files(batch_cfg))


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO/socket required")
def test_classify_file_rs_fifo_and_socket_never_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify FIFOs and Unix sockets never hang classify_file_rs or classify_batch_rs (#583)."""
    rust_ext = _load_rust_ext()

    fifo_path = tmp_path / "unwritten.pipe"
    os.mkfifo(fifo_path)
    rs_fifo = rust_ext.classify_file_rs(fifo_path, root_path=tmp_path)
    py_fifo = classifier.classify_file(fifo_path, root_path=tmp_path)
    assert rs_fifo == py_fifo
    assert rs_fifo.indicator == "|"
    assert rs_fifo.shebang is None
    assert "file" not in rs_fifo.tags

    sock_dir = tmp_path / "s"
    sock_dir.mkdir()
    monkeypatch.chdir(sock_dir)
    sock_path = sock_dir / "u.sock"
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        srv.bind("u.sock")
        rs_sock = rust_ext.classify_file_rs(sock_path, root_path=sock_dir)
        py_sock = classifier.classify_file(sock_path, root_path=sock_dir)
        assert rs_sock == py_sock
        assert rs_sock.indicator == "="
        assert rs_sock.permissions_str is not None
        assert rs_sock.permissions_str.startswith("s")
        assert "file" not in rs_sock.tags
    finally:
        srv.close()
        sock_path.unlink(missing_ok=True)
