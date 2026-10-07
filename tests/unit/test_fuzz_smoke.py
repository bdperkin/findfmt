"""Smoke tests for ClusterFuzzLite fuzz targets ensuring valid harness execution."""

from __future__ import annotations

import pytest

from tests.fuzz import fuzz_classifier, fuzz_traversal


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"x",
        b"#!/bin/bash\necho 'hello'\n",
        b"#!/usr/bin/env python3\nprint('fuzz')\n",
        b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
        b"PK\x03\x04\x14\x00\x00\x00\x08\x00",
        b"\xff\xfe\x00\x00corrupt-unicode",
        b"some text content without extension",
    ],
)
def test_classifier_fuzz_smoke(payload: bytes) -> None:
    """Verify fuzz_classifier harness executes across various byte payloads."""
    fuzz_classifier.TestOneInput(payload)


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"abc",
        b"*.py\nbuild/\n!build/keep.txt\nsub/\n",
        b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t",
        b"long_filter_tag_name_that_exceeds_normal_lengths_abcdef1234567890",
    ],
)
def test_traversal_fuzz_smoke(payload: bytes) -> None:
    """Verify fuzz_traversal harness executes across various directory configurations."""
    fuzz_traversal.TestOneInput(payload)
