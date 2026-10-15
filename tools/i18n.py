"""Maintenance script for gettext message catalog extraction, updates, and compilation."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from tools.hatch_build import compile_po_to_mo
except ImportError:
    try:
        from hatch_build import compile_po_to_mo  # type: ignore[no-redef]
    except ImportError:
        compile_po_to_mo = None  # type: ignore[assignment]

DEFAULT_DOMAIN = "findfmt"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "src" / "findfmt"
DEFAULT_LOCALE_DIR = PROJECT_ROOT / "src" / "findfmt" / "locale"
DEFAULT_POT_FILE = DEFAULT_LOCALE_DIR / f"{DEFAULT_DOMAIN}.pot"
BUGS_ADDRESS = "https://github.com/bdperkin/findfmt/issues"
DEFAULT_LANGUAGES = ["es", "fr", "de", "ja"]


def _to_rel_path_str(path: Path, base: Path = PROJECT_ROOT) -> str:
    """Return path as a relative string if inside base, else as absolute string."""
    try:
        if path.resolve().is_relative_to(base.resolve()):
            return path.resolve().relative_to(base.resolve()).as_posix()
    except (ValueError, OSError):
        pass

    return str(path)


def _get_working_dir(*paths: Path, base: Path = PROJECT_ROOT) -> Path | None:
    """Return base as working directory if all given paths are inside base."""
    try:
        if all(p.resolve().is_relative_to(base.resolve()) for p in paths):
            return base
    except (ValueError, OSError):
        pass

    return None


def _sanitize_po_locations(file_path: Path, root: Path = PROJECT_ROOT) -> None:
    """Ensure file location comments in a PO/POT file use relative paths.

    Strips absolute project root prefixes or full filesystem paths from
    location comments (e.g. `#: /path/to/project/src/...` -> `#: src/...`).

    Args:
        file_path: Path to the .po or .pot file to sanitize.
        root: Project root directory to treat as base.
    """
    if not file_path.is_file():
        return

    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    modified = False
    new_lines: list[str] = []

    res_root = str(root.resolve()).rstrip("/")
    plain_root = str(root).rstrip("/")
    prefixes = [
        f"{res_root}/",
        f"{plain_root}/",
        f"{res_root.replace('/', chr(92))}\\",
        f"{plain_root.replace('/', chr(92))}\\",
    ]
    unique_prefixes = list(dict.fromkeys(prefixes))

    pattern = re.compile(r"(^#: |\s)(?:[A-Za-z]:[\\/]|/)[^\s:]*?[\\/](src[\\/][^\s:]+:\d+)")

    def _repl(m: re.Match[str]) -> str:
        prefix = str(m.group(1))
        rel = str(m.group(2)).replace("\\", "/")
        return f"{prefix}{rel}"

    for line in lines:
        if line.startswith("#: "):
            new_line = line
            for prefix in unique_prefixes:
                if prefix in new_line:
                    new_line = new_line.replace(prefix, "")

            new_line = pattern.sub(_repl, new_line)
            if new_line != line:
                modified = True

            new_lines.append(new_line)
        else:
            new_lines.append(line)

    if modified:
        file_path.write_text("".join(new_lines), encoding="utf-8")


def extract_messages(
    source_dir: Path = DEFAULT_SOURCE_DIR,
    pot_file: Path = DEFAULT_POT_FILE,
    domain: str = DEFAULT_DOMAIN,
    bugs_address: str = BUGS_ADDRESS,
) -> int:
    """Extract translatable strings from source files into a POT template file.

    Wraps pybabel extract with xgettext fallback.

    Args:
        source_dir: Directory containing source code to inspect.
        pot_file: Output path for the generated .pot template.
        domain: Translation domain name.
        bugs_address: URL or email for bug reports in the catalog header.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    pot_file.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout.write(f"Extracting messages from {source_dir} -> {pot_file}\n")

    cwd = _get_working_dir(source_dir, pot_file)
    cmd_source = _to_rel_path_str(source_dir) if cwd else str(source_dir)
    cmd_pot = _to_rel_path_str(pot_file) if cwd else str(pot_file)

    pybabel_bin = shutil.which("pybabel")
    if pybabel_bin:
        cmd = [
            pybabel_bin,
            "extract",
            "-k",
            "_",
            "-k",
            "ngettext:1,2",
            "--project",
            domain,
            "--version",
            "0.8.0",
            "--msgid-bugs-address",
            bugs_address,
            "-o",
            cmd_pot,
            cmd_source,
        ]
        proc = subprocess.run(cmd, cwd=cwd, check=False)
        if proc.returncode == 0:
            _sanitize_po_locations(pot_file, root=PROJECT_ROOT)

        return proc.returncode

    xgettext_bin = shutil.which("xgettext")
    if xgettext_bin:
        cmd = [
            xgettext_bin,
            "--language=Python",
            "--keyword=_",
            "--keyword=ngettext:1,2",
            f"--msgid-bugs-address={bugs_address}",
            "--from-code=UTF-8",
            "-o",
            cmd_pot,
        ]
        if cwd == PROJECT_ROOT:
            py_files = [_to_rel_path_str(p, PROJECT_ROOT) for p in sorted(source_dir.rglob("*.py"))]
        else:
            py_files = [str(p) for p in sorted(source_dir.rglob("*.py"))]

        cmd.extend(py_files)
        proc = subprocess.run(cmd, cwd=cwd, check=False)
        if proc.returncode == 0:
            _sanitize_po_locations(pot_file, root=PROJECT_ROOT)

        return proc.returncode

    sys.stderr.write("Error: Neither 'pybabel' nor 'xgettext' was found in PATH.\n")
    return 1


