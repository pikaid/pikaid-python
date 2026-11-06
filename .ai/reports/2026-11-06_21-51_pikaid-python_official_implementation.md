# pikaid-python — Official Python Implementation

**Repository:** `pikaid/pikaid-python` (`origin https://github.com/pikaid/pikaid-python.git`, branch `main`)
**Specification:** pikaid spec revision 1.0.4, commit `17014d76f568c3ac9f9ce2927c1a018fdbc36d1d` (normative)
**Interoperability fixtures:** pikaid-php v1.2.0, commit `e3f843edeb5157a5d2d25196cac0d69580810a95`
**Report date:** 2026-11-06 21:51 (local)
**Package version:** 0.1.0 (not published)

## Summary

The repository contained only a README before this task (single commit `994ed35`,
`docs: initialize official Python implementation README`): no package source, tests,
packaging metadata, or CI. This work delivers the official Python implementation of
pikaid as a zero-dependency, strictly typed library targeting Python 3.11+.

The implementation provides:

- Canonical 26-character lowercase Base36 string encoding: 7 timestamp characters and
  19 randomness characters representing exactly 96 bits.
- Canonical 17-byte binary encoding: 5-byte unsigned big-endian timestamp followed by the
  12 entropy bytes unchanged.
- CSPRNG-backed generation through `secrets.token_bytes(12)`, failing closed with
  `EntropySourceError` when the source raises or returns the wrong amount of data.
- Strict decoding and full semantic validation with no trimming, padding, case folding,
  truncation, or lossy coercion.
- An immutable, hashable, ordered `Pikaid` value object plus equivalent module-level
  functions, properties for timestamp/datetime/randomness, and lossless round trips in
  both directions.
- A 220-test suite covering every official vector, the Draft 2020-12 schema, pinned
  fixture checksums, independent known-answer values, malformed and overflow input,
  boundary and zero-padding cases, property-based round trips and ordering, generated
  identifiers, CSPRNG failure injection, and executable README examples.
- Packaging (`pyproject.toml`, Hatchling, sdist + wheel), MIT `LICENSE`, `py.typed`,
  a comprehensive README, and a GitHub Actions workflow with lint/type, cross-platform
  test, and distribution-build jobs.

All locally runnable checks pass: 220 tests on Python 3.11, 3.12, 3.13, and 3.14; 100%
statement and branch coverage; Ruff formatting and lint; strict mypy; sdist/wheel build;
`twine check`; and a clean-virtualenv wheel install and functional smoke test.
GitHub-hosted execution of the workflow and non-macOS runners were not available locally
and are reported as `NOT RUN`.

No commit, tag, push, or registry publication was performed. The working tree contains
the new implementation, tests, packaging, and documentation for review.

## Requirement Coverage

### REQ-1 — Identifier format and binary layout

- Exactly 26 lowercase Base36 characters are enforced by `STRING_LENGTH` and by
  `_validate_string_shape`, which rejects any wrong length or character outside
  `0-9a-z`.
- The first 7 characters are decoded as a whole-second Unix timestamp with
  `TIMESTAMP_CHARS = 7` and `MAX_TIMESTAMP = 36**7 - 1 = 78_364_164_095`.
- The remaining 19 characters encode `RANDOMNESS_CHARS = 19`, constrained to
  `0 <= randomness <= 2**96 - 1`; `MAX_RANDOMNESS = 2**96 - 1`.
- The binary form is exactly 17 bytes: `TIMESTAMP_BYTES = 5` big-endian timestamp bytes
  plus `RANDOMNESS_BYTES = 12` entropy bytes copied unchanged.
- Encoding emits Base36 digits with `divmod` and left-pads with `rjust(width, "0")`, so
  leading zeros are preserved (`timestamp=0` encodes as `0000000`).
- Round trips are lossless in both directions and covered by known-answer tests and
  Hypothesis properties.
- Evidence: `src/pikaid/_core.py` (`_encode_base36`, `_decode_base36`,
  `_validate_string_shape`, `to_binary`, `from_binary`), `tests/test_format.py`,
  `tests/test_properties.py`, `tests/test_vectors.py`.

**Status: implemented and verified.**

### REQ-2 — Secure randomness, timestamp handling, fail-closed behavior

- Entropy is obtained exclusively from `secrets.token_bytes(RANDOMNESS_BYTES)`.
- `_random_bytes` validates that the source returned `bytes` of exactly 12 bytes and
  wraps any source exception or malformed output in `EntropySourceError`; no identifier
  is returned on failure.
