"""Maintenance script for gettext message catalog extraction, updates, and compilation."""

from __future__ import annotations

import argparse
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
            str(pot_file),
            str(source_dir),
        ]
        proc = subprocess.run(cmd, check=False)
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
            str(pot_file),
        ]
        py_files = [str(p) for p in source_dir.rglob("*.py")]
        cmd.extend(py_files)
        proc = subprocess.run(cmd, check=False)
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

    pybabel_bin = shutil.which("pybabel")
    if pybabel_bin:
        cmd = [
            pybabel_bin,
            "init",
            "-i",
            str(pot_file),
            "-d",
            str(locale_dir),
            "-l",
            locale,
            "-D",
            domain,
        ]
        proc = subprocess.run(cmd, check=False)
        return proc.returncode

    target_po = locale_dir / locale / "LC_MESSAGES" / f"{domain}.po"
    msginit_bin = shutil.which("msginit")
    if msginit_bin:
        target_po.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            msginit_bin,
            "--input",
            str(pot_file),
            "--output",
            str(target_po),
            "--locale",
            locale,
            "--no-translator",
        ]
        proc = subprocess.run(cmd, check=False)
        return proc.returncode

    # Pure Python copy fallback
    target_po.parent.mkdir(parents=True, exist_ok=True)
    content = pot_file.read_text(encoding="utf-8")
    content = content.replace("Language: \\n", f"Language: {locale}\\n").replace(
        "Language: \n",
        f"Language: {locale}\n",
    )
    target_po.write_text(content, encoding="utf-8")
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

    pybabel_bin = shutil.which("pybabel")
    if pybabel_bin:
        cmd = [
            pybabel_bin,
            "update",
            "-i",
            str(pot_file),
            "-d",
            str(locale_dir),
            "-D",
            domain,
        ]
        proc = subprocess.run(cmd, check=False)
        return proc.returncode

    msgmerge_bin = shutil.which("msgmerge")
    if msgmerge_bin:
        for po_path in locale_dir.glob(f"*/LC_MESSAGES/{domain}.po"):
            cmd = [msgmerge_bin, "--update", str(po_path), str(pot_file)]
            proc = subprocess.run(cmd, check=False)
            if proc.returncode != 0:
                return proc.returncode

        return 0

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
        cmd = [
            pybabel_bin,
            "compile",
            "-d",
            str(locale_dir),
            "-D",
            domain,
        ]
        proc = subprocess.run(cmd, check=False)
        return proc.returncode

    msgfmt_bin = shutil.which("msgfmt")
    if msgfmt_bin:
        for po_path in locale_dir.glob(f"*/LC_MESSAGES/{domain}.po"):
            mo_path = po_path.with_suffix(".mo")
            cmd = [msgfmt_bin, "-o", str(mo_path), str(po_path)]
            proc = subprocess.run(cmd, check=False)
            if proc.returncode != 0:
                return proc.returncode

        return 0

    if compile_po_to_mo is not None:
        try:
            for po_path in locale_dir.glob(f"*/LC_MESSAGES/{domain}.po"):
                mo_path = po_path.with_suffix(".mo")
                compile_po_to_mo(po_path, mo_path)
        except Exception as err:  # noqa: BLE001
            sys.stderr.write(f"Error compiling catalogs: {err}\n")
            return 1
        else:
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

    sub_extract = subparsers.add_parser("extract", help="Extract translatable strings to POT file.")
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
    sub_extract.add_argument(
        "--domain",
        default=DEFAULT_DOMAIN,
        help="Catalog domain (default: findfmt).",
    )

    sub_init = subparsers.add_parser("init", help="Initialize a new locale PO catalog.")
    sub_init.add_argument("locale", help="Locale code (e.g. es, fr, de, ja).")
    sub_init.add_argument(
        "--pot",
        type=Path,
        default=DEFAULT_POT_FILE,
        help="Input POT template file.",
    )
    sub_init.add_argument(
        "--localedir",
        type=Path,
        default=DEFAULT_LOCALE_DIR,
        help="Locale base directory.",
    )
    sub_init.add_argument(
        "--domain",
        default=DEFAULT_DOMAIN,
        help="Catalog domain (default: findfmt).",
    )

    sub_update = subparsers.add_parser("update", help="Update existing PO files from POT template.")
    sub_update.add_argument(
        "--pot",
        type=Path,
        default=DEFAULT_POT_FILE,
        help="Input POT template file.",
    )
    sub_update.add_argument(
        "--localedir",
        type=Path,
        default=DEFAULT_LOCALE_DIR,
        help="Locale base directory.",
    )
    sub_update.add_argument(
        "--domain",
        default=DEFAULT_DOMAIN,
        help="Catalog domain (default: findfmt).",
    )

    sub_compile = subparsers.add_parser("compile", help="Compile PO files into binary MO files.")
    sub_compile.add_argument(
        "--localedir",
        type=Path,
        default=DEFAULT_LOCALE_DIR,
        help="Locale base directory.",
    )
    sub_compile.add_argument(
        "--domain",
        default=DEFAULT_DOMAIN,
        help="Catalog domain (default: findfmt).",
    )

    sub_all = subparsers.add_parser(
        "all",
        help="Run extract, update, and compile lifecycle steps.",
    )
    sub_all.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Source directory.",
    )
    sub_all.add_argument(
        "--localedir",
        type=Path,
        default=DEFAULT_LOCALE_DIR,
        help="Locale directory.",
    )
    sub_all.add_argument(
        "--domain",
        default=DEFAULT_DOMAIN,
        help="Catalog domain.",
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
    if args.command == "extract":
        return extract_messages(args.source, args.output, args.domain)

    if args.command == "init":
        return init_catalog(args.locale, args.pot, args.localedir, args.domain)

    if args.command == "update":
        return update_catalogs(args.pot, args.localedir, args.domain)

    if args.command == "compile":
        return compile_catalogs(args.localedir, args.domain)

    return _run_all(args)


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
