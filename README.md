<p align="center">
  <img src="https://raw.githubusercontent.com/pikaid/pikaid-specs/v1.0.4/logo.png" alt="pikaid" width="300" />
</p>

<p align="center">
  <strong>Small · Sortable · Secure ID generator</strong>
</p>

# pikaid — Official Python Implementation

**Status: version 1.0.0 prepared, not yet published to a package index.**

This repository contains the official Python implementation of
[pikaid](https://github.com/pikaid), a compact, chronologically sortable
identifier format for databases, APIs, and distributed systems.

A pikaid is **26 lowercase Base36 characters**: a 7-character whole-second Unix
timestamp followed by 19 characters encoding exactly 96 bits of cryptographic
randomness. Its binary form is exactly **17 bytes**: a 5-byte unsigned
big-endian timestamp followed by the 12 entropy bytes unchanged. The format is
immutable and unversioned; specification revisions clarify it without changing
identifiers.

## Canonical specification

The authoritative definition is
[pikaid specification revision 1.0.4](https://github.com/pikaid/pikaid-specs/tree/v1.0.4)
(pinned at commit `17014d76f568c3ac9f9ce2927c1a018fdbc36d1d`).

Interoperability fixtures are the official
[PHP v1.2.0 vectors and schema](https://github.com/pikaid/pikaid-php/tree/v1.2.0)
(commit `e3f843edeb5157a5d2d25196cac0d69580810a95`), vendored under
`tests/vectors/`. The `pikaid-v1` filename is historical; it does not make the
identifier format versioned.

## Requirements

- Python **3.11 or newer**.
- No runtime dependencies; randomness comes from the operating system CSPRNG
  through :func:`secrets.token_bytes`.

Python 3.11 is the oldest version with the typing and standard-library
features this package targets, and it is still receiving security fixes. The
CI matrix also exercises 3.12, 3.13, and 3.14. This project has not been
verified on PyPy or on free-threaded builds.

## Installation

The package is not published yet. Install it from a checkout:

```console
python -m pip install .
```

For development:

```console
uv venv --python 3.12
uv sync --extra dev
```

## Release status and versioning

Package version **1.0.0** is the first stable version of this Python package.
The identifier format is unversioned; the package version refers only to this
implementation. It has not been published yet: no Git tag, registry upload, or
signed artifact exists. See [CHANGELOG.md](CHANGELOG.md).

## Usage

Generate an identifier for the current second:

```pycon
>>> from pikaid import generate, parse
>>> identifier = generate()
>>> len(identifier)
26
>>> identifier == identifier.lower()
True
>>> isinstance(parse(identifier).timestamp, int)
True

```

Generate with an explicit timestamp, or obtain the binary form directly:

```pycon
>>> from pikaid import generate_binary
>>> parsed = parse(generate(timestamp=1700000000))
>>> parsed.timestamp
1700000000
>>> len(generate_binary(timestamp=1700000000))
17

```

Encode, decode, and convert without loss using a deterministic value:

```pycon
>>> from pikaid import Pikaid, from_binary, to_binary
>>> known = Pikaid(timestamp=1700000000, randomness=bytes.fromhex("00112233445566778899aabb"))
>>> str(known)
'0s44we8002loz3po6mcf6vsn23'
>>> known.to_binary().hex()
'006553f10000112233445566778899aabb'
>>> known.randomness_hex
'00112233445566778899aabb'
>>> parse(str(known)) == known
True
>>> from_binary(known.to_binary()) == known
True
>>> to_binary(str(known)) == known.to_binary()
True

```

Validate strictly before trusting input:

```pycon
>>> from pikaid import is_valid, is_well_formed
>>> is_valid("00000000000000000000000000")
True
>>> is_valid("0000000000000000000000000")
False
>>> is_well_formed("0000000" + "z" * 19)
True
>>> is_valid("0000000" + "z" * 19)
False

```

`is_well_formed` checks only the length and alphabet. `is_valid` performs full
semantic validation, including the 96-bit randomness limit. Both are distinct
from parsing: `parse` raises an exception instead of returning a boolean.

Invalid input raises a subclass of `PikaidError`:

```pycon
>>> from pikaid import InvalidPikaidError, InvalidTimestampError
>>> try:
...     parse("NOT A PIKAID")
... except InvalidPikaidError:
...     print("rejected")
rejected
>>> try:
...     generate(timestamp=-1)
... except InvalidTimestampError:
...     print("rejected")
rejected

```

Comparison and sorting follow the timestamp and then the randomness bytes:

```pycon
>>> early = Pikaid(timestamp=1, randomness=bytes(12))
>>> late = Pikaid(timestamp=2, randomness=bytes(12))
>>> early < late
True
>>> str(early) < str(late)
True
>>> early.to_binary() < late.to_binary()
True

```

## Public API

The module-level functions and the `Pikaid` value type are equivalent entry
points; use whichever reads better in context. `Pikaid` is an immutable,
hashable, orderable dataclass.

| Name | Kind | Description |
| --- | --- | --- |
| `generate(timestamp=None)` | function | New identifier as 26-character `str`; defaults to the current second. |
| `generate_binary(timestamp=None)` | function | New identifier as 17 `bytes`. |
| `Pikaid.generate(timestamp=None)` | class method | New validated `Pikaid`. |
| `parse(value)` / `Pikaid.parse(value)` | function / class method | Strictly decode a string; raise `InvalidPikaidError`. |
| `from_binary(value)` / `Pikaid.from_binary(value)` | function / class method | Strictly decode 17 bytes; accept `bytes`, `bytearray`, or `memoryview`. |
| `to_binary(value)` | function | Convert a string or `Pikaid` to 17 `bytes`. |
| `is_valid(value)` | function | Full semantic validity as `bool`; never raises. |
| `is_well_formed(value)` | function | Length-and-alphabet shape check as `bool`; never raises. |
| `Pikaid.timestamp` | attribute | Unsigned whole Unix seconds, `0..78_364_164_095`. |
| `Pikaid.randomness` | attribute | Exactly 12 raw entropy `bytes`. |
| `Pikaid.randomness_hex` | property | The entropy as 24 lowercase hex characters. |
| `Pikaid.datetime` | property | Timezone-aware UTC `datetime` for the timestamp. |
| `Pikaid.to_string()` / `str(value)` | method | Canonical 26-character form. |
| `Pikaid.to_binary()` | method | Canonical 17-byte form. |

Public constants: `ALPHABET`, `STRING_LENGTH`, `TIMESTAMP_CHARS`,
`RANDOMNESS_CHARS`, `BINARY_LENGTH`, `TIMESTAMP_BYTES`, `RANDOMNESS_BYTES`,
`MAX_TIMESTAMP`, and `MAX_RANDOMNESS`.

Errors: `PikaidError` is the common base. `InvalidPikaidError` and
`InvalidTimestampError` also subclass `ValueError`; `EntropySourceError` also
subclasses `RuntimeError`.

## Ordering, security, and interoperability caveats

- **Sortable across seconds, not within one.** Lexicographic string order and
  unsigned bytewise binary order agree with `Pikaid` ordering. Identifiers
  generated in the same second are ordered by randomness, which is not
  monotonic and not related to creation time.
- **Randomness, not uniqueness.** 96 bits of CSPRNG output make collisions
  negligible in practice, but uniqueness is not guaranteed and must not be
  assumed for correctness-critical decisions.
- **Not a secret or an authentication token.** The timestamp is visible, and a
  pikaid carries no signature, MAC, or confidentiality. Do not use it as a
  bearer credential or as proof of origin.
- **Whole seconds only.** There is no sub-second precision and no monotonic
  counter. Do not use pikaid ordering as a substitute for a sequence.
- **Fail closed.** If the CSPRNG raises or returns the wrong amount of data,
  generation raises `EntropySourceError`; no identifier is produced.
- **Strict decoding.** Uppercase, whitespace, non-ASCII, wrong lengths,
  timestamps outside `0..78_364_164_095`, and randomness above `2**96 - 1` are
  rejected. Input is never trimmed, padded, or case-folded.
- **Timestamps are caller-controlled.** `generate(timestamp=...)` trusts the
  supplied value within range; it does not verify that it is the real current
  time.

`MAX_TIMESTAMP` is `36**7 - 1`, which corresponds to
`4453-04-05 15:21:35 UTC`. The `datetime` property is computed arithmetically
from the Unix epoch so it does not depend on platform `fromtimestamp` limits.

## Development and validation

```console
uv venv --python 3.12
uv sync --extra dev
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest --cov=pikaid --cov-report=term-missing
```

The test suite runs every official vector, checks the fixture checksums and
schema, and adds a pinned cross-representation conformance matrix: independent
known-answer, malformed-input, overflow, boundary, zero-padding, property-based
round-trip, ordering, generated-value, and CSPRNG-failure tests.
`tests/test_readme.py` executes the README examples, and CI enforces 100% line
and branch coverage on every matrix entry.

### Official conformance suite

`tests/official/` contains a test-only JSON-Lines adapter and a fail-closed
driver for the official cross-language suite, pinned to the immutable
`pikaid-specs` commit `059780cc0e5b113443812720d95c630649bf3aa3` (suite `1.0.0`,
specification `1.0.4`). See [`tests/official/README.md`](tests/official/README.md).

The suite's `--automated-only` exit `0` means the automated checks passed. It is
**not** a conformance certification: `P-GENERATE-RNG-SOURCE` and
`P-GENERATE-RNG-FAILURE` remain manual human-audit items, and the suite's
default exit `3` means that audit is still outstanding.

## License

MIT. See [LICENSE](LICENSE).

Copyright (c) 2026 larananas (Lara G.).