- `generate` and `generate_binary` accept an optional explicit timestamp; when omitted,
  `_now_seconds` returns `time.time_ns() // 1_000_000_000`, i.e. whole Unix seconds.
- Supplied timestamps are validated for type and range and are not claimed to reflect
  real time.
- The README explicitly avoids uniqueness, secrecy, authentication, and monotonicity
  claims, and states that collisions are negligible but not impossible.
- Evidence: `src/pikaid/_core.py` (`_random_bytes`, `_now_seconds`, `generate`,
  `generate_binary`), `tests/test_generation.py`, `tests/test_api.py`,
  `tests/test_readme.py`.

**Status: implemented and verified, including injected source failure and short/incorrect
return types.**

### REQ-3 — Strict decoding and validation

- `parse` and `Pikaid.parse` require `str`; non-strings raise `TypeError`.
- `from_binary` requires `bytes`, `bytearray`, or `memoryview`; everything else raises
  `TypeError`.
- Wrong string length, uppercase, whitespace, non-ASCII, surrogate characters, wrong
  binary length, and timestamps above the maximum are rejected with
  `InvalidPikaidError` or `InvalidTimestampError`.
- Randomness above `2**96 - 1` cannot be represented in 19 Base36 characters for the
  permitted timestamp range; `is_valid` nevertheless enforces the explicit numeric limit,
  and `Pikaid` construction validates the 12-byte randomness value.
- No input is normalized: there is no `.strip()`, `.lower()`, padding, truncation, or
  lossy coercion on any decode path.
- `is_well_formed` performs only the length/alphabet shape check. `is_valid` performs
  the full semantic check, including timestamp range and randomness bound. Both return
  real booleans and do not raise for arbitrary input.
- Evidence: `src/pikaid/_core.py`, `tests/test_validation.py`,
  `tests/test_vectors.py::test_invalid_string_vector_is_rejected` and
  `test_invalid_binary_vector_is_rejected`.

**Status: implemented and verified.**

### REQ-4 — Lossless conversions, extraction, and ordering

- `to_string`/`str`, `to_binary`, `parse`, and `from_binary` are mutually lossless;
  this is asserted for official vectors, known answers, and generated values.
- `Pikaid.timestamp`, `Pikaid.randomness`, `Pikaid.randomness_hex`, and
  `Pikaid.datetime` expose the parsed components without re-encoding ambiguity.
- `Pikaid` is an ordered dataclass: ordering follows timestamp first, then the raw
  12-byte randomness, matching lexicographic string order and unsigned bytewise binary
  order across seconds.
- Within one second, order is determined by randomness and is explicitly documented as
  not monotonic and not related to creation time.
- `datetime` is computed as `datetime(1970, 1, 1, tzinfo=UTC) + timedelta(seconds=...)`,
  avoiding platform `datetime.fromtimestamp` limits at the maximum timestamp
  (`4453-04-05 15:21:35 UTC`).
- Evidence: `src/pikaid/_core.py` (`Pikaid`, `__post_init__`, `datetime`),
  `tests/test_api.py`, `tests/test_format.py`, `tests/test_properties.py`.

**Status: implemented and verified.**

### REQ-5 — Idiomatic typed Python API

The public API is exported from `pikaid` and typed with `py.typed`:

- `generate(timestamp: int | None = None) -> str`
- `generate_binary(timestamp: int | None = None) -> bytes`
- `parse(value: str) -> Pikaid`
- `from_binary(value: bytes | bytearray | memoryview) -> Pikaid`
- `to_binary(value: str | Pikaid) -> bytes`
- `is_valid(value: object) -> bool`
- `is_well_formed(value: object) -> bool`
- `Pikaid.generate`, `Pikaid.parse`, `Pikaid.from_binary`, `Pikaid.to_string`,
  `Pikaid.to_binary`
- Properties `Pikaid.timestamp`, `Pikaid.randomness`, `Pikaid.randomness_hex`,
  `Pikaid.datetime`
- Constants `ALPHABET`, `STRING_LENGTH`, `TIMESTAMP_CHARS`, `RANDOMNESS_CHARS`,
  `BINARY_LENGTH`, `TIMESTAMP_BYTES`, `RANDOMNESS_BYTES`, `MAX_TIMESTAMP`,
  `MAX_RANDOMNESS`
- Errors `PikaidError`, `InvalidPikaidError`, `InvalidTimestampError`,
  `EntropySourceError`

