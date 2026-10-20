"""Unit tests for tag skipping and candidate file filtering."""

from __future__ import annotations

from findfmt.models import TraversalConfig
from findfmt.traversal.tags import can_skip_file_by_tags


def test_can_skip_file_by_tags() -> None:
    """Verify early candidate file rejection based on file tags and executable state."""
    # No filters
    assert not can_skip_file_by_tags("file.txt", TraversalConfig())

    # Exclude tags matched vs not matched
    cfg_ex = TraversalConfig(exclude_tags=frozenset({"python"}))
    assert can_skip_file_by_tags("script.py", cfg_ex) is True
    assert can_skip_file_by_tags("readme.md", cfg_ex) is False

    # Generic tags bypass skipping
    cfg_gen = TraversalConfig(include_tags=frozenset({"file"}))
    assert not can_skip_file_by_tags("anything.bin", cfg_gen)

    # Include tag matches filename tag
    cfg_py = TraversalConfig(include_tags=frozenset({"python"}))
    assert not can_skip_file_by_tags("module.py", cfg_py)
    # Non-interpreter tag can skip photo.jpg even without is_executable
    cfg_c = TraversalConfig(include_tags=frozenset({"c"}))
    assert can_skip_file_by_tags("photo.jpg", cfg_c) is True
    # Interpreter tag with is_executable=False can skip photo.jpg
    assert can_skip_file_by_tags("photo.jpg", cfg_py, is_executable=False) is True

    # Include tag matches MIME type
    cfg_mime = TraversalConfig(include_tags=frozenset({"image"}))
    assert not can_skip_file_by_tags("photo.jpg", cfg_mime)
    cfg_full_mime = TraversalConfig(include_tags=frozenset({"mime:image/jpeg"}))
    assert not can_skip_file_by_tags("photo.jpg", cfg_full_mime)

    # Interpreter tags when executable is True vs False
    cfg_sh = TraversalConfig(include_tags=frozenset({"bash"}))
    assert not can_skip_file_by_tags("tool", cfg_sh, is_executable=True)
    assert not can_skip_file_by_tags("tool", cfg_sh, is_executable=None)
    assert can_skip_file_by_tags("tool", cfg_sh, is_executable=False) is True

    # all_tags mode: cannot match vs matches
    cfg_all_miss = TraversalConfig(include_tags=frozenset({"python", "c"}), all_tags=True)
    assert can_skip_file_by_tags("test.py", cfg_all_miss) is True
    assert (
        can_skip_file_by_tags(
            "test.py",
            TraversalConfig(include_tags=frozenset({"python", "ruby"}), all_tags=True),
            is_executable=False,
        )
        is True
    )
    cfg_all_match = TraversalConfig(include_tags=frozenset({"python"}), all_tags=True)
    assert not can_skip_file_by_tags("test.py", cfg_all_match)
