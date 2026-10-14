"""Unit tests for XML and HTML document formatters."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from findfmt.formatters import (
    HtmlFormatter,
    OutputFormat,
    XmlFormatter,
    get_formatter,
)
from findfmt.models import FileInfo


@pytest.fixture
def sample_files() -> list[FileInfo]:
    """Provide diverse sample FileInfo instances for formatting tests."""
    return [
        FileInfo(
            path=Path("/workspace/project/main.py"),
            relative_path=Path("main.py"),
            tags=frozenset({"python", "text"}),
            shebang="#!/usr/bin/env python3",
            mime_type="text/x-python",
            is_executable=True,
            is_symlink=False,
            size_bytes=1024,
            permissions_str="-rwxr-xr-x",
            owner_user="alice",
            owner_group="developers",
            inode=12345,
            device=6789,
            mtime=1700000000.0,
            ctime=1700000000.0,
            indicator="*",
        ),
        FileInfo(
            path=Path("/workspace/project/pkg/module.py"),
            relative_path=Path("pkg/module.py"),
            tags=frozenset({"python"}),
            shebang=None,
            mime_type="text/x-python",
            is_executable=False,
            is_symlink=False,
            size_bytes=2048,
        ),
        FileInfo(
            path=Path("/workspace/project/pkg/link.txt"),
            relative_path=Path("pkg/link.txt"),
            tags=frozenset({"text"}),
            shebang=None,
            mime_type="text/plain",
            is_executable=False,
            is_symlink=True,
            symlink_target="module.py",
            size_bytes=9,
        ),
    ]


# -----------------------------------------------------------------------------
# XML Formatter Tests
# -----------------------------------------------------------------------------


def test_xml_formatter_empty() -> None:
    """Verify XmlFormatter produces valid empty tree document."""
    fmt = XmlFormatter()
    out = fmt.format([])
    assert out.startswith("<?xml")
    assert "<tree" in out
    parsed = ET.fromstring(out)
    assert parsed.tag == "tree"
    assert len(parsed) == 0

    buf = io.StringIO()
    fmt.stream([], buf)
    assert buf.getvalue() == out


def test_xml_formatter_hierarchy(sample_files: list[FileInfo]) -> None:
    """Verify XmlFormatter builds nested directories, files, tags, and MIME elements."""
    fmt = XmlFormatter(absolute=False)
    out = fmt.format(sample_files)

    parsed = ET.fromstring(out)
    assert parsed.tag == "tree"

    # Root directory '.'
    root_dir = parsed.find("directory")
    assert root_dir is not None
    assert root_dir.attrib["name"] == "."

    # main.py file under root directory
    main_file = root_dir.find("file")
    assert main_file is not None
    assert main_file.attrib["name"] == "main.py"
    assert main_file.attrib["path"] == "main.py"
    assert main_file.attrib["size"] == "1024"
    assert main_file.attrib["executable"] == "true"
    assert main_file.attrib["symlink"] == "false"
    assert main_file.attrib["permissions"] == "-rwxr-xr-x"
    assert main_file.attrib["user"] == "alice"
    assert main_file.attrib["group"] == "developers"

    tags = [t.text for t in main_file.findall("tag")]
    assert tags == ["python", "text"]
    mime_node = main_file.find("mime")
    assert mime_node is not None
    assert mime_node.text == "text/x-python"
    shebang_node = main_file.find("shebang")
    assert shebang_node is not None
    assert shebang_node.text == "#!/usr/bin/env python3"

    # pkg subdirectory
    pkg_dir = root_dir.find("directory")
    assert pkg_dir is not None
    assert pkg_dir.attrib["name"] == "pkg"

    pkg_files = pkg_dir.findall("file")
    assert len(pkg_files) == 2
    symlink_file = next(f for f in pkg_files if f.attrib["name"] == "link.txt")
    assert symlink_file.attrib["symlink"] == "true"
    assert symlink_file.attrib["symlink_target"] == "module.py"


def test_xml_formatter_absolute(sample_files: list[FileInfo]) -> None:
    """Verify XmlFormatter handles absolute path hierarchies."""
    fmt = XmlFormatter(absolute=True)
    out = fmt.format(sample_files)

    parsed = ET.fromstring(out)
    root_dir = parsed.find("directory")
    assert root_dir is not None
    assert root_dir.attrib["name"] == "/"


def test_xml_formatter_no_indent(sample_files: list[FileInfo]) -> None:
    """Verify XmlFormatter suppresses indentation when no_indent=True."""
    fmt_pretty = XmlFormatter(no_indent=False)
    fmt_compact = XmlFormatter(no_indent=True)

    out_pretty = fmt_pretty.format(sample_files)
    out_compact = fmt_compact.format(sample_files)

    assert "  <directory" in out_pretty
    assert "  <directory" not in out_compact


def test_xml_formatter_sizes_and_du(sample_files: list[FileInfo]) -> None:
    """Verify XmlFormatter human-readable size formatting and accumulated sizes."""
    fmt = XmlFormatter(human_readable=True, accumulate_size=True)
    out = fmt.format(sample_files)

    parsed = ET.fromstring(out)
    root_dir = parsed.find("directory")
    assert root_dir is not None
    assert "accumulated_size" in root_dir.attrib


def test_xml_formatter_directory_file_info() -> None:
    """Verify XmlFormatter populates directory metadata when FileInfo represents a dir."""
    dir_info = FileInfo(
        path=Path("/workspace/project/pkg"),
        relative_path=Path("pkg"),
        tags=frozenset({"directory"}),
        permissions_str="drwxr-xr-x",
        owner_user="root",
        owner_group="root",
        indicator="/",
    )
    fmt = XmlFormatter()
    out = fmt.format([dir_info])
    parsed = ET.fromstring(out)
    root_dir = parsed.find("directory")
    assert root_dir is not None
    pkg_dir = root_dir.find("directory")
    assert pkg_dir is not None
    assert pkg_dir.attrib["name"] == "pkg"
    assert pkg_dir.attrib["permissions"] == "drwxr-xr-x"
    assert pkg_dir.attrib["user"] == "root"
    assert pkg_dir.attrib["indicator"] == "/"


def test_xml_formatter_special_characters() -> None:
    """Verify XmlFormatter safely escapes XML special characters."""
    file_info = FileInfo(
        path=Path("/workspace/project/<test>&'\" file.txt"),
        relative_path=Path("<test>&'\" file.txt"),
        tags=frozenset({"tag<1>", "tag&2"}),
        mime_type="text/plain",
    )
    fmt = XmlFormatter()
    out = fmt.format([file_info])
    assert 'name="&lt;test&gt;&amp;\'&quot; file.txt"' in out
    parsed = ET.fromstring(out)
    assert parsed.tag == "tree"


# -----------------------------------------------------------------------------
# HTML Formatter Tests
# -----------------------------------------------------------------------------


def test_html_formatter_empty() -> None:
    """Verify HtmlFormatter produces valid HTML5 page for empty results."""
    fmt = HtmlFormatter()
    out = fmt.format([])
    assert "<!DOCTYPE html>" in out
    assert "<title>Directory Tree</title>" in out
    assert "<h1>Directory Tree</h1>" in out
    assert '<pre class="tree"><code></code></pre>' in out

    buf = io.StringIO()
    fmt.stream([], buf)
    assert buf.getvalue() == out


def test_html_formatter_hyperlinks_and_base_href(sample_files: list[FileInfo]) -> None:
    """Verify HtmlFormatter constructs clickable hyperlinks with base HREF prefix."""
    fmt = HtmlFormatter(base_href="http://localhost:8000")
    out = fmt.format(sample_files)

    assert '<a href="http://localhost:8000" class="dir">.</a>' in out
    assert '<a href="http://localhost:8000/main.py" class="file">main.py</a>' in out
    assert '<a href="http://localhost:8000/pkg/module.py" class="file">module.py</a>' in out
    assert '<a href="http://localhost:8000/pkg/link.txt" class="symlink">link.txt</a>' in out


def test_html_formatter_base_href_trailing_slash(sample_files: list[FileInfo]) -> None:
    """Verify HtmlFormatter handles base HREF with trailing slash cleanly."""
    fmt = HtmlFormatter(base_href="http://localhost:8000/")
    out = fmt.format(sample_files)

    assert "http://localhost:8000/main.py" in out
    assert "http://localhost:8000//main.py" not in out


def test_html_formatter_no_links(sample_files: list[FileInfo]) -> None:
    """Verify HtmlFormatter suppresses hyperlinks when no_links=True."""
    fmt = HtmlFormatter(no_links=True)
    out = fmt.format(sample_files)

    assert "<a href=" not in out
    assert '<span class="dir">.</span>' in out
    assert '<span class="file">main.py</span>' in out
    assert '<span class="symlink">link.txt</span>' in out


def test_html_formatter_title_customization(sample_files: list[FileInfo]) -> None:
    """Verify HtmlFormatter customizes document title and heading."""
    fmt = HtmlFormatter(title="Custom Project Files")
    out = fmt.format(sample_files)

    assert "<title>Custom Project Files</title>" in out
    assert "<h1>Custom Project Files</h1>" in out


def test_html_formatter_intro_outro_templates(
    sample_files: list[FileInfo],
    tmp_path: Path,
) -> None:
    """Verify HtmlFormatter reads and injects intro/outro template fragments."""
    intro_file = tmp_path / "intro.html"
    intro_file.write_text("<div class='custom-intro'>Header Info</div>\n", encoding="utf-8")
    outro_file = tmp_path / "outro.html"
    outro_file.write_text("<div class='custom-outro'>Footer Copyright</div>\n", encoding="utf-8")

    fmt = HtmlFormatter(intro_file=intro_file, outro_file=outro_file)
    out = fmt.format(sample_files)

    assert "<div class='custom-intro'>Header Info</div>" in out
    assert "<div class='custom-outro'>Footer Copyright</div>" in out
    # Verify intro precedes tree listing and outro follows tree listing
    intro_idx = out.index("custom-intro")
    tree_idx = out.index('<pre class="tree">')
    outro_idx = out.index("custom-outro")
    assert intro_idx < tree_idx < outro_idx


def test_html_formatter_intro_outro_direct_strings(sample_files: list[FileInfo]) -> None:
    """Verify HtmlFormatter accepts intro and outro directly as strings."""
    fmt = HtmlFormatter(intro="<!-- intro -->", outro="<!-- outro -->")
    out = fmt.format(sample_files)
    assert "<!-- intro -->" in out
    assert "<!-- outro -->" in out


def test_html_formatter_special_characters_url_encoding() -> None:
    """Verify HtmlFormatter URL-encodes special path characters and escapes text."""
    file_info = FileInfo(
        path=Path("/workspace/project/my folder/report & data.html"),
        relative_path=Path("my folder/report & data.html"),
        tags=frozenset({"html"}),
    )
    fmt = HtmlFormatter(base_href="https://example.com/repo")
    out = fmt.format([file_info])

    assert "https://example.com/repo/my%20folder/report%20%26%20data.html" in out
    assert "report &amp; data.html" in out


def test_html_formatter_metadata_badges_sizes(sample_files: list[FileInfo]) -> None:
    """Verify HtmlFormatter renders metadata, sizes, badges, and mime types."""
    fmt = HtmlFormatter(
        show_permissions=True,
        show_user=True,
        show_group=True,
        show_size=True,
        human_readable=True,
        accumulate_size=True,
        classify=True,
    )
    out = fmt.format(sample_files)

    assert '<span class="meta">[' in out
    assert '<span class="size">' in out
    assert '<span class="badge badge-python">python</span>' in out
    assert '<span class="mime">text/x-python</span>' in out


def test_html_formatter_no_indent(sample_files: list[FileInfo]) -> None:
    """Verify HtmlFormatter omits tree guide lines when no_indent=True."""
    fmt_guides = HtmlFormatter(no_indent=False)
    fmt_no_guides = HtmlFormatter(no_indent=True)

    out_guides = fmt_guides.format(sample_files)
    out_no_guides = fmt_no_guides.format(sample_files)

    assert "├── " in out_guides or "└── " in out_guides
    assert "├── " not in out_no_guides
    assert "└── " not in out_no_guides


def test_html_formatter_absolute(sample_files: list[FileInfo]) -> None:
    """Verify HtmlFormatter handles absolute root paths."""
    fmt = HtmlFormatter(absolute=True)
    out = fmt.format(sample_files)
    assert 'class="dir">/</a>' in out


def test_get_formatter_options_forwarding() -> None:
    """Verify get_formatter passes document-specific options to HtmlFormatter and XmlFormatter."""
    xml_fmt = get_formatter(
        OutputFormat.XML,
        no_indent=True,
        show_permissions=True,
    )
    assert isinstance(xml_fmt, XmlFormatter)
    assert xml_fmt.no_indent is True
    assert xml_fmt.show_permissions is True

    html_fmt = get_formatter(
        OutputFormat.HTML,
        base_href="http://example.com",
        title="Custom Title",
        no_links=True,
    )
    assert isinstance(html_fmt, HtmlFormatter)
    assert html_fmt.base_href == "http://example.com"
    assert html_fmt.title == "Custom Title"
    assert html_fmt.no_links is True


def test_duplicate_directory_entries() -> None:
    """Verify duplicate directory entries update existing tree node."""
    dir_info = FileInfo(
        path=Path("/workspace/project/subdir"),
        relative_path=Path("subdir"),
        tags=frozenset({"directory"}),
        mime_type=None,
        size_bytes=4096,
        indicator="/",
    )
    xml_out = XmlFormatter().format([dir_info, dir_info])
    assert '<directory name="subdir"' in xml_out

    html_out = HtmlFormatter().format([dir_info, dir_info])
    assert 'class="dir">subdir</a>' in html_out


def test_html_formatter_empty_tags_with_mime() -> None:
    """Verify HTML entry rendering when tags is empty and mime type is present."""
    child = FileInfo(
        path=Path("/workspace/project/plain.txt"),
        relative_path=Path("plain.txt"),
        tags=frozenset(),
        mime_type="text/plain",
        size_bytes=100,
        indicator="",
    )
    html_out = HtmlFormatter().format([child])
    assert '<span class="mime">text/plain</span>' in html_out
    assert '<span class="badge' not in html_out