The value object supports equality, hashing, ordering, pickling, `repr`, and `str`.
`tests/test_api.py` asserts the exact `__all__`, star-import surface, signatures through
behavior, metadata version agreement, and value semantics.

**Status: implemented and verified.**

### REQ-6 — Test coverage and evidence

- All official fixtures are executed: 4 valid vectors, 6 invalid string vectors, and
  4 invalid binary vectors, plus Draft 2020-12 schema validation and SHA-256 pinning of
  both vendored files.
- Independent tests cover known-answer values from the specification, zero padding,
  maximum values, malformed strings and binaries, overflow, non-ASCII and surrogate
  input, `bool` versus `int` timestamp handling, binary type handling, CSPRNG failure and
  malformed source output, ordering, lossless round trips, and generated identifiers.
- Hypothesis property tests exercise string and binary round trips, parse/serialize
  agreement, and ordering consistency.
- README examples are executed by `tests/test_readme.py`.
- Final result: **220 tests passed**, **100% statement and branch coverage**
  (`153 statements`, `46 branches`, `0 missed`, `fail_under = 90`).
- Test modules: `test_vectors.py` (17), `test_format.py` (38),
  `test_generation.py` (27), `test_validation.py` (113), `test_properties.py` (4),
  `test_api.py` (18), and `test_readme.py` (3). These are the runtime collection counts
  and sum to 220.
- No test is a tautology over the implementation: expected values come from the
  specification, official vectors, or independent arithmetic oracles.

**Status: implemented and verified. Coverage exceeds the 90% target even without the
coverage threshold assertion.**

### REQ-7 — Installable package, metadata, license, README

- `pyproject.toml` defines the `pikaid` distribution, version `0.1.0`, MIT license,
  `requires-python = ">=3.11"`, classifiers for 3.11–3.14, `Typing :: Typed`, zero
  runtime dependencies, and a Hatchling build backend.
- The sdist includes source, tests, README, LICENSE, and `pyproject.toml`; the wheel
  contains the four `pikaid` package files (`__init__.py`, `_core.py`, `errors.py`,
  `py.typed`) plus standard `dist-info` metadata.
- `LICENSE` is MIT, copyright 2026 larananas (Lara G.).
- `README.md` preserves the pikaid brand and the “Small · Sortable · Secure ID
  generator” tagline, states clearly that the package is not yet published, explains the
  Python version rationale, documents installation from source, documents every public
  API entry, and records accurate ordering, uniqueness, secrecy, precision, and
  timestamp-trust caveats.
- README examples are deterministic or assert only stable properties, and are executed
  as tests.
- No publication, upload, or release claim is made.

**Status: implemented and verified.**

### REQ-8 — Continuous integration

`.github/workflows/ci.yml` defines three jobs:

1. **Lint, types, documentation** on Ubuntu with Python 3.12: Ruff format check, Ruff
   lint, strict mypy, and README tests.
2. **Test** matrix with 8 entries: Ubuntu 3.11, 3.12, 3.13, 3.14; macOS 3.11 and 3.14;
   Windows 3.11 and 3.14. Each runs the full suite with coverage.
3. **Package** on Ubuntu with Python 3.12: build sdist and wheel, `twine check`, install
   the wheel in a clean virtual environment, and run a functional smoke test.

The workflow uses `actions/checkout@v4` and `actions/setup-python@v5`, read-only
`contents` permission, per-job timeouts, and `fail-fast: false`. It contains no
platform-specific shell syntax; the clean-environment step uses `clean-venv/bin/python`
on Ubuntu only.

The workflow was parsed successfully with PyYAML: jobs `lint`, `test`, `package`, 8 test
matrix entries, and step counts 7/4/6. Every command used by the workflow was run
locally on macOS equivalents. GitHub-hosted execution and the Linux/Windows runners were
not available and are marked `NOT RUN`.

**Status: implemented; local command equivalents verified; hosted execution NOT RUN.**

### REQ-9 — Scope, safety, and non-destructive execution

- Changes are limited to the package source, tests, fixtures, packaging, license,
  README, CI, and `.gitignore` in `pikaid/pikaid-python`.
- No unrelated rewrite, infrastructure change, credential, secret, or destructive Git
  operation was introduced.
- No commit, tag, push, force-push, release, or registry publication was performed.
- `.ai/` (audit material and this report) is untracked and excluded from the package
  artifacts by the Hatchling include list.
- `.DS_Store` remains untracked and untouched.

**Status: implemented and verified.**

## Root Cause / Technical Approach

