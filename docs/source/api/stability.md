# API Stability Policy

`findfmt` follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html). This page
defines what the public Python API is, what stays compatible within the 1.x line, and how changes
are caught before release.

## 1. What Is Public

The public API is every name listed in the `__all__` of the `findfmt` package and its submodules.
Everything else is internal and may change in any release:

- names that start with an underscore, or are not listed in `__all__`;
- the `tools/` and `tests/` directories.

Command-line options, configuration keys, environment variables, and [exit codes](../cli/index.md)
are covered by the same compatibility promise as the Python API.

## 2. Compatibility Within 1.x

Within the 1.x line:

- Public names are not removed or renamed without a deprecation period.
- Existing calls keep working: new parameters are optional, and are added at the end or as
  keyword-only parameters.
- Enumeration members keep their names and values, and comparisons with those values keep working.
- Exception classes keep their place in the `FindFmtError` hierarchy.

### 2.1. Pass Arguments by Keyword

Some public functions and classes take many parameters, and their positional order is not
guaranteed. Pass arguments to these by keyword:

- **`TraversalConfig`**: 1.0.2 inserted `csv_safe` in the middle of its fields.
- **CLI command callbacks** such as `findfmt.cli.findfmt`: Click always calls them by keyword, and
  1.1 inserted `exit_status` in the middle of the signature.

Version 2.0 will make these parameters keyword-only
([#504](https://github.com/bdperkin/findfmt/issues/504)).

### 2.2. Documented Exceptions in 1.1

1.1 changes two things that 1.0.x users can notice. Both are listed as breaking changes in the
changelog and explained in [Upgrading to findfmt 1.1](../guides/upgrading.md):

- Python 3.10 is no longer supported.
- `SortKey` and `OutputFormat` are `enum.StrEnum` subclasses, so `str()` and f-strings return a
  member's value. Member names, values, and comparisons are unchanged.

## 3. How Changes Are Caught

`tools/api_surface.py` records every public name with its kind and, where meaningful, its signature,
class members, or enumeration values. The committed snapshot `tests/unit/api_surface.json` pins that
surface, and `tests/unit/test_api_surface.py` fails when the API changes. The failure lists the
added, removed, and changed names.

To make an intentional API change:

1. Regenerate the snapshot with `uv run python tools/api_surface.py --write`.
2. Record the change in `CHANGELOG.md`, and add it to the upgrade notes if it can break callers.

## 4. API Changes in 1.1

Compared with 1.0.0, 1.1 removes no public names and adds 20, including helpers for CSV
formula-injection safety, `--exit-status`, atomic output files, and terminal cell widths. Signature
changes add only optional or keyword-only parameters, apart from the positional-order cases in §2.1.
Compared with the latest 1.0.x release (1.0.2), 1.1 adds 2 names (both for `--exit-status`) and
changes the two `StrEnum` classes, the CLI command callbacks, and `execute_findfmt` (a new
keyword-only `exit_status` parameter).
