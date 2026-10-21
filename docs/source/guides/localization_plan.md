# Translation and Localization Plan (i18n & l10n)

This document establishes the architecture, linguistic metadata, phased roadmap, and contribution
workflow for internationalization (i18n) and localization (l10n) across `findfmt`.

```{note}
All translation issues are aligned with the **Future Features** milestone. Active tracking issues and parent epics are cross-linked below.
```

______________________________________________________________________

## 1. Core Architecture

The `findfmt` internationalization architecture uses standard GNU gettext runtime protocols combined
with custom Hatchling build hooks and Sphinx documentation tooling:

- **Runtime Engine (`src/findfmt/i18n.py`)**: Wraps `gettext.translation()` with hierarchical
  fallback order: `LANGUAGE` → `LC_ALL` → `LC_MESSAGES` → `LANG` → `C`. Provides `_()` for standard
  message strings and `ngettext()` for pluralized counts. Supports CLI runtime overrides via
  `--locale <locale>` and `--lang <locale>`.
- **Maintenance Tooling (`tools/i18n.py`)**: Automates message extraction (`extract`), catalog
  initialization (`init <locale>`), updates (`update`), and compilation (`compile`). Enforces
  relative path location comments (`#: src/findfmt/...`) via `_sanitize_po_locations()` to ensure
  local build paths are never exposed.
- **Packaging Build Hook (`tools/hatch_build.py`)**: Compiles `.po` message catalogs under
  `src/findfmt/locale/*/LC_MESSAGES/*.po` into binary `.mo` catalogs during wheel and sdist
  packaging.
- **Documentation Localization (`docs/source/locale/`)**: Integrates with Sphinx `gettext` and
  `sphinx-intl` to generate localized HTML sites and man pages.
- **Security & Quality Gates**: The pre-commit hook `check-no-absolute-locale-paths` rejects any
  absolute path location comments in `.po` files. Test suites enforce 100% statement and branch
  coverage.

______________________________________________________________________

## 2. Implementation Phasing

Languages are organized into five strategic tiers based on speaker population, linguistic diversity,
and script complexity:

