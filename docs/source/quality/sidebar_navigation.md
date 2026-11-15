# Sphinx & Furo Sidebar Navigation Architecture (ADR)

This document records the technical feasibility analysis and Architecture Decision Record (ADR) for
expandable hierarchical heading navigation in the Sphinx and Furo left sidebar (Issue
[#309](https://github.com/bdperkin/findfmt/issues/309), Epic
[#379](https://github.com/bdperkin/findfmt/issues/379)).

______________________________________________________________________

## 1. Context & Problem Statement

In standard Sphinx documentation built with the **Furo** theme, the left navigation drawer
(`.sidebar-tree`) displays only document-level titles, while in-page headings (`H2`, `H3`) appear
exclusively in the right-hand "On this page" table of contents (`.toc-tree`).

For multi-section reference documentation—such as **User Guides** (`guides/index.md`), **CLI
Reference** (`cli/index.md`), and **API Reference** (`api/findfmt.md`)—readers could not expand a
document entry in the left sidebar to jump directly to nested sections or module anchors without
first loading the target page.

______________________________________________________________________

## 2. Technical Feasibility Investigation

### 2.1. Sphinx `toctree` Resolution vs. Furo `titles_only` Default

Sphinx's `TocTree` adapter (`sphinx.environment.adapters.toctree._resolve_toctree`) supports two
modes when constructing the global navigation tree:

- **`titles_only=True`**: Emits only top-level document titles (`H1`), ignoring all in-page
  subsections regardless of `:maxdepth:` directives in MyST Markdown sources.
- **`titles_only=False`**: Includes nested document headings (`H2`, `H3`, `H4`) and Python autodoc
  object anchors up to the active `maxdepth` ceiling.

By default, Furo's `_compute_navigation_tree(context)` function in `furo/__init__.py` sets
`titles_only=True`:

```python
toctree_html = toctree(
    collapse=False,
    titles_only=True,
    maxdepth=-1,
    includehidden=True,
)
```

Because `titles_only=True` is passed directly to Sphinx's `toctree()` template callable, increasing
`:maxdepth:` in `docs/source/index.md` or section index files alone has no effect on Furo's left
sidebar.

### 2.2. Furo Navigation Tree Post-Processing (`get_navigation_tree`)

Furo transforms Sphinx's raw `toctree` HTML via `furo.navigation.get_navigation_tree(toctree_html)`.
Inspection of `furo.navigation` confirms that this post-processor is completely depth-agnostic:

1. It parses the `toctree` HTML fragment with `BeautifulSoup` and iterates recursively over every
   `<li>` element (`soup.find_all("li", recursive=True)`).
2. Whenever an `<li>` element contains a child `<ul>` (whether that `<ul>` represents child
   documents or nested in-page headings), Furo appends the `has-children` CSS class, injects an
   `<input type="checkbox" class="toctree-checkbox" role="switch" aria-label="Toggle navigation of ...">`,
   and inserts a `<label>` containing the `#svg-arrow-right` expand/collapse chevron icon.
3. Any `<li>` along the active document ancestry carrying the `current` class has its checkbox
   marked `checked=""` by default.
4. Furo's CSS rules (`.toctree-checkbox ~ ul { display: none; }` and
   `.toctree-checkbox:checked ~ ul { display: block; }`) operate on general sibling selectors and
   therefore support arbitrary nesting depths (`toctree-l1` through `toctree-l4`).

### 2.3. Evaluation of Implementation Alternatives

| Architecture Candidate                                              | Mechanism                                                                                                             | Accessibility & Mobile Drawer Behavior                                                         | Maintenance Overhead                                           | Verdict      |
| :------------------------------------------------------------------ | :-------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------- | :------------------------------------------------------------- | :----------- |
| **Option A: `:maxdepth:` Directive Audit Only**                     | Increase `:maxdepth:` in `index.md`, `guides/index.md`, `api/index.md`, and `quality/index.md`.                       | No change; Furo's default `titles_only=True` suppresses all in-page headings.                  | None, but fails to meet functional requirements.               | **Rejected** |
| **Option B: Client-Side DOM Mirroring (Custom JS)**                 | Inject custom JavaScript to clone `.toc-tree` headings into `.sidebar-tree` after page load.                          | Only populates headings for the currently loaded page; causes layout shift without JavaScript. | High; fragile across Furo DOM updates.                         | **Rejected** |
| **Option C: Document Splitting into Micro-Pages**                   | Split every `H2`/`H3` section in `cli/index.md` and `api/findfmt.md` into separate `.md` files.                       | Works with `titles_only=True`, but fragments single-page reading, man-page builds, and i18n.   | High; multiplies `.po` translation catalogs and cross-links.   | **Rejected** |
| **Option D: Sphinx `html-page-context` Hook + Template/CSS Polish** | Rebuild `furo_navigation_tree` with `titles_only=False` and `maxdepth=4` via `get_navigation_tree` at `priority=600`. | Preserves native CSS-only checkboxes, mobile drawer behavior, and `role="switch"` semantics.   | Low; uses public Sphinx events and standard Furo transformers. | **Selected** |

______________________________________________________________________

## 3. Architecture Decision & Implementation Details

- **Status:** Accepted (Milestone `v1.3.1`, Issue
  [#309](https://github.com/bdperkin/findfmt/issues/309)).
- **Selected Depth:** `SIDEBAR_NAVIGATION_MAXDEPTH = 4` (`:maxdepth: 4` across root and section
  toctrees).

### 3.1. Sphinx Event Hook (`docs/source/conf.py`)

`docs/source/conf.py` registers `_configure_hierarchical_sidebar` on Sphinx's `html-page-context`
event at `priority=600` (running immediately after Furo's built-in `_html_page_context` handler at
`priority=500`):

- Invokes `context["toctree"](collapse=False, titles_only=False, maxdepth=4, includehidden=True)`.
- Passes the resulting HTML fragment through `furo.navigation.get_navigation_tree()` so every page
  and heading level (`toctree-l1` through `toctree-l4`) receives native collapsible checkboxes and
  chevron labels:
  - **User Guides (`guides/index.md`):** Expands from guide titles (`Installation`, `Configuration`,
    etc.) into `H2` sections (`1. Installation Methods`, `2. Platform Notes`,
    `3. Verification & Diagnostics`) and `H3` subsections (`1.1. Standalone Execution with uvx`).
  - **CLI Reference (`cli/index.md`):** Expands directly into `1. Synopsis`, `2. Description`,
    `3. Options` (`3.1. Tag Filtering`, `3.2. Traversal Controls`, `3.3. Output Controls`,
    `3.4. Information & Diagnostics`), and `8. Examples`.
  - **API Reference (`api/findfmt.md`):** Expands `Package Modules` into module sections
    (`1. Core Data Models (findfmt.models)`, `2. File Classifier (findfmt.classifier)`, etc.) and
    individual class and function anchors (`FileInfo`, `TraversalConfig`, `classify_file()`).

### 3.2. Accessibility & Mobile Responsiveness (`navigation.html` & `custom.css`)

1. **Landmark Labeling:** `docs/source/_templates/sidebar/navigation.html` adds
   `aria-label="{{ _('Navigation') }}"` to `.sidebar-tree`.
2. **Keyboard Switch Focus:** Stock Furo styles `.toctree-checkbox` with `display: none`, which
   removes the `<input type="checkbox" role="switch">` elements from the keyboard tab order.
   `docs/source/_static/custom.css` overrides `.sidebar-tree .toctree-checkbox` to remain positioned
   over the toggle button with `opacity: 0` and adds a high-contrast `:focus-visible` outline on the
   sibling `<label>`, enabling keyboard users to tab through and toggle any nested heading branch
   with `Space`.
3. **Visual Hierarchy & Mobile Drawer:** Subtle left border guides on `.toctree-l2 > ul` and
   `.toctree-l3 > ul` visually distinguish nested heading levels in both desktop layouts and the
   slide-out mobile navigation drawer across light and dark Furo themes.
