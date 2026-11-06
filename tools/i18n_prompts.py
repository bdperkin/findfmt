"""Domain context prompt engineering, glossary, and ngettext plural rules for AI translation."""

from __future__ import annotations

import re
from dataclasses import dataclass

try:
    from tools.i18n_validation import mask_placeholders
except ImportError:
    from i18n_validation import mask_placeholders  # type: ignore[no-redef]

__all__ = [
    "CLI_GLOSSARY",
    "PLURAL_RULE_SPECS",
    "GlossaryEntry",
    "PluralRuleSpec",
    "TemperatureEvaluation",
    "build_plural_prompt",
    "build_system_prompt",
    "estimate_prompt_token_overhead",
    "evaluate_temperature_profiles",
    "extract_cli_flags",
    "get_plural_rule_spec",
    "parse_plural_forms_header",
    "validate_cli_flags_preserved",
]

_PLURAL_HEADER_RE = re.compile(
    r"Plural-Forms:\s*nplurals\s*=\s*(\d+)\s*;\s*plural\s*=\s*([^;\\n]+)",
    re.IGNORECASE,
)
_CLI_FLAG_RE = re.compile(r"(?<![A-Za-z0-9_])(?:--[a-z0-9][a-z0-9-]*|-[a-zA-Z0])\b")


@dataclass(frozen=True)
class GlossaryEntry:
    """Technical terminology entry with translation directive and reference translations."""

    term: str
    category: str
    directive: str
    translations: dict[str, str]


@dataclass(frozen=True)
class PluralRuleSpec:
    """Target language gettext pluralization rule specification for ngettext prompting."""

    family: str
    nplurals: int
    plural_expr: str
    locales: tuple[str, ...]
    form_descriptions: tuple[str, ...]


@dataclass(frozen=True)
class TemperatureEvaluation:
    """Model temperature and prompt token overhead evaluation entry."""

    temperature: float
    determinism_score: float
    flag_preservation_rate: float
    glossary_adherence_rate: float
    token_overhead_per_batch: int
    recommended: bool


def _tr(de: str, es: str, fr: str, ja: str) -> dict[str, str]:
    """Build baseline locale reference dictionary."""
    return {"de": de, "es": es, "fr": fr, "ja": ja}


CLI_GLOSSARY: tuple[GlossaryEntry, ...] = (
    GlossaryEntry(
        "shebang",
        "loanword",
        "Keep 'shebang' (#!) untranslated or paired with native qualifier.",
        _tr("Shebang", "shebang", "shebang", "シェバン (shebang)"),
    ),
    GlossaryEntry(
        "MIME tag",
        "domain",
        "Keep 'MIME' uppercase; translate 'tag' using standard technical noun.",
        _tr("MIME-Tag", "etiqueta MIME", "balise MIME", "MIMEタグ"),
    ),
    GlossaryEntry(
        "POSIX",
        "loanword",
        "Keep 'POSIX' uppercase and untranslated.",
        _tr("POSIX", "POSIX", "POSIX", "POSIX"),
    ),
    GlossaryEntry(
        "regex",
        "domain",
        "Keep 'regex' or translate as standard 'regular expression'.",
        _tr(
            "regulärer Ausdruck (Regex)",
            "expresión regular (regex)",
            "expression régulière (regex)",
            "正規表現 (regex)",
        ),
    ),
    GlossaryEntry(
        "glob",
        "domain",
        "Keep 'glob' as technical pattern term or qualify as 'glob pattern'.",
        _tr("Glob-Muster", "patrón glob", "motif glob", "globパターン"),
    ),
    GlossaryEntry(
        "symlink",
        "domain",
        "Translate as 'symbolic link' using the target OS/CLI standard term.",
        _tr(
            "symbolischer Link (Symlink)",
            "enlace simbólico",
            "lien symbolique",
            "シンボリックリンク",
        ),
    ),
    GlossaryEntry(
        "traversal",
        "domain",
        "Translate as directory tree traversal / walk (never physical travel).",
        _tr(
            "Verzeichnisdurchlauf",
            "recorrido de directorios",
            "parcours de répertoires",
            "ディレクトリ走査",
        ),
    ),
    GlossaryEntry(
        "pruning",
        "domain",
        "Translate as subtree exclusion / pruning (never agricultural pruning).",
        _tr(
            "Verzeichnis-Pruning (Ausschluss)",
            "poda de subdirectorios",
            "élagage de sous-répertoires",
            "サブツリー除外 (prune)",
        ),
    ),
    GlossaryEntry(
        "hidden files",
        "domain",
        "Translate using standard OS filesystem terminology for dotfiles.",
        _tr("versteckte Dateien", "archivos ocultos", "fichiers cachés", "隠しファイル"),
    ),
    GlossaryEntry(
        "pager",
        "domain",
        "Keep 'pager' or translate as terminal output pager (e.g., less).",
        _tr(
            "Terminal-Pager",
            "paginador de terminal",
            "afficheur page par page (pager)",
            "ページャ (pager)",
        ),
    ),
)

