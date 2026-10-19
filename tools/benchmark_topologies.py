"""Synthetic directory tree and topology generators for findfmt benchmarks."""

from __future__ import annotations

import contextlib
import os
import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

DEFAULT_SEED = 42
MAX_DEEP_BRANCHES = 8
MAX_DEEP_LEVELS = 20

__all__ = [
    "DEFAULT_SEED",
    "MAX_DEEP_BRANCHES",
    "MAX_DEEP_LEVELS",
    "count_directories",
    "generate_synthetic_tree",
]


def count_directories(root: Path) -> int:
    """Count total subdirectories beneath root path."""
    return sum(len(dirs) for _, dirs, _ in os.walk(root))


def _setup_flat_topology(root: Path) -> list[Path]:
    """Configure flat topology with all files placed directly in root."""
    (root / ".gitignore").write_text("*.tmp\n*.log\n", encoding="utf-8")
    return [root]


def _setup_deep_topology(root: Path) -> list[Path]:
    """Configure deeply nested hierarchy with 20 levels of nesting and branching factor 2."""
    dirs: list[Path] = [root]
    curr_dirs = [root]
    for level in range(1, MAX_DEEP_LEVELS + 1):
        next_dirs: list[Path] = []
        for parent in curr_dirs:
            for b in (0, 1):
                d = parent / f"b{b}_lvl{level:02d}"
                dirs.append(d)
                next_dirs.append(d)

        if len(next_dirs) > MAX_DEEP_BRANCHES:
            half = MAX_DEEP_BRANCHES // 2
            next_dirs = next_dirs[:half] + next_dirs[-half:]

        curr_dirs = next_dirs

    (root / ".gitignore").write_text("*.tmp\n*.log\n", encoding="utf-8")
    return dirs


def _setup_real_world_topology(root: Path, target_files: int) -> list[Path]:
    """Configure realistic monorepo topology with massive ignored directories."""
    ignore_rules = "node_modules/\n.venv/\nbuild/\ndist/\n*.tmp\n*.log\n__pycache__/\n.cache/\n"
    (root / ".gitignore").write_text(ignore_rules, encoding="utf-8")

    ignored_subdirs = [
        root / "node_modules" / "pkg_a",
        root / "node_modules" / "pkg_b",
        root / ".venv" / "lib" / "python3.13" / "site-packages",
        root / "build" / "artifacts",
        root / "dist" / "bundle",
    ]
    for idir in ignored_subdirs:
        idir.mkdir(parents=True, exist_ok=True)
        dummy_count = min(max(20, target_files // 10), 200)
        for idx in range(dummy_count):
            (idir / f"dep_{idx:04d}.js").write_text("module.exports = {};\n", encoding="utf-8")

    dirs: list[Path] = [root]
    for pkg in ("packages/core", "packages/cli", "apps/web", "libs/utils"):
        pkg_root = root / pkg
        dirs.append(pkg_root)
        dirs.extend(pkg_root / sub for sub in ("src", "tests", "docs", "scripts"))

    return dirs


def _setup_standard_topology(root: Path) -> list[Path]:
    """Configure standard tiered topology with balanced package directories."""
    top_names = (
        "src",
        "lib",
        "pkg",
        "components",
        "utils",
        "tests",
        "docs",
        "scripts",
        "build",
        "node_modules",
    )
    sub_names = ("core", "api", "handlers", "models", "helpers")
    dirs: list[Path] = [root]
    dirs.extend(root / top for top in top_names)
    dirs.extend(root / top / sub for top in top_names for sub in sub_names)
    ignore_rules = "node_modules/\nbuild/\n*.tmp\n*.log\n.cache/\n"
    (root / ".gitignore").write_text(ignore_rules, encoding="utf-8")
    return dirs


def generate_synthetic_tree(
    root: Path,
    target_files: int,
    seed: int = DEFAULT_SEED,
    topology: str = "standard",
) -> tuple[int, int]:
    """Generate a reproducible, tiered synthetic directory tree."""
    root.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    extensions = [".py"] * 3 + [".sh", ".md", ".json", ".yaml", ".txt", ".tmp", ".log", ".bin"]
    templates: dict[str, Any] = {
        ".py": "def action() -> int:\n    return 42\n",
        ".sh": "#!/usr/bin/env bash\necho 42\n",
        ".md": "# Doc\nContent.\n",
        ".json": '{"id": 42}\n',
        ".yaml": "id: 42\n",
        ".bin": b"\x00\x01\x02\x03",
    }
    shebang = "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n"

    if topology == "flat":
        dirs = _setup_flat_topology(root)
    elif topology == "deep":
        dirs = _setup_deep_topology(root)
    elif topology == "real-world":
        dirs = _setup_real_world_topology(root, target_files)
    else:
        dirs = _setup_standard_topology(root)

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    files_created = 0
    for i in range(max(1, target_files)):
        target_dir = rng.choice(dirs)
        ext = rng.choice(extensions)
        fp = target_dir / f"item_{i:06d}{ext}"
        content = templates.get(ext, f"content {i}\n")
        if isinstance(content, bytes):
            fp.write_bytes(content)
        else:
            fp.write_text(content, encoding="utf-8")

        files_created += 1

    scripts_dir = root / "scripts"
    if scripts_dir.exists() or topology in ("standard", "real-world"):
        scripts_dir.mkdir(parents=True, exist_ok=True)
        for s_name in ("worker", "deploy"):
            sp = scripts_dir / s_name
            sp.write_text(shebang, encoding="utf-8")
            with contextlib.suppress(OSError):
                sp.chmod(0o755)

            files_created += 1

    return files_created, count_directories(root)
