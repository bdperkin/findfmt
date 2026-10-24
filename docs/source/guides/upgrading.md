# Upgrading to findfmt 1.1

`findfmt` 1.1 is a minor release with a few intentional, visible changes since 1.0.x. Most users
only need to check the Python version they run on. If you parse `findfmt` output, call it from
scripts, or use the Python API, read the sections that apply to you.

## 1. Summary of Changes

| Change                                                                                 | Who is affected                                      | What to do                                                      |
| :------------------------------------------------------------------------------------- | :--------------------------------------------------- | :-------------------------------------------------------------- |
| Python 3.10 support dropped; the minimum is Python 3.11 (#441)                         | Users and CI jobs on Python 3.10                     | Upgrade Python, or pin `findfmt<1.1`                            |
| Human-readable sizes use IEC binary unit labels (`KiB`, `MiB`) (#352)                  | Anyone parsing sizes from output                     | Update parsers; the values are unchanged                        |
| `SortKey` and `OutputFormat` render as their value in `str()` and f-strings (#441)     | Python API users who turn these members into strings | Use the member or `.value`; comparisons with strings still work |
| Wrapper commands exit with status 1 when an error carries a message (#373)             | Scripts that run the wrapper commands                | Treat a non-zero status as failure                              |
| New `--exit-status` option: exit with status 1 when nothing matches (#367)             | Shell scripts (opt-in)                               | Optional                                                        |
| Python 3.15 is supported and tested; the container image runs Python 3.14 (#335, #440) | Everyone                                             | No action needed                                                |

## 2. Python 3.10 Is No Longer Supported

Python 3.10 reached end of life on 2026-10-01. `findfmt` 1.1 requires Python 3.11 or newer and is
tested on Python 3.11 through 3.15 on Linux, macOS, and Windows (#441).

On Python 3.10, installers keep selecting the latest compatible 1.0.x release, because 1.1 declares
`requires-python = ">=3.11"`. To make that explicit, pin the 1.0 series:

```bash
pip install "findfmt<1.1"
uv add "findfmt<1.1"
```

Only the latest release receives fixes (see the
[security policy](https://github.com/bdperkin/findfmt/blob/main/SECURITY.md)), so upgrade Python
when you can. See the [compatibility guide](../quality/compatibility.md) for the full support
policy.

## 3. Human-Readable Sizes Use IEC Binary Units

Sizes are calculated in powers of 1024, and the labels now say so (#352). The numbers are unchanged;
only the unit labels differ.

On the command line, `-h` / `--human-readable` output changes from single-letter units to IEC
labels:

```text
# findfmt 1.0.x
[1.5 K] a.bin
[2.9 M] b.bin

# findfmt 1.1
[1.5 KiB] a.bin
[2.9 MiB] b.bin
```

In the Python API, `findfmt.sizes.format_size()` changes from `KB`/`MB` to `KiB`/`MiB`, matching
`format_size_binary()`:

```python
from findfmt.sizes import format_size

format_size(1536)  # 1.0.x: "1.5 KB"   1.1: "1.5 KiB"
```

If you parse sizes with a regular expression, accept the new labels, for example
`(\d+(?:\.\d+)?) ?([KMGTP]i?B?|B)`.

## 4. `SortKey` and `OutputFormat` Render as Their Value

`findfmt.SortKey` and `findfmt.OutputFormat` are now `enum.StrEnum` subclasses (#441). As a result,
`str()`, `format()`, f-strings, and `%s` formatting return the member's value instead of the
class-qualified name:

```python
from findfmt import OutputFormat, SortKey

str(SortKey.SIZE)  # 1.0.x: "SortKey.SIZE"   1.1: "size"
f"{OutputFormat.JSON}"  # 1.0.x: "OutputFormat.JSON"   1.1: "json"
```

Comparisons with strings, hashing, `repr()`, JSON output, CLI help, and configuration handling are
unchanged, so `SortKey.SIZE == "size"` is still true. If you relied on the old text, build it
explicitly: `f"{type(member).__name__}.{member.name}"`.

## 5. Wrapper Commands Exit Non-Zero on Errors

The wrapper commands (`findfiles`, `findfilefmt`, `findfilemime`, `findfmt0`, `findshebang`, and
`findsummary`) now exit with status 1 when they stop with an error that carries a message instead of
a numeric status (#373). Previously they exited with status 0 in that case, hiding the failure. The
`findfmt` command itself is not affected, and normal runs still exit with status 0.

If a script ran a wrapper command and ignored its exit status, treat a non-zero status as a failure.

## 6. New: `--exit-status` for Scripts

`findfmt` still exits with status 0 when nothing matches. Pass the new `--exit-status` option to get
`grep`-style behavior, where no matches means exit status 1 (#367):

```bash
if findfmt --exit-status -t python src/ > /dev/null; then
  echo "Python files found"
fi
```

## 7. Platform Support

Python 3.15 is now fully supported and required to pass CI on Linux, macOS, and Windows, and the
container image (`ghcr.io/bdperkin/findfmt`) runs on Python 3.14 (#335, #440). No action is needed.
For everything else in this release, see the
[changelog](https://github.com/bdperkin/findfmt/blob/main/CHANGELOG.md).