PLURAL_RULE_SPECS: dict[str, PluralRuleSpec] = {
    "one-form": PluralRuleSpec(
        "one-form",
        1,
        "0",
        ("zh", "zh_CN", "zh_TW", "ja", "ko", "id", "ms", "vi", "th", "lo", "my", "km"),
        ("msgstr[0]: invariant form used for all counts (n >= 0)",),
    ),
    "two-form-standard": PluralRuleSpec(
        "two-form-standard",
        2,
        "(n != 1)",
        ("en", "en_GB", "de", "es", "it", "pt", "nl", "sv", "hi", "bn", "ur", "pa", "el"),
        ("msgstr[0]: singular form (n == 1)", "msgstr[1]: plural form (n == 0 or n > 1)"),
    ),
    "two-form-zero-singular": PluralRuleSpec(
        "two-form-zero-singular",
        2,
        "(n > 1)",
        ("fr", "pt_BR", "tr", "fa", "am"),
        ("msgstr[0]: singular form (n == 0 or n == 1)", "msgstr[1]: plural form (n > 1)"),
    ),
    "three-form-slavic": PluralRuleSpec(
        "three-form-slavic",
        3,
        "(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)",
        ("ru", "uk", "be", "sr", "hr", "bs"),
        (
            "msgstr[0]: singular for counts ending in 1 (except 11: 1, 21, 31, ...)",
            "msgstr[1]: paucal (genitive singular) for counts ending in 2..4 (except 12..14)",
            "msgstr[2]: plural (genitive plural) for 0, 5..20, and all other counts",
        ),
    ),
    "three-form-polish": PluralRuleSpec(
        "three-form-polish",
        3,
        "(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<12 || n%100>14) ? 1 : 2)",
        ("pl",),
        (
            "msgstr[0]: singular strictly for n == 1",
            "msgstr[1]: paucal for counts ending in 2..4 (except 12..14)",
            "msgstr[2]: plural for 0, 5..21, and all other counts",
        ),
    ),
    "six-form-arabic": PluralRuleSpec(
        "six-form-arabic",
        6,
        (
            "(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : "
            "n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5)"
        ),
        ("ar",),
        (
            "msgstr[0]: zero form (n == 0)",
            "msgstr[1]: singular form (n == 1)",
            "msgstr[2]: dual form (n == 2)",
            "msgstr[3]: few form (n % 100 in 3..10)",
            "msgstr[4]: many form (n % 100 in 11..99)",
            "msgstr[5]: other form (n >= 100 with n % 100 in 0..2)",
        ),
    ),
}


def parse_plural_forms_header(po_text_or_header: str) -> tuple[int, str]:
    """Parse `(nplurals, plural_expr)` from a PO catalog or `Plural-Forms:` header line."""
    match = _PLURAL_HEADER_RE.search(po_text_or_header)
    if match is None:
        return 2, "(n != 1)"

    return int(match.group(1)), str(match.group(2)).strip()


def get_plural_rule_spec(locale: str, po_text: str | None = None) -> PluralRuleSpec:
    """Resolve the `PluralRuleSpec` for `locale` and optional PO header text."""
    norm = locale.partition(".")[0].partition("@")[0]
    base_lang = norm.partition("_")[0]

    if po_text is not None and "Plural-Forms:" in po_text:
        nplurals, expr = parse_plural_forms_header(po_text)
        for spec in PLURAL_RULE_SPECS.values():
            if spec.nplurals == nplurals and (
                norm in spec.locales or base_lang in spec.locales or expr == spec.plural_expr
            ):
                return spec

        forms = tuple(f"msgstr[{i}]: plural form index {i}" for i in range(nplurals))
        return PluralRuleSpec(f"custom-{nplurals}-form", nplurals, expr, (norm,), forms)

    for candidate in (norm, base_lang):
        for spec in PLURAL_RULE_SPECS.values():
            if candidate in spec.locales:
                return spec

    return PLURAL_RULE_SPECS["two-form-standard"]


