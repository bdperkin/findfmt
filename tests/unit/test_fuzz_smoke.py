"""Smoke tests for ClusterFuzzLite and cargo-fuzz targets ensuring valid harness execution (#585)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from tests.fuzz import fuzz_classifier, fuzz_traversal

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"x",
        b"#!/bin/bash\necho 'hello'\n",
        b"#!/usr/bin/env -S python3 -u\nprint('fuzz')\n",
        b"#! /usr/bin/env nix-shell\n#! nix-shell -i bash -p bash\necho ok\n",
        b"#!/bin/sh 'unclosed_quote\n",
        b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
        b"PK\x03\x04\x14\x00\x00\x00\x08\x00",
        b"\xff\xfe\x00\x00corrupt-unicode",
        b"\x03#!/usr/bin/env python3\nx = 1\n",
        b"some text content without extension",
    ],
)
def test_classifier_fuzz_smoke(payload: bytes) -> None:
    """Verify differential fuzz_classifier harness executes across diverse byte payloads."""
    fuzz_classifier.TestOneInput(payload)


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"abc",
        b"*.py\nbuild/\n!build/keep.txt\nsub/\n",
        b"[z-a]\nescaped\\ \n  leading.py\n#!/usr/bin/env python3\n",
        b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t",
        b"long_filter_tag_name_that_exceeds_normal_lengths_abcdef1234567890",
    ],
)
def test_traversal_fuzz_smoke(payload: bytes) -> None:
    """Verify differential fuzz_traversal harness executes across diverse directory configurations."""
    fuzz_traversal.TestOneInput(payload)


def test_cargo_fuzz_manifest_and_seed_corpus_integrity() -> None:
    """Verify findfmt_rs/fuzz cargo-fuzz manifest, targets, and seed corpus files are consistent."""
    fuzz_dir = _REPO_ROOT / "findfmt_rs" / "fuzz"
    manifest_path = fuzz_dir / "Cargo.toml"
    assert manifest_path.is_file()

    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["package"]["metadata"]["cargo-fuzz"] is True

    bins = manifest["bin"]
    expected_names = {"fuzz_shebang_header", "fuzz_classifier_tags", "fuzz_sort_gitignore"}
    assert {entry["name"] for entry in bins} == expected_names
    for entry in bins:
        target_file = fuzz_dir / entry["path"]
        assert target_file.is_file(), f"Missing cargo-fuzz target source: {target_file}"

    seed_files = sorted((fuzz_dir / "seed_corpus").glob("*.txt"))
    assert len(seed_files) >= 3
    for seed_file in seed_files:
        raw = seed_file.read_bytes()
        fuzz_classifier.TestOneInput(raw)
        fuzz_traversal.TestOneInput(raw)
