<p align="center">
  <a href="https://github.com/pikaid/pikaid-specs">
    <img src="https://raw.githubusercontent.com/pikaid/pikaid-specs/v1.0.4/logo.png" alt="pikaid" width="300">
  </a>
</p>

<p align="center">
  <strong>Small · Sortable · Secure ID generator</strong>
</p>

<div align="center">

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/language-Python-3776AB.svg)](https://github.com/pikaid/pikaid-python)
[![CI](https://github.com/pikaid/pikaid-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/pikaid/pikaid-python/actions/workflows/ci.yml)
[![Official implementation](https://img.shields.io/badge/official-implementation-2e7d32.svg)](https://github.com/pikaid/pikaid-specs)
[![Specification 1.0.4](https://img.shields.io/badge/spec-1.0.4-4b56a6.svg)](https://github.com/pikaid/pikaid-specs/tree/v1.0.4)

</div>

**pikaid** is the **official Python implementation** of a compact, chronologically sortable, collision-resistant identifier format for databases, APIs, and distributed systems.

This is the immutable, unversioned [pikaid format](https://github.com/pikaid/pikaid-specs/tree/v1.0.4), documented in specification revision **1.0.4**.

## ✨ Why pikaid?

- **Short:** Compact, readable IDs for URLs, logs, and API resources.
- **Sortable:** Lexicographically ordered by timestamp, with **one-second precision**.
- **Collision-resistant:** 96 bits of cryptographic randomness make collisions extremely unlikely, never impossible.
- **Storage-friendly:** Use `BINARY(17)` or readable `CHAR(26)`.
- **Distributed-friendly:** No central sequence generator or coordination required.

## 🧬 Identifier format

A pikaid contains **26 lowercase Base36 characters**: a **7-character Unix-seconds timestamp** followed by **19 characters encoding 96 bits of cryptographic randomness**. Its binary form is **17 bytes**: 5 unsigned big-endian timestamp bytes followed by 12 randomness bytes.

![Identifier structure](https://raw.githubusercontent.com/pikaid/pikaid-specs/v1.0.4/structure.svg)

> **Ordering:** Different seconds sort chronologically. Within the same second, randomness—not issuance order—decides the order.

> **Security:** These are identifiers, **not secrets**, session credentials, authentication tokens, or API keys.

## ⚙️ Requirements

- Python **3.11 or newer**.
- No runtime dependencies; randomness comes from the operating system CSPRNG
  through :func:`secrets.token_bytes`.

Python 3.11 is the oldest version with the typing and standard-library
features this package targets, and it is still receiving security fixes.
CI verifies supported CPython versions on Linux, macOS, and Windows; PyPy and free-threaded builds are not claimed.

## 📦 Installation

The package is not yet on PyPI. Install it from this public source repository:

```sh
git clone https://github.com/pikaid/pikaid-python.git
cd pikaid-python
python -m pip install .
```

For development and tests, use `python -m pip install -e '.[dev]'` from the checkout.

## 🚀 Basic Usage

Copy and run the complete example below (for example, save it as `demo.py` and execute `python demo.py`):

```python
from pikaid import generate, parse, to_binary, from_binary, is_valid

identifier = generate()
assert is_valid(identifier)
parsed = parse(identifier)
binary = to_binary(identifier)
assert len(identifier) == 26 and len(binary) == 17
assert from_binary(binary) == identifier
print(identifier, parsed.timestamp)
```

## 💡 Example Use Case

Use pikaid to identify **users, orders, invoices, uploads, events, and API resources**. Independent services can generate compact IDs without a shared counter, while timestamp-based ordering helps with indexing, sorting, and logs.

## 📚 Canonical specification

- [Canonical specification](https://github.com/pikaid/pikaid-specs)
- [Revision 1.0.4](https://github.com/pikaid/pikaid-specs/tree/v1.0.4)

Specification revisions describe the format; they do not change the encoded identifiers.

## 🧩 API Reference

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

## 🔄 Order Guarantee

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

## 🛢 Storage Recommendations

| Representation | Size | Recommended for |
| --- | ---: | --- |
| **BINARY(17)** | 17 bytes | Compact primary keys and indexes |
| **CHAR(26)** | 26 characters | Readable SQL, debugging, URLs, and logs |

Use an **ASCII bytewise/binary collation** for text columns (for example, `ascii_bin` on MariaDB/MySQL). Case-insensitive or locale-aware sorting is not a substitute for canonical bytewise comparison.

## ✅ Verification and release status

The [CI workflow](https://github.com/pikaid/pikaid-python/actions/workflows/ci.yml) runs native tests, pinned automated conformance checks, and language-specific quality gates. To run the native checks locally from a checkout, use `python -m pytest` after installing the development extras.

**Automated passing tests are not a security certification.** The independent CSPRNG source and failure-path audits (`P-GENERATE-RNG-SOURCE` and `P-GENERATE-RNG-FAILURE`) still require separate human evidence.

<details>
<summary>Platform, tooling, and conformance details</summary>

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
`tests/test_readme.py` executes the README examples, and the test command
enforces 100% line and branch coverage; the CI workflow applies the same gate
to every matrix entry when hosted runners are available.

### Official conformance suite

`tests/official/` contains a test-only JSON-Lines adapter and a fail-closed
driver for the official cross-language suite, pinned to the immutable
`pikaid-specs` commit `059780cc0e5b113443812720d95c630649bf3aa3` (suite `1.0.0`,
specification `1.0.4`). See [`tests/official/README.md`](tests/official/README.md).

The suite's `--automated-only` exit `0` means the automated checks passed. It is
**not** a conformance certification: `P-GENERATE-RNG-SOURCE` and
`P-GENERATE-RNG-FAILURE` remain manual human-audit items, and the suite's
default exit `3` means that audit is still outstanding.

</details>

Registry publication is not implied by a green CI: use the installation method documented above.

## 🤝 Contributing

Contributions are always welcome! 💙

Whether you're fixing a typo, improving documentation, adding tests, or making pikaid even better, every contribution is appreciated.

**Want to help? Here's how:**

- 🐛 **Found a bug?** [Open an issue](https://github.com/pikaid/pikaid-python/issues) with clear reproduction steps.
- 💡 **Have an idea?** Start with an issue before making major changes.
- 🛠️ **Ready to contribute?** Open a pull request explaining your changes.
- 🧪 **Keep it tested.** Add meaningful regression tests for behavior changes and follow the existing conventions.
- ✅ **Make sure CI passes.** All required checks must be green before a pull request is merged. No shortcuts!

**One important rule:** pikaid's identifier format is immutable. Contributions must preserve the [canonical specification (revision 1.0.4)](https://github.com/pikaid/pikaid-specs/tree/v1.0.4).

🔐 **Found a security vulnerability?** Report it privately using GitHub's security reporting (when available), or [contact the maintainer](mailto:larananas.dev@proton.me)—not through a public issue.

**Every improvement matters, big or small. Thanks for helping make pikaid better!** 🐇

## 📄 License

The implementation is available under the [MIT License](LICENSE).

## ✉️ Contact

For licensing or project-related questions: [larananas.dev@proton.me](mailto:larananas.dev@proton.me).