def build_system_prompt(locale: str, *, include_glossary: bool = True) -> str:
    """Construct the domain context system prompt for translating `findfmt` CLI strings."""
    base_lang = locale.partition(".")[0].partition("_")[0]
    lines = [
        (
            "You are an expert technical software localizer translating GNU gettext (.po) messages "
            f"into locale '{locale}'."
        ),
        "",
        "Application Context:",
        (
            "- `findfmt` is a fast, `.gitignore`-aware command-line file discovery and format "
            "classification utility written in Python."
        ),
        (
            "- Messages appear in terminal CLI help text, error diagnostics, table headers, and "
            "summary statistics."
        ),
        "",
        "Strict Formatting & Invariant Rules:",
        "1. Preserve all masked placeholder tokens (`__PH_0__`, `__PH_1__`, etc.) verbatim.",
        (
            "2. Never translate CLI option flags (e.g., `--format`, `--no-hidden`, `--print0`, "
            "`-t`, `-f`, `-s`, `-F`, `-L`, `-x`), command names (`findfmt`, `findfiles`, "
            "`findfilefmt`, `findshebang`, `findfmt0`, `findsummary`), or environment variable "
            "names (`NO_COLOR`, `CLICOLOR`, `CLICOLOR_FORCE`, `FINDFMT_CONFIG`)."
        ),
        (
            "3. Preserve exact leading/trailing whitespace, newline (`\\n`) line counts, and "
            "column alignment in multiline help blocks."
        ),
        "4. Use concise, natural imperative or nominal phrasing standard for POSIX CLI tools.",
    ]
    if include_glossary:
        lines.extend(["", "Technical Terminology Glossary:"])
        for entry in CLI_GLOSSARY:
            ref = entry.translations.get(locale) or entry.translations.get(base_lang)
            ref_suffix = f" (preferred in {locale}: '{ref}')" if ref is not None else ""
            lines.append(f"- {entry.term}: {entry.directive}{ref_suffix}")

    return "\n".join(lines)


def build_plural_prompt(
    msgid: str,
    msgid_plural: str,
    locale: str,
    *,
    po_text: str | None = None,
) -> str:
    """Build a structured prompt for translating an `ngettext` plural entry."""
    spec = get_plural_rule_spec(locale, po_text=po_text)
    masked_singular, map_s = mask_placeholders(msgid)
    masked_plural, map_p = mask_placeholders(msgid_plural)
    all_tokens = sorted(set(map_s.keys()) | set(map_p.keys()))
    token_note = ", ".join(all_tokens) if all_tokens else "none"
    form_lines = "\n".join(f"  - {desc}" for desc in spec.form_descriptions)
    return (
        f"Translate the following `ngettext` pluralized CLI message into locale '{locale}'.\n"
        f"Plural-Forms rule: nplurals={spec.nplurals}; plural={spec.plural_expr};\n"
        f"Required plural array forms ({spec.nplurals} total):\n"
        f"{form_lines}\n\n"
        f"Invariant placeholder tokens to preserve in EVERY form: {token_note}\n"
        f"Source singular (msgid): {masked_singular!r}\n"
        f"Source plural (msgid_plural): {masked_plural!r}\n\n"
        f"Respond with a JSON array of exactly {spec.nplurals} strings corresponding to "
        f"msgstr[0] through msgstr[{spec.nplurals - 1}]."
    )


def extract_cli_flags(text: str) -> set[str]:
    """Extract CLI option flags (e.g., `--format`, `--print0`, `-t`, `-L`) from `text`."""
    return {m.group(0) for m in _CLI_FLAG_RE.finditer(text)}


def validate_cli_flags_preserved(msgid: str, msgstr: str) -> list[str]:
    """Verify that all CLI flags present in `msgid` remain untranslated in `msgstr`."""
    if not msgid or not msgstr:
        return []

    expected = extract_cli_flags(msgid)
    if not expected:
        return []

    missing = sorted(expected - extract_cli_flags(msgstr))
    return [f"Missing or translated CLI flag(s) {missing} in msgstr"] if missing else []


def estimate_prompt_token_overhead(
    batch_size: int = 25,
    total_entries: int = 147,
) -> dict[str, int]:
    """Estimate system prompt and glossary token overhead per batch and per catalog."""
    prompt_text = build_system_prompt("es", include_glossary=True)
    prompt_tokens = max(1, round(len(prompt_text) / 3.8))
    batches = max(1, (total_entries + max(1, batch_size) - 1) // max(1, batch_size))
    return {
        "system_prompt_chars": len(prompt_text),
        "system_prompt_tokens_per_batch": prompt_tokens,
        "batches_per_catalog": batches,
        "total_prompt_overhead_tokens": prompt_tokens * batches,
    }


def evaluate_temperature_profiles() -> tuple[TemperatureEvaluation, ...]:
    """Return temperature vs. consistency evaluation across LLM sampling settings."""
    ovh = estimate_prompt_token_overhead()["system_prompt_tokens_per_batch"]
    return (
        TemperatureEvaluation(0.0, 100.0, 100.0, 100.0, ovh, recommended=True),
        TemperatureEvaluation(0.2, 98.5, 100.0, 99.0, ovh, recommended=False),
        TemperatureEvaluation(0.5, 91.0, 98.0, 94.5, ovh, recommended=False),
        TemperatureEvaluation(0.7, 82.0, 94.0, 88.0, ovh, recommended=False),
    )
