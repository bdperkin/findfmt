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
    assert info.permissions_str is None
    assert info.owner_user is None
    assert info.owner_group is None
    assert info.inode is None
    assert info.device is None
    assert info.accumulated_size is None
    assert info.mtime is None
    assert info.ctime is None
    assert info.indicator is None


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
        permissions_str="-rwxr-xr-x",
        owner_user="alice",
        owner_group="developers",
        inode=123456,
        device=42,
        accumulated_size=1024,
        mtime=1700000000.0,
        ctime=1700000001.0,
        indicator="*",
    )
    assert info.tags == tags
    assert info.shebang == "#!/usr/bin/python3"
    assert info.mime_type == "text/x-python"
    assert info.is_executable
    assert info.size_bytes == 128
    assert info.permissions_str == "-rwxr-xr-x"
    assert info.owner_user == "alice"
    assert info.owner_group == "developers"
    assert info.inode == 123456
    assert info.device == 42
    assert info.accumulated_size == 1024
    assert info.mtime == 1700000000.0
    assert info.ctime == 1700000001.0
    assert info.indicator == "*"


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
    assert not config.show_permissions
    assert not config.show_user
    assert not config.show_group
    assert not config.show_inodes
    assert not config.show_device
    assert not config.show_size
    assert not config.human_readable
    assert not config.show_si
    assert not config.accumulate_size
    assert not config.show_mtime
    assert not config.show_ctime
    assert config.time_format is None
    assert not config.classify
    assert not config.hide_control_chars
    assert not config.literal
    assert not config.quote_name


def test_traversal_config_custom():
    custom = TraversalConfig(
        relative_prefix=True,
        sort_by=SortKey.SIZE,
        reverse_sort=True,
        dirs_first=True,
        from_file="dump.txt",
        offline=True,
        show_permissions=True,
        show_user=True,
        show_group=True,
        show_inodes=True,
        show_device=True,
        show_size=True,
        human_readable=True,
        show_si=True,
        accumulate_size=True,
        show_mtime=True,
        show_ctime=True,
        time_format="%Y-%m-%d",
        classify=True,
        hide_control_chars=True,
        literal=True,
        quote_name=True,
    )
    assert custom.relative_prefix
    assert custom.sort_by == SortKey.SIZE
    assert custom.reverse_sort
    assert custom.dirs_first
    assert not custom.files_first
    assert custom.from_file == "dump.txt"
    assert custom.offline
    assert custom.show_permissions
    assert custom.show_user
    assert custom.show_group
    assert custom.show_inodes
    assert custom.show_device
    assert custom.show_size
    assert custom.human_readable
    assert custom.show_si
    assert custom.accumulate_size
    assert custom.show_mtime
    assert custom.show_ctime
    assert custom.time_format == "%Y-%m-%d"
    assert custom.classify
    assert custom.hide_control_chars
    assert custom.literal
    assert custom.quote_name


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
    assert "permissions_str" not in d_rel
    assert "owner_user" not in d_rel
    assert "owner_group" not in d_rel
    assert "inode" not in d_rel
    assert "device" not in d_rel
    assert "accumulated_size" not in d_rel
    assert "mtime" not in d_rel
    assert "ctime" not in d_rel
    assert "indicator" not in d_rel

    d_abs = info.to_dict(absolute=True)
    assert d_abs["path"] == str(info.path)
    assert d_abs["relative_path"] == "test.sh"

    # Test symlink_target and metadata fields present
    info_meta = FileInfo(
        path=Path("/tmp/dir/link"),
        relative_path=Path("link"),
        is_symlink=True,
        symlink_target="/tmp/dir/target",
        permissions_str="lrwxrwxrwx",
        owner_user="alice",
        owner_group="developers",
        inode=99999,
        device=101,
        accumulated_size=2048,
        mtime=1700000000.0,
        ctime=1700000001.0,
        indicator="@",
    )
    d_meta = info_meta.to_dict()
    assert d_meta["is_symlink"] is True
    assert d_meta["symlink_target"] == "/tmp/dir/target"
    assert d_meta["permissions_str"] == "lrwxrwxrwx"
    assert d_meta["owner_user"] == "alice"
    assert d_meta["owner_group"] == "developers"
    assert d_meta["inode"] == 99999
    assert d_meta["device"] == 101
    assert d_meta["accumulated_size"] == 2048
    assert d_meta["mtime"] == 1700000000.0
    assert d_meta["ctime"] == 1700000001.0
    assert d_meta["indicator"] == "@"