def init_catalog(
    locale: str,
    pot_file: Path = DEFAULT_POT_FILE,
    locale_dir: Path = DEFAULT_LOCALE_DIR,
    domain: str = DEFAULT_DOMAIN,
) -> int:
    """Initialize a new language PO catalog from a POT template.

    Args:
        locale: Target locale code (e.g. 'es', 'fr').
        pot_file: Input POT template path.
        locale_dir: Destination directory for locale catalogs.
        domain: Translation domain name.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    if not pot_file.is_file():
        sys.stderr.write(f"Error: Template file {pot_file} not found. Run 'extract' first.\n")
        return 1

    target_po = locale_dir / locale / "LC_MESSAGES" / f"{domain}.po"
    cwd = _get_working_dir(pot_file, locale_dir)
    cmd_pot = _to_rel_path_str(pot_file) if cwd else str(pot_file)
    cmd_locale = _to_rel_path_str(locale_dir) if cwd else str(locale_dir)

    pybabel_bin = shutil.which("pybabel")
    if pybabel_bin:
        cmd = [pybabel_bin, "init", "-i", cmd_pot, "-d", cmd_locale, "-l", locale, "-D", domain]
        proc = subprocess.run(cmd, cwd=cwd, check=False)
        if proc.returncode == 0:
            _sanitize_po_locations(target_po, root=PROJECT_ROOT)

        return proc.returncode

    msginit_bin = shutil.which("msginit")
    if msginit_bin:
        target_po.parent.mkdir(parents=True, exist_ok=True)
        cmd_target = _to_rel_path_str(target_po) if cwd else str(target_po)
        cmd = [
            msginit_bin,
            "--input",
            cmd_pot,
            "--output",
            cmd_target,
            "--locale",
            locale,
            "--no-translator",
        ]
        proc = subprocess.run(cmd, cwd=cwd, check=False)
        if proc.returncode == 0:
            _sanitize_po_locations(target_po, root=PROJECT_ROOT)

        return proc.returncode

    # Pure Python copy fallback
    target_po.parent.mkdir(parents=True, exist_ok=True)
    content = pot_file.read_text(encoding="utf-8")
    content = content.replace("Language: \\n", f"Language: {locale}\\n").replace(
        "Language: \n",
        f"Language: {locale}\n",
    )
    target_po.write_text(content, encoding="utf-8")
    _sanitize_po_locations(target_po, root=PROJECT_ROOT)
    sys.stdout.write(f"Created catalog {target_po} (fallback)\n")
    return 0


def update_catalogs(
    pot_file: Path = DEFAULT_POT_FILE,
    locale_dir: Path = DEFAULT_LOCALE_DIR,
    domain: str = DEFAULT_DOMAIN,
) -> int:
    """Update all existing language PO catalogs from POT template.

    Args:
        pot_file: Source POT template path.
        locale_dir: Directory containing locale catalogs.
        domain: Translation domain name.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    if not pot_file.is_file():
        sys.stderr.write(f"Error: Template file {pot_file} not found. Run 'extract' first.\n")
        return 1

    cwd = _get_working_dir(pot_file, locale_dir)
    cmd_pot = _to_rel_path_str(pot_file) if cwd else str(pot_file)
    cmd_locale = _to_rel_path_str(locale_dir) if cwd else str(locale_dir)

    pybabel_bin = shutil.which("pybabel")
    if pybabel_bin:
        cmd = [pybabel_bin, "update", "-i", cmd_pot, "-d", cmd_locale, "-D", domain]
        proc = subprocess.run(cmd, cwd=cwd, check=False)
        if proc.returncode == 0:
            for po_path in locale_dir.glob(f"*/LC_MESSAGES/{domain}.po"):
                _sanitize_po_locations(po_path, root=PROJECT_ROOT)

        return proc.returncode

    msgmerge_bin = shutil.which("msgmerge")
    if msgmerge_bin:
        for po_path in locale_dir.glob(f"*/LC_MESSAGES/{domain}.po"):
            cmd_target = _to_rel_path_str(po_path) if cwd else str(po_path)
            cmd = [msgmerge_bin, "--update", cmd_target, cmd_pot]
            proc = subprocess.run(cmd, cwd=cwd, check=False)
            if proc.returncode != 0:
                return proc.returncode

            _sanitize_po_locations(po_path, root=PROJECT_ROOT)

        return 0

    for po_path in locale_dir.glob(f"*/LC_MESSAGES/{domain}.po"):
        _sanitize_po_locations(po_path, root=PROJECT_ROOT)

    sys.stderr.write("Warning: Neither 'pybabel' nor 'msgmerge' found for catalog updates.\n")
    return 0


