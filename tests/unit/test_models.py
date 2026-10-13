from pathlib import Path

from findfmt.models import FileInfo, SortKey, TraversalConfig


def test_sort_key_enum() -> None:
    """Verify SortKey enum members and string values."""
    assert SortKey.NAME.value == "name"
    assert SortKey.VERSION.value == "version"
    assert SortKey.TIME.value == "time"
    assert SortKey.MTIME.value == "mtime"
    assert SortKey.CTIME.value == "ctime"
    assert SortKey.SIZE.value == "size"
    assert SortKey.NONE.value == "none"


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
    assert not config.relative_prefix
    assert not config.null_delimited
    assert not config.show_tags
    assert not config.show_summary
    assert config.output_format == "text"
    assert config.sort_by == SortKey.NAME
    assert not config.reverse_sort
    assert not config.dirs_first
    assert not config.files_first
    assert config.from_file is None
    assert not config.offline

    custom = TraversalConfig(
        relative_prefix=True,
        sort_by=SortKey.SIZE,
        reverse_sort=True,
        dirs_first=True,
        from_file="dump.txt",
        offline=True,
    )
    assert custom.relative_prefix
    assert custom.sort_by == SortKey.SIZE
    assert custom.reverse_sort
    assert custom.dirs_first
    assert not custom.files_first
    assert custom.from_file == "dump.txt"
    assert custom.offline


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
    assert "symlink_target" not in d_rel

    d_abs = info.to_dict(absolute=True)
    assert d_abs["path"] == str(info.path)
    assert d_abs["relative_path"] == "test.sh"

    # Test symlink_target present
    info_symlink = FileInfo(
        path=Path("/tmp/dir/link"),
        relative_path=Path("link"),
        is_symlink=True,
        symlink_target="/tmp/dir/target",
    )
    d_sym = info_symlink.to_dict()
    assert d_sym["is_symlink"] is True
    assert d_sym["symlink_target"] == "/tmp/dir/target"
