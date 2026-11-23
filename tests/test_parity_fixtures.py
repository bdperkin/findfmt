"""Filesystem scenario builders for findfmt Rust-vs-Python parity tests (#584)."""

from __future__ import annotations

import contextlib
import os
import socket
import stat
import sys
from pathlib import Path


def _make_executable(path: Path) -> None:
    """Add owner/group/other execute bits on POSIX platforms."""
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def build_gitignore_and_exclude_tree(tmp_path: Path) -> tuple[Path, Path]:
    """Build a repository exercising empty dirs, nested gitignore negations, spaces, and excludes."""
    xdg_ignore = tmp_path / "git" / "ignore"
    xdg_ignore.parent.mkdir(parents=True, exist_ok=True)
    xdg_ignore.write_text("*.globalign\n", encoding="utf-8")

    repo = tmp_path / "ignore_repo"
    (repo / ".git" / "info").mkdir(parents=True)
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (repo / ".git" / "info" / "exclude").write_text("*.gitexcl\n!keep.gitexcl\n", encoding="utf-8")

    (repo / "empty_top").mkdir()
    (repo / "sub" / "empty_nested").mkdir(parents=True)
    (repo / "sub" / "only_ignored").mkdir(parents=True)
    (repo / "sub" / "only_ignored" / "drop.log").write_text("ignored\n", encoding="utf-8")
    (repo / "ignored_dir").mkdir()
    (repo / "ignored_dir" / "inside.py").write_text("x = 0\n", encoding="utf-8")

    gitignore_lines = [
        "# Root comment",
        r"\#literal_hash.txt",
        "*.log",
        "!root_keep.log",
        "/anchored.cfg",
        r"\ leading.py",
        r"spaced\ file.md",
        "ignored_dir/",
    ]
    if sys.platform != "win32":
        gitignore_lines.append(r"trailing\ ")
        (repo / "trailing ").write_text("ignored trailing\n", encoding="utf-8")
        (repo / "trailing").write_text("kept no trailing space\n", encoding="utf-8")

    (repo / ".gitignore").write_text("\n".join(gitignore_lines) + "\n", encoding="utf-8")
    (repo / "#literal_hash.txt").write_text("hash\n", encoding="utf-8")
    (repo / "drop.log").write_text("log\n", encoding="utf-8")
    (repo / "root_keep.log").write_text("kept\n", encoding="utf-8")
    (repo / "anchored.cfg").write_text("root anchored\n", encoding="utf-8")
    (repo / "sub" / "anchored.cfg").write_text("nested kept\n", encoding="utf-8")
    (repo / " leading.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "leading.py").write_text("x = 2\n", encoding="utf-8")
    (repo / "spaced file.md").write_text("# ignored\n", encoding="utf-8")
    (repo / "kept file.md").write_text("# kept\n", encoding="utf-8")
    (repo / "skip.gitexcl").write_text("excl\n", encoding="utf-8")
    (repo / "keep.gitexcl").write_text("kept excl\n", encoding="utf-8")
    (repo / "skip.globalign").write_text("global\n", encoding="utf-8")
    (repo / "SkipCase.TXT").write_text("upper\n", encoding="utf-8")

    (repo / "sub" / ".gitignore").write_text("!nested_keep.log\n*.localtmp\n", encoding="utf-8")
    (repo / "sub" / "nested_keep.log").write_text("override\n", encoding="utf-8")
    (repo / "sub" / "nested_drop.log").write_text("still ignored\n", encoding="utf-8")
    (repo / "sub" / "scratch.localtmp").write_text("tmp\n", encoding="utf-8")

    (repo / ".dotdir").mkdir()
    (repo / ".dotdir" / "secret.yaml").write_text("k: v\n", encoding="utf-8")
    (repo / ".dotfile.toml").write_text("a = 1\n", encoding="utf-8")

    custom_ignore = tmp_path / "custom.gitignore"
    custom_ignore.write_text("*.md\n!kept\\ file.md\n", encoding="utf-8")
    (repo / "extra.customign").write_text("c\n", encoding="utf-8")
    return repo, custom_ignore


def build_symlink_and_boundary_tree(tmp_path: Path) -> tuple[Path, bool]:
    """Build a directory tree with symlink loops, broken links, depth tiers, and filelimit dirs."""
    root = tmp_path / "bounds_repo"
    deep = root / "d1" / "d2" / "d3"
    deep.mkdir(parents=True)
    (root / "top.py").write_text("top = 1\n", encoding="utf-8")
    (root / "d1" / "lvl1.py").write_text("l1 = 1\n", encoding="utf-8")
    (root / "d1" / "d2" / "lvl2.rs").write_text("pub fn f() {}\n", encoding="utf-8")
    (deep / "lvl3.py").write_text("l3 = 1\n", encoding="utf-8")

    crowded = root / "crowded"
    crowded.mkdir()
    for idx in range(5):
        (crowded / f"item_{idx}.txt").write_text(f"payload {idx}\n", encoding="utf-8")

    sparse = root / "sparse"
    sparse.mkdir()
    sh_script = sparse / "run_tool"
    sh_script.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    _make_executable(sh_script)
    (sparse / "readme.md").write_text("# sparse\n", encoding="utf-8")

    cycle_a = root / "cycle_a"
    cycle_b = root / "cycle_b"
    links = root / "links"
    empty_cycle = root / "empty_cycle"
    for d in (cycle_a, cycle_b, links, empty_cycle):
        d.mkdir()

    (cycle_a / "alpha.py").write_text("a = 1\n", encoding="utf-8")
    (cycle_b / "beta.rs").write_text("fn b() {}\n", encoding="utf-8")

    symlinks_ok = True
    try:
        (cycle_a / "to_b").symlink_to(cycle_b, target_is_directory=True)
        (cycle_b / "to_a").symlink_to(cycle_a, target_is_directory=True)
        (cycle_a / "self_loop").symlink_to(cycle_a / "self_loop")
        (links / "broken.py").symlink_to(root / "missing_target.py")
        (links / "valid_script").symlink_to(sh_script)
        (empty_cycle / "loop_root").symlink_to(empty_cycle, target_is_directory=True)
    except OSError:
        symlinks_ok = False

    return root, symlinks_ok


def build_sorting_tree(tmp_path: Path) -> Path:
    """Build a tree with varied sizes, mtimes, cases, and Unicode-digit natural version names."""
    root = tmp_path / "sort_repo"
    for sub_name in ("AlphaDir", "betaDir", "v2_dir", "v10_dir"):
        sub = root / sub_name
        sub.mkdir(parents=True)
        (sub / "child.py").write_text(f"# {sub_name}\n", encoding="utf-8")

    specs: list[tuple[str, bytes, int]] = [
        ("empty_0.txt", b"", 1_700_000_300),
        ("tie_b.py", b"x = 12345678901234\n", 1_700_000_200),
        ("tie_a.py", b"y = 12345678901234\n", 1_700_000_200),
        ("CaseUpper.md", b"a" * 128, 1_700_000_150),
        ("caselower.md", b"b" * 512, 1_700_000_100),
        ("item2.py", b"v = 2\n", 1_700_000_210),
        ("item10.py", b"v = 10\n", 1_700_000_220),
        ("item02.py", b"v = 02\n", 1_700_000_230),
        ("uni_\u0662.txt", b"arabic 2\n", 1_700_000_240),
        ("uni_\u0661\u0660.txt", b"arabic 10\n", 1_700_000_250),
        ("uni_\uff12.txt", b"fullwidth 2\n", 1_700_000_260),
        ("uni_\u0968.txt", b"devanagari 2\n", 1_700_000_270),
    ]
    for name, payload, ts in specs:
        fp = root / name
        fp.write_bytes(payload)
        os.utime(fp, (ts, ts))

    return root


def _add_posix_special_and_non_utf8(root: Path, probe_paths: list[Path], cwd_save: Path) -> None:
    """Populate POSIX-only control chars, non-UTF-8 surrogateescape names, FIFO, and socket."""
    for ctrl_name in ("ctrl_\x07_bell.txt", "ctrl_\x1b_esc.py", "data:,hello"):
        with contextlib.suppress(OSError):
            cp = root / ctrl_name
            cp.write_text("ctrl\n", encoding="utf-8")
            probe_paths.append(cp)

    raw_root = os.fsencode(root)
    bad_file = Path(os.fsdecode(raw_root + b"/surrogate_\xff_\xfe.py"))
    bad_dir = Path(os.fsdecode(raw_root + b"/dir_\x80"))
    bad_nested = Path(os.fsdecode(raw_root + b"/dir_\x80/mod_\xff.rs"))
    bad_link = root / "surrogate_target_link.py"
    with contextlib.suppress(OSError):
        bad_file.write_bytes(b"#!/usr/bin/env python3\nx = 1\n")
        _make_executable(bad_file)
        bad_dir.mkdir()
        bad_nested.write_bytes(b"pub fn ok() {}\n")
        bad_link.symlink_to(os.fsdecode(b"missing_\xff.py"))
        probe_paths.extend([bad_file, bad_nested, bad_link])

    if hasattr(os, "mkfifo"):
        fifo = root / "named.pipe"
        os.mkfifo(fifo)
        probe_paths.append(fifo)
        sock_sub = root / "sk"
        sock_sub.mkdir()
        os.chdir(sock_sub)
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as srv:
                srv.bind("p.sock")
                probe_paths.append(sock_sub / "p.sock")
        finally:
            os.chdir(cwd_save)


def build_classification_and_encoding_tree(tmp_path: Path) -> tuple[Path, list[Path]]:
    """Build diverse magic-byte, shebang, Unicode bidi, and POSIX non-UTF-8/FIFO fixtures."""
    root = tmp_path / "cls_repo"
    root.mkdir()
    probe_paths: list[Path] = []

    payloads: list[tuple[str, bytes, bool]] = [
        ("img_extless", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", False),
        ("elf_extless", b"\x7fELF\x02\x01\x01\x00\x00\x00", True),
        ("doc.pdf", b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n\x00", False),
        ("archive.tgz", b"\x1f\x8b\x08\x00\x00\x00\x00\x00", False),
        ("xml.plist", b'<?xml version="1.0"?><plist version="1.0"></plist>\n', False),
        ("bin.plist", b"bplist00\x00\x01\x02\x03", False),
        ("nul_at_1023", (b"x" * 1023) + b"\x00", False),
        ("nul_at_1024", (b"x" * 1024) + b"\x00tail", False),
        ("empty_file", b"", False),
        ("Dockerfile.stage", b"FROM scratch\n", False),
        ("Makefile", b"all:\n\t@true\n", False),
        (".bashrc", b"export EDITOR=vim\n", False),
        ("sb_env_py", b"#!/usr/bin/env python3\nprint(1)\n", True),
        ("sb_env_s", b"#!/usr/bin/env -S python3 -u -B\nprint(2)\n", True),
        ("sb_quoted", b'#!"/opt/spaced dir/bin/ruby" -w\nputs 1\n', True),
        ("sb_unclosed", b"#!/bin/sh 'unclosed_quote\necho hi\n", True),
        ("sb_bad_utf8", b"#!/usr/bin/python3 \xff\nprint(3)\n", True),
        ("sb_ctrl", b"#!/usr/bin/python3 \x01\nprint(4)\n", True),
        ("sb_nonexec", b"#!/usr/bin/env node\nconsole.log(1)\n", False),
        ("sb_nix", b"#! /usr/bin/env nix-shell\n#! nix-shell -i bash -p bash\necho nix\n", True),
        ("bidi_\u202eevil\u202c.py", b"x = 1\n", False),
        ("rlm_\u200fnote.txt", b"rtl mark\n", False),
        ("zwsp_\u200bscript.sh", b"#!/bin/sh\necho zwsp\n", True),
        ("cjk_日本語.md", b"# Heading\n", False),
    ]
    for name, data, is_exec in payloads:
        fp = root / name
        fp.write_bytes(data)
        if is_exec:
            _make_executable(fp)

        probe_paths.append(fp)

    if os.name == "posix":
        _add_posix_special_and_non_utf8(root, probe_paths, Path.cwd())

    return root, probe_paths
