# Accessibility Statement

`findfmt` is committed to providing an accessible, inclusive experience for all users and contributors,
regardless of ability or assistive technology.

We strive to align our command-line tools, documentation, and community workflows with the
[Web Content Accessibility Guidelines (WCAG) 2.1 Level AA](https://www.w3.org/WAI/standards-guidelines/wcag/)
standards wherever applicable.

______________________________________________________________________

## 1. Supported Environments & Assistive Technologies

### 1.1. Command-Line Interface (CLI)

The `findfmt` CLI is designed from the ground up for compatibility with terminal screen readers and assistive
tooling:

- **Screen Reader Compatibility**: Verified for predictable speech output on standard terminal emulators
  across Linux ([Orca](https://help.gnome.org/orca/)), macOS
  ([VoiceOver](https://www.apple.com/accessibility/features/?vision)), and Windows
  ([NVDA](https://www.nvaccess.org/) and [JAWS](https://vispero.com/jaws-screen-reader-software/)).
- **Stream-Oriented Plain Text**: CLI output emits linear, deterministic text streams to `stdout` and error
  diagnostics to `stderr` without ANSI escape codes, cursor jumps, or animated spinners in standard execution
  modes.
- **Machine-Readable Delimiters**: Supports `-0` / `--print0` NUL-separated streaming for unambiguous parsing
  and programmatic integration with `xargs -0` and automated scripts.
- **Color Independence, `NO_COLOR`, `FORCE_COLOR`, & `TERM=dumb` Support**: No critical information is
  communicated exclusively through color. `findfmt` honors explicit `--color` / `--no-color` flags first,
  followed by [`NO_COLOR`](https://no-color.org/) (disabling ANSI styles whenever `NO_COLOR` is non-empty),
  `FORCE_COLOR` / `CLICOLOR_FORCE`, `CLICOLOR=0`, and `TERM=dumb` / `TERM=unknown`, and disables ANSI styling
  by default whenever output is redirected to a non-TTY pipe or file unless enabled by a higher-precedence
  setting such as `--color` or `FORCE_COLOR=1` (`src/findfmt/cli/terminal.py`). Behavior is identical across
  both the native Rust extension (`findfmt._rust_ext`) and pure-Python fallback (`findfmt._fallback`).
- **Localized, Sanitized Diagnostics Across Rust & Python**: Traversal I/O warnings and CLI diagnostics coming
  from either `findfmt._rust_ext` or `findfmt._fallback` are formatted through
  `src/findfmt/cli/diagnostics.py`, translated via GNU `gettext` (`findfmt.i18n`), and stripped of ANSI escape
  codes, C0/C1 control characters, Unicode bidirectional (`BiDi`) overrides, and invalid UTF-8 surrogates
  before reaching `stdout` or `stderr`.

### 1.2. Project Documentation & Web Systems

Our web documentation (hosted via Sphinx and GitHub Pages) is configured to adhere to WCAG 2.1 Level AA
standards:

- **Semantic Markup**: Uses structured HTML landmarks (`<nav>`, `<main>`, `<article>`, `<aside>`, `<header>`,
  `<footer>`) to facilitate smooth screen reader orientation.
- **Clear Heading Hierarchy**: Maintains sequential heading levels (`H1` through `H6`) to ensure reliable
  section jumping.
- **Contrast Ratios**: Ensures text-to-background contrast ratios exceed the 4.5:1 minimum threshold for
  normal body text and 3:1 for large headings.
- **Keyboard Navigation**: All interactive elements (search modals, navigation sidebars, code-copy buttons)
  are fully operable via keyboard focus indicators without mouse interaction.
- **Descriptive Alt Text**: Graphical assets, diagrams, and illustrations provide clear, contextual
  alternative text.

______________________________________________________________________

## 2. Known Limitations & Workarounds

While we actively work to identify and eliminate barriers, some external environments may present constraints:

- **Terminal Emulator Color Schemes**: Highly customized terminal themes with non-standard contrast profiles
  may impact ANSI code readability. **Workaround**: Set `export NO_COLOR=1` in your shell environment to force
  monochrome output.
- **Wide Delimited Streams**: When inspecting verbose file lists with long absolute paths, terminal
  word-wrapping can impact speech cadence on certain screen readers. **Workaround**: Use relative path
  traversal (the default behavior) or pipe into a pager such as `less -R`.

______________________________________________________________________

## 3. Reporting Accessibility Barriers & Feedback

We actively welcome feedback and bug reports from users who encounter barriers while interacting with
`findfmt`.

### 3.1. Public Issue Tracker

If you encounter an accessibility barrier in the CLI, website, or documentation:

1. Visit our [GitHub Issues](https://github.com/bdperkin/findfmt/issues).
2. Open a new issue detailing:
   - The assistive technology or environment used (screen reader, terminal emulator, operating system).
   - The specific command or documentation URL where the barrier occurred.
   - The expected versus actual behavior.
3. Label the issue with `accessibility`.

### 3.2. Confidential or Direct Inquiries

For sensitive inquiries, private barrier reports, or direct consultation, please contact the maintainer
directly:

- **Contact**: Brandon Perkins
- **Email**: [bdperkin@gmail.com](mailto:bdperkin@gmail.com)
- **Response Commitment**: We commit to acknowledging all accessibility reports within **48–72 hours** and
  prioritizing remediations in upcoming releases.