def compile_catalogs(
    locale_dir: Path = DEFAULT_LOCALE_DIR,
    domain: str = DEFAULT_DOMAIN,
) -> int:
    """Compile all PO catalogs under locale_dir to binary MO catalogs.

    Args:
        locale_dir: Directory containing locale catalogs.
        domain: Translation domain name.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    pybabel_bin = shutil.which("pybabel")
    if pybabel_bin:
        cmd = [pybabel_bin, "compile", "-d", str(locale_dir), "-D", domain]
        return subprocess.run(cmd, check=False).returncode

    msgfmt_bin = shutil.which("msgfmt")
    if msgfmt_bin:
        for po_path in locale_dir.glob(f"*/LC_MESSAGES/{domain}.po"):
            mo_path = po_path.with_suffix(".mo")
            proc = subprocess.run([msgfmt_bin, "-o", str(mo_path), str(po_path)], check=False)
            if proc.returncode != 0:
                return proc.returncode

        return 0

    if compile_po_to_mo is not None:
        try:
            for po_path in locale_dir.glob(f"*/LC_MESSAGES/{domain}.po"):
                compile_po_to_mo(po_path, po_path.with_suffix(".mo"))
        except Exception as err:  # noqa: BLE001
            sys.stderr.write(f"Error compiling catalogs: {err}\n")
            return 1

        return 0

    sys.stderr.write("Error: No suitable compiler found for catalogs.\n")
    return 1


def build_parser() -> argparse.ArgumentParser:
    """Build command line argument parser for i18n management.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="i18n.py",
        description="Extract, update, and compile gettext translation catalogs for findfmt.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    domain_p = argparse.ArgumentParser(add_help=False)
    domain_p.add_argument(
        "--domain",
        default=DEFAULT_DOMAIN,
        help="Catalog domain (default: findfmt).",
    )

    loc_p = argparse.ArgumentParser(add_help=False)
    loc_p.add_argument(
        "--localedir",
        type=Path,
        default=DEFAULT_LOCALE_DIR,
        help="Locale base directory.",
    )

    pot_p = argparse.ArgumentParser(add_help=False)
    pot_p.add_argument(
        "--pot",
        type=Path,
        default=DEFAULT_POT_FILE,
        help="Input POT template file.",
    )

    sub_extract = subparsers.add_parser(
        "extract",
        parents=[domain_p],
        help="Extract translatable strings to POT file.",
    )
    sub_extract.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Source directory (default: src/findfmt).",
    )
    sub_extract.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_POT_FILE,
        help="Output POT file (default: src/findfmt/locale/findfmt.pot).",
    )

    sub_init = subparsers.add_parser(
        "init",
        parents=[domain_p, pot_p, loc_p],
        help="Initialize a new locale PO catalog.",
    )
    sub_init.add_argument("locale", help="Locale code (e.g. es, fr, de, ja).")

    subparsers.add_parser(
        "update",
        parents=[domain_p, pot_p, loc_p],
        help="Update existing PO files from POT template.",
    )
    subparsers.add_parser(
        "compile",
        parents=[domain_p, loc_p],
        help="Compile PO files into binary MO files.",
    )

    sub_all = subparsers.add_parser(
        "all",
        parents=[domain_p, loc_p],
        help="Run extract, update, and compile lifecycle steps.",
    )
    sub_all.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Source directory.",
    )

    return parser


def _run_all(args: argparse.Namespace) -> int:
    """Run extract, update, and compile lifecycle steps in sequence."""
    pot = args.localedir / f"{args.domain}.pot"
    code = extract_messages(args.source, pot, args.domain)
    if code != 0:
        return code

    code = update_catalogs(pot, args.localedir, args.domain)
    if code != 0:
        return code

    return compile_catalogs(args.localedir, args.domain)


def _dispatch_command(args: argparse.Namespace) -> int:
    """Dispatch parsed command to the matching handler function."""
    handlers = {
        "extract": lambda: extract_messages(args.source, args.output, args.domain),
        "init": lambda: init_catalog(args.locale, args.pot, args.localedir, args.domain),
        "update": lambda: update_catalogs(args.pot, args.localedir, args.domain),
        "compile": lambda: compile_catalogs(args.localedir, args.domain),
        "all": lambda: _run_all(args),
    }
    return handlers[args.command]()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for i18n maintenance tool.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code integer.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    return _dispatch_command(args)


if __name__ == "__main__":
    sys.exit(main())