The starting repository was a scaffold: the package directory existed but contained no
implementation, and there was no test or packaging infrastructure. The task was therefore
a greenfield implementation inside an existing, correctly identified repository rather
than a defect fix.

Technical approach:

1. **Normative anchoring.** The specification revision 1.0.4 was downloaded and read
   from the pinned commit; the official PHP v1.2.0 vectors, schema, and behavior were
   used only as independent interoperability evidence. Audit copies are under `.ai/audit/`
   and are not part of the package.
2. **Representation.** A single `Pikaid` dataclass stores a validated integer timestamp
   and exactly 12 raw entropy bytes. Both encodings are derived from those two fields,
   which makes the string and binary forms provably consistent and eliminates duplicated
   parsing logic.
3. **Encoding.** Base36 is implemented with explicit digit loops and zero padding rather
   than `str.format` or `int` string conversion, keeping leading zeros and rejecting any
   character outside the canonical alphabet before arithmetic.
4. **Strictness.** Public decode entry points validate type and shape first, then decode,
   then enforce range in one shared `_ensure_timestamp` path. Boolean timestamps are
   rejected explicitly even though `bool` is an `int` subclass.
5. **Entropy.** A private `_random_bytes` function isolates `secrets.token_bytes`,
   validates its output, and converts failures to `EntropySourceError`. Tests monkeypatch
   `secrets.token_bytes` to simulate source failure and malformed output.
6. **Time.** Current time is `time.time_ns() // 1_000_000_000`; `datetime` uses epoch
   arithmetic instead of `fromtimestamp` so the maximum timestamp is representable on all
   platforms.
7. **Validation split.** `is_well_formed` and `is_valid` are intentionally distinct:
   shape-only versus full semantic validity. This matches the requirement to distinguish
   them and gives callers a cheap pre-check without implying semantic validity.
8. **Interoperability.** Official vectors are vendored byte-for-byte, pinned by SHA-256,
   and validated against the official Draft 2020-12 schema before being used as oracles.
9. **Packaging and CI.** A `src/` layout with Hatchling produces a clean wheel and an
   sdist containing tests. CI mirrors every local check and adds an isolated wheel
   install to catch packaging-only failures.

No translation of PHP code was performed; the PHP implementation was consulted only to
confirm behavior at ambiguous boundaries such as binary overflow and invalid-character
handling.

## Files Changed

New files:

- `src/pikaid/__init__.py` — public exports, `__all__`, `__version__`.
- `src/pikaid/_core.py` — constants, Base36 codec, validation, generation, `Pikaid`.
- `src/pikaid/errors.py` — exception hierarchy.
- `src/pikaid/py.typed` — PEP 561 marker.
- `tests/__init__.py` — test package marker.
- `tests/support.py` — shared deterministic helpers.
- `tests/test_vectors.py` — official vectors, schema, checksum pinning.
- `tests/test_format.py` — encoding, binary layout, extraction, round trips.
- `tests/test_validation.py` — strict rejection, boundaries, types, overflow.
- `tests/test_generation.py` — generation, timestamps, CSPRNG failure injection.
- `tests/test_properties.py` — Hypothesis round-trip and ordering properties.
- `tests/test_api.py` — public surface, value semantics, metadata version.
- `tests/test_readme.py` — executable README examples and documentation claims.
- `tests/vectors/pikaid-v1.json` — official valid/invalid vectors (unmodified).
- `tests/vectors/pikaid-v1.schema.json` — official Draft 2020-12 schema (unmodified).
- `tests/vectors/README.md` — provenance, pinned commit, SHA-256 checksums.
- `pyproject.toml` — build system, metadata, dev dependencies, tool configuration.
- `LICENSE` — MIT license.
- `.gitignore` — virtual environments, build output, caches, `.ai/run/`.
- `.github/workflows/ci.yml` — lint/type, 8-entry test matrix, package job.
- `uv.lock` — resolved development environment lockfile.

Modified files:

- `README.md` — replaced the placeholder with the full implementation documentation
  (usage, API table, caveats, specification and fixture pins, development commands).

Not included in the deliverable:

- `.ai/audit/` — downloaded specification and PHP reference material for traceability.
- `.ai/reports/` — this report.
- `.DS_Store` — pre-existing untracked macOS metadata, left untouched.

## Validation

Environment: macOS (darwin), CPython 3.12.11 primary; additional environments CPython
3.11, 3.13, and 3.14. Commands were run from `/Users/lara/Dev/projects/pikaid-python`.

