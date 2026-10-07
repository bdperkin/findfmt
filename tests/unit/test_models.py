from pathlib import Path

from findfmt.models import FileInfo, TraversalConfig


def test_file_info_defaults():
    path = Path("sample.py")
    info = FileInfo(path=path, relative_path=path)
    assert info.path == path
    assert info.relative_path == path
    assert info.tags == frozenset()
    assert info.shebang is None
    assert info.mime_type is None
    assert not info.is_executable
    assert not info.is_symlink
    assert info.size_bytes == 0


def test_file_info_custom():
    path = Path("virtual_root/test.py")
    rel_path = Path("test.py")
    tags = frozenset(["python", "text"])
    info = FileInfo(
        path=path,
        relative_path=rel_path,
        tags=tags,
        shebang="#!/usr/bin/python3",
        mime_type="text/x-python",
        is_executable=True,
        is_symlink=False,
        size_bytes=128,
    )
    assert info.tags == tags
    assert info.shebang == "#!/usr/bin/python3"
    assert info.mime_type == "text/x-python"
    assert info.is_executable
    assert info.size_bytes == 128


def test_traversal_config_defaults():
    config = TraversalConfig()
    assert config.root_paths == (Path(),)
    assert config.include_tags == frozenset()
    assert config.exclude_tags == frozenset()
    assert not config.all_tags
    assert config.shebang_filter is None
    assert config.respect_gitignore
    assert not config.include_hidden
    assert not config.follow_symlinks
    assert config.relative_paths
    assert not config.null_delimited
    assert not config.show_tags
    assert not config.show_summary
    assert config.output_format == "text"


def test_file_info_to_dict():
    info = FileInfo(
        path=Path("/tmp/dir/test.sh"),
        relative_path=Path("test.sh"),
        tags=frozenset({"shell", "text"}),
        shebang="#!/bin/bash",
        mime_type="text/x-shellscript",
        is_executable=True,
        is_symlink=False,
        size_bytes=512,
    )
    d_rel = info.to_dict(absolute=False)
    assert d_rel["path"] == "test.sh"
    assert d_rel["relative_path"] == "test.sh"
    assert d_rel["tags"] == ["shell", "text"]
    assert d_rel["shebang"] == "#!/bin/bash"

    d_abs = info.to_dict(absolute=True)
    assert d_abs["path"] == "/tmp/dir/test.sh"
    assert d_abs["relative_path"] == "test.sh"
