"""Sphinx configuration for findfmt documentation."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Protocol, cast

# Ensure package is importable for autodoc
sys.path.insert(0, str(Path("../..").resolve() / "src"))

from findfmt import __version__

project = "findfmt"
copyright = "Brandon Perkins"
author = "Brandon Perkins"
version = __version__
release = __version__

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinxcontrib.typer",
]

source_suffix = {
    ".md": "markdown",
}

root_doc = "index"

# MyST parser configuration
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
]
myst_heading_anchors = 3

# HTML Theme Settings
html_theme = "furo"
html_title = "findfmt Documentation"
html_logo = "_static/icon.svg"
html_favicon = "_static/favicon.ico"
templates_path = ["_templates"]
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "source_repository": "https://github.com/bdperkin/findfmt",
    "source_branch": "main",
    "source_directory": "docs/source/",
}
SIDEBAR_NAVIGATION_MAXDEPTH = 4
html_context = {
    "languages": [
        ("en", "English", "🇬🇧"),
        ("de", "Deutsch", "🇩🇪"),
        ("es", "Español", "🇪🇸"),
        ("fr", "Français", "🇫🇷"),
        ("ja", "日本語", "🇯🇵"),
    ],
}

# Man page output
man_pages = [
    (
        "cli/index",
        "findfmt",
        "Content-aware file discovery and classification suite",
        ["Brandon Perkins"],
        1,
    ),
    (
        "cli/index",
        "findfiles",
        "Find all files and directories including hidden files respecting .gitignore",
        ["Brandon Perkins"],
        1,
    ),
    (
        "cli/index",
        "findfilemime",
        "Find files and list detected format and MIME tags",
        ["Brandon Perkins"],
        1,
    ),
    (
        "cli/index",
        "findfilefmt",
        "Find files by format tag, including hidden files",
        ["Brandon Perkins"],
        1,
    ),
    (
        "cli/index",
        "findshebang",
        "Find files by shebang interpreter pattern, including hidden files",
        ["Brandon Perkins"],
        1,
    ),
    (
        "cli/index",
        "findfmt0",
        "Find files and output NUL-delimited paths (--print0)",
        ["Brandon Perkins"],
        1,
    ),
    (
        "cli/index",
        "findsummary",
        "Find files and print summary statistics to stderr",
        ["Brandon Perkins"],
        1,
    ),
]

# EPUB output
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright
epub_show_urls = "footnote"
epub_use_index = True
epub_exclude_files = ["_static/favicon.ico"]
suppress_warnings = ["epub.unknown_project_files"]

# LaTeX / PDF output
latex_elements: dict[str, str] = {
    "papersize": "letterpaper",
    "pointsize": "10pt",
    "geometry": r"\usepackage[margin=1in]{geometry}",
    "preamble": r"""
\DeclareUnicodeCharacter{256D}{\mbox{+}}
\DeclareUnicodeCharacter{256E}{\mbox{+}}
\DeclareUnicodeCharacter{2570}{\mbox{+}}
\DeclareUnicodeCharacter{256F}{\mbox{+}}
""",
}
latex_documents = [
    (
        "index",
        "findfmt.tex",
        "findfmt Documentation",
        "Brandon Perkins",
        "manual",
    ),
]

# GNU Texinfo output
texinfo_documents = [
    (
        "index",
        "findfmt",
        "findfmt Documentation",
        author,
        "findfmt",
        "Content-aware file discovery and classification suite.",
        "Utilities",
    ),
]

# Help system output
htmlhelp_basename = "findfmtdoc"
qthelp_basename = "findfmt"
devhelp_basename = "findfmt"

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_ivar = True

# Linkcheck options
linkcheck_timeout = 15
linkcheck_retries = 3
linkcheck_workers = 5
linkcheck_anchors = True
linkcheck_ignore = [
    r"https://github\.com/.*/security/.*",
    r"https://github\.com/.*/advisories/.*",
    r"https://github\.com/.*/stargazers",  # GitHub returns 404 to unauthenticated clients
    r"https://github\.com/bdperkin/findfmt/pull/\d+",  # Skip dynamic PRs
]

# Gettext localization configuration
locale_dirs = ["locale/"]
gettext_compact = False
gettext_uuid = True


class _SphinxApp(Protocol):
    """Minimal Sphinx application protocol for event registration."""

    def connect(self, event: str, callback: object, priority: int = 500) -> int:
        """Connect a callback to a Sphinx build lifecycle event."""
        ...


class _TocTreeCallable(Protocol):
    """Protocol for Sphinx's HTML context toctree template helper."""

    def __call__(
        self,
        *,
        collapse: bool = False,
        titles_only: bool = False,
        maxdepth: int = -1,
        includehidden: bool = True,
    ) -> str | None:
        """Render the global Sphinx table of contents HTML fragment."""
        ...


class _FuroNavigationModule(Protocol):
    """Protocol for Furo's navigation tree post-processing module."""

    def get_navigation_tree(self, toctree_html: str) -> str:
        """Transform Sphinx toctree HTML into Furo's collapsible sidebar markup."""
        ...


def _configure_hierarchical_sidebar(
    app: object,
    pagename: str,
    templatename: str,
    context: dict[str, object],
    doctree: object,
) -> None:
    """Populate Furo's left sidebar navigation tree with nested page headings (#309)."""
    del app, pagename, templatename, doctree
    raw_toctree = context.get("toctree")
    if callable(raw_toctree):
        toctree_callable = cast("_TocTreeCallable", raw_toctree)
        furo_nav = cast("_FuroNavigationModule", importlib.import_module("furo.navigation"))
        toctree_html = toctree_callable(
            collapse=False,
            titles_only=False,
            maxdepth=SIDEBAR_NAVIGATION_MAXDEPTH,
            includehidden=True,
        )
        context["furo_navigation_tree"] = furo_nav.get_navigation_tree(str(toctree_html or ""))


def setup(app: _SphinxApp) -> dict[str, object]:
    """Register Sphinx HTML context hooks for hierarchical sidebar navigation (#309)."""
    app.connect("html-page-context", _configure_hierarchical_sidebar, priority=600)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": release,
    }