| Check | Command | Result |
| --- | --- | --- |
| Formatting | `uv run ruff format --check .` | `PASS` — 16 files already formatted |
| Linting | `uv run ruff check .` | `PASS` — all checks passed |
| Static typing | `uv run mypy src` | `PASS` — no issues in 3 source files (strict, `warn_unreachable`) |
| Test suite and coverage (3.12) | `uv run pytest --cov=pikaid --cov-report=term-missing` | `PASS` — 220 passed; 100% statements and branches (153 stmts, 46 branches) |
| Test suite (3.11) | `.venv-3.11/bin/python -m pytest -q` | `PASS` — 220 passed |
| Test suite (3.13) | `.venv-3.13/bin/python -m pytest -q` | `PASS` — 220 passed |
| Test suite (3.14) | `.venv-3.14/bin/python -m pytest -q` | `PASS` — 220 passed |
| Build | `uv run python -m build` | `PASS` — `pikaid-0.1.0.tar.gz` and `pikaid-0.1.0-py3-none-any.whl` |
| Distribution metadata | `uv run twine check dist/*` | `PASS` — both artifacts PASSED |
| Wheel install smoke test | clean venv, `uv pip install dist/pikaid-0.1.0-py3-none-any.whl`, functional assertions | `PASS` — version 0.1.0, Python 3.12.11, imports from `site-packages`, known answer and round trip correct |
| Workflow syntax and structure | PyYAML parse of `.github/workflows/ci.yml` | `PASS` — 3 jobs, 8 matrix entries, expected step counts |
| Official vectors and schema | `uv run pytest tests/test_vectors.py` | `PASS` — 17 tests, all vectors and schema, checksums pinned |
| README examples | `uv run pytest tests/test_readme.py` | `PASS` — 3 tests, doctests executed |
| GitHub Actions hosted run | `gh workflow run` / push-triggered run | `NOT RUN` — no commit or push was authorized; hosted runners unavailable locally |
| Linux (Ubuntu) execution | CI matrix runner | `NOT RUN` — no Linux host available; commands verified only on macOS |
| Windows execution | CI matrix runner | `NOT RUN` — no Windows host available; commands verified only on macOS |
| Independent subagent review | review subagent | `NOT RUN` — agent model unavailable (`Model unavailable: profile/small`); no repeated retries |

Fixture integrity:

- `pikaid-v1.json` SHA-256:
  `b0c9dfdd063613424414fef5c9065fbd2f81d645d0ab42b34e27cde715613500`
- `pikaid-v1.schema.json` SHA-256:
  `4441d4dbaa6c5450ae9cbfb2438c53bc0421bba2b7fcc9ef9b158e5d1de0759e`

These checksums are asserted by `tests/test_vectors.py` and documented in
`tests/vectors/README.md`.

## Deviations and Unresolved Issues

- **No hosted CI execution.** The workflow is complete and locally equivalent commands
  pass, but no GitHub Actions run occurred because committing or pushing was outside the
  authorized scope and no remote run was requested. This is reported as `NOT RUN`, not as
  a pass.
- **No Linux or Windows execution.** The matrix declares those runners, but validation
  was performed only on macOS. Platform-specific behavior is therefore unproven by
  execution, though the implementation uses only portable standard-library APIs.
- **No independent subagent review.** The review subagent could not start because its
  model was unavailable. The review is not claimed; the implementation was self-reviewed
  and validated through tests, linting, typing, and packaging checks.
- **Package is not published.** This is intentional and explicitly stated in the README.
  No PyPI metadata, credentials, or upload steps were added.
- **Coverage threshold versus actual coverage.** The configured minimum is 90%; the
  measured result is 100%. The report states the measured result, not the threshold.
- **`uv.lock` is included.** It was generated by resolving the declared development
  dependencies and pins the local validation environment. It is not required at runtime;
  consumers installing the wheel or sdist do not depend on it.
- **Report delivery is separate from task status.** The authoritative report is written
  under `.ai/reports/`; an identical copy is published to the mounted
  `Tohru Drive/pikaid-python/reports/` directory and verified by checksum. Mount-level
  file equality does not by itself prove cloud synchronization, and any delivery failure
  is reported separately from `task_result`.
- No unresolved functional defect is known.

## Final Status

task_result: PASS

All nine requirements are implemented and locally verified. The only non-passing checks
are explicitly unavailable execution environments (GitHub-hosted CI, Linux, Windows, and
an independent subagent review), which are reported as `NOT RUN` with reasons and are not
counted as successes. No commit, push, tag, release, or publication was performed.