| Tier                         | Speaker Threshold     | Scope & Objective                                                                             | Status                                                                                                                      |
| ---------------------------- | --------------------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Tier 0: Baseline**         | Core Starters         | English (`en`), German (`de`), Spanish (`es`), French (`fr`), Japanese (`ja`).                | **Active / Initial Catalogs**                                                                                               |
| **Tier 1: High Reach**       | ≥ 120 Million         | 15 major global languages covering >6.5 billion aggregate speakers.                           | **Tracked ([#214](https://github.com/bdperkin/findfmt/issues/214)–[#228](https://github.com/bdperkin/findfmt/issues/228))** |
| **Tier 2: Medium Reach**     | 10M – 120 Million     | 37 prominent national and regional languages across all global families.                      | **Tracked ([#234](https://github.com/bdperkin/findfmt/issues/234)–[#270](https://github.com/bdperkin/findfmt/issues/270))** |
| **Tier 3: Regional & Niche** | < 10 Million          | Minority languages, regional dialects, and indigenous scripts.                                | **Planned under Epics**                                                                                                     |
| **Tier 4: Special**          | Constructed & Extinct | International auxiliary languages (Esperanto, Interlingua) and historical languages (Gothic). | **Planned under Epics**                                                                                                     |

______________________________________________________________________

## 3. Infrastructure & Architecture Issues

To support global scripts, bidirectional rendering, and regional standards, five foundational
infrastructure issues have been established:

- **[#229: feat(i18n): implement right-to-left (RTL) and bidirectional (BiDi) terminal formatting support](https://github.com/bdperkin/findfmt/issues/229)**
  Enables visual bidirectional reordering (Unicode BiDi algorithm) for monospace table
  (`RichTableFormatter`) and tree (`RichTreeFormatter`) formatters when outputting Arabic (`ar`),
  Urdu (`ur`), Persian (`fa`), Hebrew (`he`), or Kurdish (`ku`).
- **[#230: fix(format): audit and enforce cell-width alignment for CJK double-width characters across formatters](https://github.com/bdperkin/findfmt/issues/230)**
  Audits terminal column calculation to ensure full-width East Asian glyphs (Chinese
  `zh_CN`/`zh_TW`, Japanese `ja`, Korean `ko`) occupy two terminal cells using `wcwidth`/`cell_len`
  instead of string length.
- **[#231: feat(i18n): localize file sizes, numeric separators, and timestamps per regional locale standards](https://github.com/bdperkin/findfmt/issues/231)**
  Adapts decimal separators (`12.4 MB` vs `12,4 MB`), thousands separators, and date-time formats
  according to active `LC_NUMERIC` and `LC_TIME` settings.
- **[#232: test(i18n): create automated verification suite for complex multi-tier gettext pluralization rules](https://github.com/bdperkin/findfmt/issues/232)**
  Provides automated test fixtures verifying plural mapping for single-form, two-form, three-form
  Slavic, three-form Polish, and six-form Arabic rules in `findfmt.i18n.ngettext`.
- **[#233: ci(docs): configure automated multilingual Sphinx documentation builds in CI pipeline](https://github.com/bdperkin/findfmt/issues/233)**
  Configures `.github/workflows/docs.yml` to compile and publish multilingual Sphinx documentation
  subdirectories (`docs/<locale>/`).

______________________________________________________________________

## 4. Tier 1 Tracking Matrix (≥ 120M Speakers)

Each Tier 1 language has an active GitHub sub-issue under the **Future Features** milestone attached
to its parent epic:

| Locale Code | Language Name              | Language Family    |                      Parent Epic                       |                       Sub-Issue                        | Speakers |         Script          | Text Dir |      Plural Forms (`nplurals`)       |                            Status                            |
| :---------: | -------------------------- | ------------------ | :----------------------------------------------------: | :----------------------------------------------------: | -------: | :---------------------: | :------: | :----------------------------------: | :----------------------------------------------------------: |
|    `en`     | English                    | Germanic           | [#197](https://github.com/bdperkin/findfmt/issues/197) | [#214](https://github.com/bdperkin/findfmt/issues/214) |  ~1.46 B |          Latin          |   LTR    |             2 (`n != 1`)             |                   Canonical Catalog Active                   |
|    `de`     | German                     | Germanic           | [#197](https://github.com/bdperkin/findfmt/issues/197) | [#215](https://github.com/bdperkin/findfmt/issues/215) |   ~133 M |          Latin          |   LTR    |             2 (`n != 1`)             |                    Starter Catalog Active                    |
|   `zh_CN`   | Chinese (China / Mandarin) | Sino-Tibetan       | [#198](https://github.com/bdperkin/findfmt/issues/198) | [#216](https://github.com/bdperkin/findfmt/issues/216) |  ~1.14 B | Simplified Han (`Hans`) |   LTR    |               1 (`0`)                | Issue [#216](https://github.com/bdperkin/findfmt/issues/216) |
|    `hi`     | Hindi                      | Indo-Aryan         | [#199](https://github.com/bdperkin/findfmt/issues/199) | [#217](https://github.com/bdperkin/findfmt/issues/217) |   ~610 M |       Devanagari        |   LTR    |             2 (`n != 1`)             | Issue [#217](https://github.com/bdperkin/findfmt/issues/217) |
|    `bn`     | Bengali                    | Indo-Aryan         | [#199](https://github.com/bdperkin/findfmt/issues/199) | [#218](https://github.com/bdperkin/findfmt/issues/218) |   ~273 M |         Bengali         |   LTR    |             2 (`n != 1`)             | Issue [#218](https://github.com/bdperkin/findfmt/issues/218) |
|    `ur`     | Urdu                       | Indo-Aryan         | [#199](https://github.com/bdperkin/findfmt/issues/199) | [#219](https://github.com/bdperkin/findfmt/issues/219) |   ~232 M | Perso-Arabic (Nastaliq) | **RTL**  |             2 (`n != 1`)             | Issue [#219](https://github.com/bdperkin/findfmt/issues/219) |
|    `pa`     | Punjabi                    | Indo-Aryan         | [#199](https://github.com/bdperkin/findfmt/issues/199) | [#220](https://github.com/bdperkin/findfmt/issues/220) |   ~125 M |  Gurmukhi / Shahmukhi   |   LTR    |             2 (`n != 1`)             | Issue [#220](https://github.com/bdperkin/findfmt/issues/220) |
|    `es`     | Spanish                    | Romance            | [#200](https://github.com/bdperkin/findfmt/issues/200) | [#221](https://github.com/bdperkin/findfmt/issues/221) |   ~559 M |          Latin          |   LTR    |             2 (`n != 1`)             |                    Starter Catalog Active                    |
|    `fr`     | French                     | Romance            | [#200](https://github.com/bdperkin/findfmt/issues/200) | [#222](https://github.com/bdperkin/findfmt/issues/222) |   ~310 M |          Latin          |   LTR    |             2 (`n > 1`)              |                    Starter Catalog Active                    |
|    `pt`     | Portuguese (European)      | Romance            | [#200](https://github.com/bdperkin/findfmt/issues/200) | [#223](https://github.com/bdperkin/findfmt/issues/223) |   ~264 M |          Latin          |   LTR    |             2 (`n != 1`)             | Issue [#223](https://github.com/bdperkin/findfmt/issues/223) |
|   `pt_BR`   | Portuguese (Brazil)        | Romance            | [#200](https://github.com/bdperkin/findfmt/issues/200) | [#224](https://github.com/bdperkin/findfmt/issues/224) |   ~208 M |          Latin          |   LTR    |             2 (`n > 1`)              | Issue [#224](https://github.com/bdperkin/findfmt/issues/224) |
|    `ar`     | Arabic                     | Afroasiatic        | [#201](https://github.com/bdperkin/findfmt/issues/201) | [#225](https://github.com/bdperkin/findfmt/issues/225) |   ~370 M |         Arabic          | **RTL**  | 6 (zero, one, two, few, many, other) | Issue [#225](https://github.com/bdperkin/findfmt/issues/225) |
|    `ru`     | Russian                    | Slavic             | [#202](https://github.com/bdperkin/findfmt/issues/202) | [#226](https://github.com/bdperkin/findfmt/issues/226) |   ~255 M |        Cyrillic         |   LTR    |             3 (`Slavic`)             | Issue [#226](https://github.com/bdperkin/findfmt/issues/226) |
|    `id`     | Indonesian                 | Austronesian       | [#203](https://github.com/bdperkin/findfmt/issues/203) | [#227](https://github.com/bdperkin/findfmt/issues/227) |   ~199 M |          Latin          |   LTR    |               1 (`0`)                | Issue [#227](https://github.com/bdperkin/findfmt/issues/227) |
|    `ja`     | Japanese                   | Japonic & Koreanic | [#205](https://github.com/bdperkin/findfmt/issues/205) | [#228](https://github.com/bdperkin/findfmt/issues/228) |   ~123 M |      Kanji / Kana       |   LTR    |               1 (`0`)                |                    Starter Catalog Active                    |

______________________________________________________________________

## 5. Tier 2 Tracking Matrix (10M – 120M Speakers)

Each Tier 2 language has an active GitHub sub-issue under the **Future Features** milestone attached
to its parent epic:

| Locale Code | Language Name                  | Language Family     |                      Parent Epic                       |                       Sub-Issue                        | Speakers |          Script           |   Text Dir    |             Plural Forms (`nplurals`)              |
| :---------: | ------------------------------ | ------------------- | :----------------------------------------------------: | :----------------------------------------------------: | -------: | :-----------------------: | :-----------: | :------------------------------------------------: |
|   `en_GB`   | English (United Kingdom)       | Germanic            | [#197](https://github.com/bdperkin/findfmt/issues/197) | [#234](https://github.com/bdperkin/findfmt/issues/234) |    ~60 M |           Latin           |      LTR      |                    2 (`n != 1`)                    |
|    `nl`     | Dutch                          | Germanic            | [#197](https://github.com/bdperkin/findfmt/issues/197) | [#235](https://github.com/bdperkin/findfmt/issues/235) |    ~24 M |           Latin           |      LTR      |                    2 (`n != 1`)                    |
|    `sv`     | Swedish                        | Germanic            | [#197](https://github.com/bdperkin/findfmt/issues/197) | [#236](https://github.com/bdperkin/findfmt/issues/236) |    ~10 M |           Latin           |      LTR      |                    2 (`n != 1`)                    |
|    `my`     | Burmese                        | Sino-Tibetan        | [#198](https://github.com/bdperkin/findfmt/issues/198) | [#237](https://github.com/bdperkin/findfmt/issues/237) |    ~33 M |          Myanmar          |      LTR      |                      1 (`0`)                       |
|   `zh_TW`   | Chinese (Taiwan / Traditional) | Sino-Tibetan        | [#198](https://github.com/bdperkin/findfmt/issues/198) | [#238](https://github.com/bdperkin/findfmt/issues/238) |    ~23 M | Traditional Han (`Hant`)  |      LTR      |                      1 (`0`)                       |
|    `mr`     | Marathi                        | Indo-Aryan          | [#199](https://github.com/bdperkin/findfmt/issues/199) | [#239](https://github.com/bdperkin/findfmt/issues/239) |    ~99 M |        Devanagari         |      LTR      |                    2 (`n != 1`)                    |
|    `gu`     | Gujarati                       | Indo-Aryan          | [#199](https://github.com/bdperkin/findfmt/issues/199) | [#240](https://github.com/bdperkin/findfmt/issues/240) |    ~62 M |         Gujarati          |      LTR      |                    2 (`n != 1`)                    |
|    `or`     | Odia                           | Indo-Aryan          | [#199](https://github.com/bdperkin/findfmt/issues/199) | [#241](https://github.com/bdperkin/findfmt/issues/241) |    ~35 M |           Odia            |      LTR      |                    2 (`n != 1`)                    |
|    `mai`    | Maithili                       | Indo-Aryan          | [#199](https://github.com/bdperkin/findfmt/issues/199) | [#242](https://github.com/bdperkin/findfmt/issues/242) |    ~34 M | Devanagari / Mithilakshar |      LTR      |                    2 (`n != 1`)                    |
|    `as`     | Assamese                       | Indo-Aryan          | [#199](https://github.com/bdperkin/findfmt/issues/199) | [#243](https://github.com/bdperkin/findfmt/issues/243) |    ~15 M |     Bengali-Assamese      |      LTR      |                    2 (`n != 1`)                    |
|    `si`     | Sinhala                        | Indo-Aryan          | [#199](https://github.com/bdperkin/findfmt/issues/199) | [#244](https://github.com/bdperkin/findfmt/issues/244) |    ~17 M |          Sinhala          |      LTR      |                    2 (`n != 1`)                    |
|    `ne`     | Nepali                         | Indo-Aryan          | [#199](https://github.com/bdperkin/findfmt/issues/199) | [#245](https://github.com/bdperkin/findfmt/issues/245) |    ~16 M |        Devanagari         |      LTR      |                    2 (`n != 1`)                    |
|    `it`     | Italian                        | Romance             | [#200](https://github.com/bdperkin/findfmt/issues/200) | [#246](https://github.com/bdperkin/findfmt/issues/246) |    ~68 M |           Latin           |      LTR      |                    2 (`n != 1`)                    |
|    `ro`     | Romanian                       | Romance             | [#200](https://github.com/bdperkin/findfmt/issues/200) | [#247](https://github.com/bdperkin/findfmt/issues/247) |    ~24 M |           Latin           |      LTR      | 3 (`n==1?0:(((n%100>19)\|(n%100==0&&n!=0))?2:1))`) |
|    `ca`     | Catalan                        | Romance             | [#200](https://github.com/bdperkin/findfmt/issues/200) | [#248](https://github.com/bdperkin/findfmt/issues/248) |    ~10 M |           Latin           |      LTR      |                    2 (`n != 1`)                    |
|    `am`     | Amharic                        | Afroasiatic         | [#201](https://github.com/bdperkin/findfmt/issues/201) | [#249](https://github.com/bdperkin/findfmt/issues/249) |    ~58 M |     Ge'ez (Ethiopic)      |      LTR      |                    2 (`n > 1`)                     |
|    `pl`     | Polish                         | Slavic              | [#202](https://github.com/bdperkin/findfmt/issues/202) | [#250](https://github.com/bdperkin/findfmt/issues/250) |    ~40 M |           Latin           |      LTR      |                    3 (`Polish`)                    |
|    `uk`     | Ukrainian                      | Slavic              | [#202](https://github.com/bdperkin/findfmt/issues/202) | [#251](https://github.com/bdperkin/findfmt/issues/251) |    ~40 M |         Cyrillic          |      LTR      |                    3 (`Slavic`)                    |
|    `cs`     | Czech                          | Slavic              | [#202](https://github.com/bdperkin/findfmt/issues/202) | [#252](https://github.com/bdperkin/findfmt/issues/252) |  ~10.7 M |           Latin           |      LTR      |                    3 (`Czech`)                     |
|    `ms`     | Malay                          | Austronesian        | [#203](https://github.com/bdperkin/findfmt/issues/203) | [#253](https://github.com/bdperkin/findfmt/issues/253) |    ~30 M |           Latin           |      LTR      |                      1 (`0`)                       |
|    `te`     | Telugu                         | Dravidian           | [#204](https://github.com/bdperkin/findfmt/issues/204) | [#254](https://github.com/bdperkin/findfmt/issues/254) |    ~96 M |          Telugu           |      LTR      |                    2 (`n != 1`)                    |
|    `ta`     | Tamil                          | Dravidian           | [#204](https://github.com/bdperkin/findfmt/issues/204) | [#255](https://github.com/bdperkin/findfmt/issues/255) |    ~87 M |           Tamil           |      LTR      |                    2 (`n != 1`)                    |
|    `kn`     | Kannada                        | Dravidian           | [#204](https://github.com/bdperkin/findfmt/issues/204) | [#256](https://github.com/bdperkin/findfmt/issues/256) |    ~59 M |          Kannada          |      LTR      |                    2 (`n != 1`)                    |
|    `ml`     | Malayalam                      | Dravidian           | [#204](https://github.com/bdperkin/findfmt/issues/204) | [#257](https://github.com/bdperkin/findfmt/issues/257) |    ~38 M |         Malayalam         |      LTR      |                    2 (`n != 1`)                    |
|    `ko`     | Korean                         | Japonic & Koreanic  | [#205](https://github.com/bdperkin/findfmt/issues/205) | [#258](https://github.com/bdperkin/findfmt/issues/258) |    ~82 M |          Hangul           |      LTR      |                      1 (`0`)                       |
|    `nqo`    | N'Ko / Manding                 | Niger–Congo         | [#206](https://github.com/bdperkin/findfmt/issues/206) | [#259](https://github.com/bdperkin/findfmt/issues/259) |    ~40 M |           N'Ko            |    **RTL**    |                      1 (`0`)                       |
|    `zu`     | Zulu                           | Niger–Congo         | [#206](https://github.com/bdperkin/findfmt/issues/206) | [#260](https://github.com/bdperkin/findfmt/issues/260) |    ~14 M |           Latin           |      LTR      |                    2 (`n != 1`)                    |
|    `tr`     | Turkish                        | Turkic              | [#207](https://github.com/bdperkin/findfmt/issues/207) | [#261](https://github.com/bdperkin/findfmt/issues/261) |    ~90 M |           Latin           |      LTR      |                    2 (`n > 1`)                     |
|    `kk`     | Kazakh                         | Turkic              | [#207](https://github.com/bdperkin/findfmt/issues/207) | [#262](https://github.com/bdperkin/findfmt/issues/262) |    ~15 M |     Cyrillic / Latin      |      LTR      |                    2 (`n != 1`)                    |
|    `fa`     | Persian                        | Other Indo-European | [#208](https://github.com/bdperkin/findfmt/issues/208) | [#263](https://github.com/bdperkin/findfmt/issues/263) |    ~79 M |       Perso-Arabic        |    **RTL**    |                    2 (`n > 1`)                     |
|    `ku`     | Kurdish                        | Other Indo-European | [#208](https://github.com/bdperkin/findfmt/issues/208) | [#264](https://github.com/bdperkin/findfmt/issues/264) |    ~30 M |   Latin / Perso-Arabic    | LTR / **RTL** |                    2 (`n != 1`)                    |
|    `hu`     | Hungarian                      | Uralic              | [#209](https://github.com/bdperkin/findfmt/issues/209) | [#265](https://github.com/bdperkin/findfmt/issues/265) |    ~13 M |           Latin           |      LTR      |                    2 (`n != 1`)                    |
|    `el`     | Greek                          | Hellenic            | [#210](https://github.com/bdperkin/findfmt/issues/210) | [#266](https://github.com/bdperkin/findfmt/issues/266) |    ~13 M |           Greek           |      LTR      |                    2 (`n != 1`)                    |
|    `vi`     | Vietnamese                     | All Other           | [#211](https://github.com/bdperkin/findfmt/issues/211) | [#267](https://github.com/bdperkin/findfmt/issues/267) |    ~86 M |     Latin (Quốc ngữ)      |      LTR      |                      1 (`0`)                       |
|    `th`     | Thai                           | All Other           | [#211](https://github.com/bdperkin/findfmt/issues/211) | [#268](https://github.com/bdperkin/findfmt/issues/268) |    ~61 M |           Thai            |      LTR      |                      1 (`0`)                       |
|    `lo`     | Lao                            | All Other           | [#211](https://github.com/bdperkin/findfmt/issues/211) | [#269](https://github.com/bdperkin/findfmt/issues/269) |    ~30 M |            Lao            |      LTR      |                      1 (`0`)                       |
|    `km`     | Khmer                          | All Other           | [#211](https://github.com/bdperkin/findfmt/issues/211) | [#270](https://github.com/bdperkin/findfmt/issues/270) |    ~16 M |           Khmer           |      LTR      |                      1 (`0`)                       |

______________________________________________________________________

## 6. Language Family Catalog & Hierarchy

The 17 GitHub Epics organize all 52 active language sub-issues and subsequent phases:

```text
[Epic #197] Germanic (~1.83B)
├── [x] #214: en (English - ~1.46B)
├── [x] #215: de (German - ~133M)
├── [x] #234: en_GB (English UK - ~60M)
├── [x] #235: nl (Dutch - ~24M)
├── [x] #236: sv (Swedish - ~10M)
├── [ ] af (Afrikaans - ~9M)
├── [ ] da (Danish - ~6M)
├── [ ] nb (Norwegian Bokmål - ~3M)
├── [ ] yi (Yiddish - ~600k)
├── [ ] nn (Norwegian Nynorsk - ~600k)
└── [ ] is (Icelandic - ~370k)

[Epic #198] Sino-Tibetan (~1.42B)
├── [x] #216: zh_CN (Mandarin China - ~1.14B)
├── [x] #237: my (Burmese - ~33M)
├── [x] #238: zh_TW (Mandarin Taiwan - ~23M)
├── [ ] zh_HK (Cantonese Hong Kong - ~7M)
├── [ ] bo (Tibetan - ~6M)
├── [ ] ii (Sichuan Yi - ~2M)
├── [ ] mni (Manipuri - ~1.8M)
└── [ ] dz (Dzongkha - ~600k)

[Epic #199] Indo-Aryan (~1.39B)
├── [x] #217: hi (Hindi - ~610M)
├── [x] #218: bn (Bengali - ~273M)
├── [x] #219: ur (Urdu - ~232M)
├── [x] #220: pa (Punjabi - ~125M)
├── [x] #239: mr (Marathi - ~99M)
├── [x] #240: gu (Gujarati - ~62M)
├── [x] #241: or (Odia - ~35M)
├── [x] #242: mai (Maithili - ~34M)
├── [x] #243: as (Assamese - ~15M)
├── [x] #244: si (Sinhala - ~17M)
├── [x] #245: ne (Nepali - ~16M)
└── [ ] dv (Divehi - ~340k)

[Epic #200] Romance (~1.25B)
├── [x] #221: es (Spanish - ~559M)
├── [x] #222: fr (French - ~310M)
├── [x] #223: pt (Portuguese European - ~264M)
├── [x] #224: pt_BR (Portuguese Brazil - ~208M)
├── [x] #246: it (Italian - ~68M)
├── [x] #247: ro (Romanian - ~24M)
├── [x] #248: ca (Catalan - ~10M)
├── [ ] gl (Galician - ~2.4M)
└── [ ] ast (Asturian - ~550k)

[Epic #201] Afroasiatic (~480M)
├── [x] #225: ar (Arabic - ~370M)
├── [x] #249: am (Amharic - ~58M)
├── [ ] he (Hebrew - ~9M)
├── [ ] kab (Kabyle - ~5M)
└── [ ] syr (Syriac - ~300k)

[Epic #202] Slavic (~415M)
├── [x] #226: ru (Russian - ~255M)
├── [x] #250: pl (Polish - ~40M)
├── [x] #251: uk (Ukrainian - ~40M)
├── [x] #252: cs (Czech - ~10.7M)
├── [ ] sr (Serbian - ~9M)
├── [ ] bg (Bulgarian - ~6.5M)
├── [ ] hr (Croatian - ~5.5M)
├── [ ] sk (Slovak - ~5M)
├── [ ] be (Belarusian - ~2.5M)
├── [ ] sl (Slovenian - ~2.5M)
├── [ ] bs (Bosnian - ~2M)
└── [ ] mk (Macedonian - ~2M)

[Epic #203] Austronesian (~295M)
├── [x] #227: id (Indonesian - ~199M)
└── [x] #253: ms (Malay - ~30M)

[Epic #204] Dravidian (~270M)
├── [x] #254: te (Telugu - ~96M)
├── [x] #255: ta (Tamil - ~87M)
├── [x] #256: kn (Kannada - ~59M)
└── [x] #257: ml (Malayalam - ~38M)

[Epic #205] Japonic & Koreanic (~205M)
├── [x] #228: ja (Japanese - ~123M)
└── [x] #258: ko (Korean - ~82M)

[Epic #206] Niger–Congo (~210M)
├── [x] #259: nqo (N'Ko / Manding - ~40M)
├── [x] #260: zu (Zulu - ~14M)
├── [ ] xh (Xhosa - ~8.2M)
├── [ ] ts (Tsonga - ~7M)
├── [ ] tn (Tswana - ~6M)
├── [ ] nso (Northern Sotho - ~5M)
├── [ ] ss (Swazi - ~2.5M)
├── [ ] nr (Southern Ndebele - ~2.1M)
└── [ ] ve (Venda - ~1.3M)

[Epic #207] Turkic (~165M)
├── [x] #261: tr (Turkish - ~90M)
└── [x] #262: kk (Kazakh - ~15M)

[Epic #208] Other Indo-European (~124M)
├── [x] #263: fa (Persian - ~79M)
├── [x] #264: ku (Kurdish - ~30M)
├── [ ] sq (Albanian - ~7.5M)
├── [ ] hy (Armenian - ~7M)
├── [ ] lt (Lithuanian - ~3M)
├── [ ] ga (Irish - ~1.7M)
├── [ ] lv (Latvian - ~1.5M)
├── [ ] cy (Welsh - ~900k)
└── [ ] br (Breton - ~200k)

[Epic #209] Uralic (~18M)
├── [x] #265: hu (Hungarian - ~13M)
├── [ ] fi (Finnish - ~5.4M)
└── [ ] et (Estonian - ~1.1M)

[Epic #210] Hellenic (~13M)
└── [x] #266: el (Greek - ~13M)

[Epic #211] All Other (~200M)
├── [x] #267: vi (Vietnamese - ~86M)
├── [x] #268: th (Thai - ~61M)
├── [x] #269: lo (Lao - ~30M)
├── [x] #270: km (Khmer - ~16M)
├── [ ] sat (Santali - ~7.3M)
├── [ ] ka (Georgian - ~4M)
├── [ ] eu (Basque - ~900k)
├── [ ] iu (Inuktitut - ~40k)
└── [ ] chr (Cherokee - ~2k)

[Epic #212] Constructive & Artificial (~2M)
├── [ ] eo (Esperanto - ~2M)
└── [ ] ia (Interlingua - ~Few thousand)

[Epic #213] Extinct (0)
└── [ ] got (Gothic - 0)
```

______________________________________________________________________

## 7. Developer Implementation Workflow

Follow these steps when implementing support for a target locale `<locale>`:

### 7.1. Step 1: Initialize or Update Message Catalog

Extract translatable strings and initialize the catalog:

```bash
# Extract latest message strings from codebase into findfmt.pot
uv run python tools/i18n.py extract

# For a new language: initialize catalog from template
uv run python tools/i18n.py init <locale>

# For existing catalogs: synchronize with template
uv run python tools/i18n.py update
```

The catalog is created or updated at: `src/findfmt/locale/<locale>/LC_MESSAGES/findfmt.po`

### 7.2. Step 2: Configure the Plural-Forms Header

Edit `src/findfmt/locale/<locale>/LC_MESSAGES/findfmt.po` and set the `Plural-Forms` header
according to gettext standards:

- **Single Form (`nplurals=1; plural=0;`)**: Applicable to Chinese (`zh_CN`, `zh_TW`), Japanese
  (`ja`), Korean (`ko`), Indonesian (`id`), Malay (`ms`), Vietnamese (`vi`), Thai (`th`), Lao
  (`lo`), Burmese (`my`), Khmer (`km`), N'Ko (`nqo`).
- **Two Forms (`nplurals=2; plural=(n != 1);`)**: Applicable to English (`en`, `en_GB`), German
  (`de`), Spanish (`es`), Italian (`it`), Catalan (`ca`), Dutch (`nl`), Swedish (`sv`), Greek
  (`el`), Hindi (`hi`), Bengali (`bn`), Urdu (`ur`), Punjabi (`pa`), Marathi (`mr`), Gujarati
  (`gu`), Odia (`or`), Telugu (`te`), Tamil (`ta`), Kannada (`kn`), Malayalam (`ml`), Zulu (`zu`),
  Hungarian (`hu`).
- **French & Brazilian Portuguese (`nplurals=2; plural=(n > 1);`)**: Applicable where 0 and 1 take
  the singular form: French (`fr`), Brazilian Portuguese (`pt_BR`), Turkish (`tr`), Persian (`fa`),
  Amharic (`am`).
- **Slavic Three Forms
  (`nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);`)**:
  Applicable to Russian (`ru`), Ukrainian (`uk`), Belarusian (`be`), Serbian (`sr`), Croatian
  (`hr`), Bosnian (`bs`).
- **Polish Three Forms
  (`nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<12 || n%100>14) ? 1 : 2);`)**:
  Applicable to Polish (`pl`).
- **Czech Three Forms (`nplurals=3; plural=(n==1) ? 0 : (n>=2 && n<=4) ? 1 : 2;`)**: Applicable to
  Czech (`cs`), Slovak (`sk`).
- **Romanian Three Forms (`nplurals=3; plural=(n==1?0:(((n%100>19)||(n%100==0&&n!=0))?2:1));`)**:
  Applicable to Romanian (`ro`).
- **Arabic Six Forms
  (`nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5);`)**:
  Applicable to Arabic (`ar`).

### 7.3. Step 3: Translate Strings & Validate Format Placeholders

- Translate all `msgid` entries into `msgstr` (or `msgstr[0]`, `msgstr[1]`, etc. for pluralized
  strings).
- Ensure formatting placeholders (such as `{count}`, `{path}`, `%s`) are preserved verbatim.
- Retain command-line arguments, option flags (`--tree`, `-t`, `-s`), and tag names without
  translation.
- Ensure all files are saved with UTF-8 encoding without byte-order marks (BOM).

### 7.4. Step 4: Compile Catalogs and Test Packaging

Compile `.po` files to binary `.mo` format and verify wheel packaging:

```bash
# Compile catalogs
uv run python tools/i18n.py compile

# Verify Hatchling packaging build hook compiles catalogs
uv build
```

### 7.5. Step 5: Add Unit & Integration Tests

Add test cases to `tests/unit/test_i18n_runtime.py` verifying:

1. Catalog loading via `override_locale("<locale>")`.
2. Execution of the CLI with `--locale <locale>` or `--lang <locale>`.
3. Boundary testing of singular and plural numbers.
4. Clean rendering without mojibake or string interpolation errors.

### 7.6. Step 6: Sphinx Documentation Localization

Extract documentation strings and update language catalogs for Sphinx:

```bash
# Extract documentation gettext catalog
uv run sphinx-build -b gettext docs/source docs/build/gettext

# Initialize or update documentation catalog
uv run sphinx-intl update -p docs/build/gettext -l <locale>
```

### 7.7. Step 7: Quality Verification Gates

Run the automated verification suite:

```bash
# Verify quality gates and 100% coverage
uv run python tools/verify_quality.py

# Verify pre-commit hooks (including check-no-absolute-locale-paths)
uv run pre-commit run --all-files
```
