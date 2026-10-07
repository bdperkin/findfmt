"""Sphinx configuration for findfmt documentation."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure package is importable for autodoc
sys.path.insert(0, str(Path("../..").resolve() / "src"))

project = "findfmt"
copyright = "Brandon Perkins"
author = "Brandon Perkins"
version = "0.1.0"
release = "0.1.0"

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
html_logo = "_static/logo.svg"
html_favicon = "_static/favicon.ico"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "source_repository": "https://github.com/bdperkin/findfmt",
    "source_branch": "main",
    "source_directory": "docs/source/",
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
]

# EPUB output
epub_show_urls = "footnote"
epub_exclude_files = ["_static/favicon.ico"]
suppress_warnings = ["epub.unknown_project_files"]

# LaTeX / PDF output
latex_elements: dict[str, str] = {
    "papersize": "letterpaper",
    "pointsize": "10pt",
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

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_ivar = True
