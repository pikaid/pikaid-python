# pikaid-python — Final Release-Readiness Hardening

**Repository:** `pikaid/pikaid-python` (`origin https://github.com/pikaid/pikaid-python.git`)
**Audited commit:** `a8627191cfb711ebafa907124d315005f06d738b` (branch `hardening/final-release-readiness`)
**Baseline commit:** `59eb2581fc5fa1ba3617cf4478ab987b935dc5af` (`main`)
**Pull request:** <https://github.com/pikaid/pikaid-python/pull/1> (open, not merged)
**Remote CI on audited commit:** <https://github.com/pikaid/pikaid-python/actions/runs/42339421932> — **success**, 10/10 checks
**Specification:** pikaid spec revision 1.0.4, commit `17014d76f568c3ac9f9ce2927c1a018fdbc36d1d` (normative, unchanged)
**Interoperability oracle:** pikaid-php v1.2.0, commit `e3f843edeb5157a5d2d25196cac0d69580810a95`
**Report date:** 2026-11-07 05:41 CET
**Package version:** 0.1.0 (not published; no tag, no registry upload, no credential use)

## Summary

This pass audited the existing implementation, its tests, its GitHub Actions workflow and
the previous report, reproduced the one real remote failure, fixed it, and re-verified the
repository end to end. It delivered three changes on one branch, in two commits:

1. **The actual defect (remote CI).** `main` was red: run
   [42337039049](https://github.com/pikaid/pikaid-python/actions/runs/42337039049) failed on
   `windows-latest` for Python 3.11 and 3.14, in exactly one test,
   `tests/test_vectors.py::test_vector_fixtures_are_pinned` (1 failed, 219 passed per job).
   Windows checks the repository out with `core.autocrlf=true`, which rewrote the vendored
   LF fixtures to CRLF, so their SHA-256 no longer matched the pinned value. A new
   `.gitattributes` enforces LF for all text files and explicitly for the byte-pinned
   fixtures. The hash assertions and the fixture bytes were not touched — the fix makes the
   platform deliver the canonical bytes the test already required.
2. **Two audit findings, both non-functional.** `.ai/audit/pikaid-v1.json` and
   `.ai/audit/pikaid-v1.schema.json` were byte-identical duplicates of the canonical
   checksum-pinned fixtures in `tests/vectors/` (proven with `cmp`), a silent drift hazard;
   they were removed and provenance is now documented in `.ai/audit/README.md`. A stale
   `# pragma: no cover` on the CSPRNG failure path in `src/pikaid/_core.py` excluded
   genuinely executed code from the coverage report; it was removed, so the reported
   coverage is now honest.
3. **Independent verification**, not just self-consistency: a PHP v1.2.0 conformance oracle
   (1018 checks, 0 failures) generated 208 boundary and deterministic pseudo-random cases
   that were then re-checked against this Python implementation, together with 500 binary
   mutations, 500 string mutations, and type/boundary assertions (0 failures).

Final state: 220 tests pass on Python 3.11, 3.12, 3.13 and 3.14 locally; 100% statement and
branch coverage (155 statements, 46 branches, 0 missed); Ruff format and lint clean; strict
mypy clean; wheel and sdist build reproducibly; `twine check` passes; a clean-virtualenv
consumer smoke test passes. On GitHub, all 10 checks — including both Windows jobs — are
green on the audited commit, with 220 passed and 100% coverage in the Windows logs.

No API, format, error semantics, fixture, test vector, coverage threshold, CI matrix entry,
OS target or runtime was changed or weakened. `main` itself is still red at `59eb258` until
PR #1 is merged; merging was outside the authorized scope and was deliberately not done.

## Requirement Coverage

### REQ-1 — Repository scope and non-destructive execution

- All changes are confined to `pikaid/pikaid-python`: one new `.gitattributes`, one new
  `.ai/audit/README.md`, two deleted duplicate audit fixtures, one removed coverage
  comment, and this report.
- No cross-repository edit, no spec change, no unrelated refactor, no version bump, no tag,
  no release, no registry publication, no credential use.
- No force-push and no rewrite of `main`. Work was pushed to a new branch
  `hardening/final-release-readiness` and opened as PR #1. `git ls-remote` confirms
  `refs/heads/main` is still `59eb2581...`.
- No pre-existing user file or untracked file was deleted or modified.
- Evidence: `git diff --stat 59eb258..HEAD` (5 files, +33/−195),
  `git ls-remote origin main`, PR #1 metadata.

**Status: satisfied.**

### REQ-2 — Immutable unversioned format invariants

- Unchanged by this pass. The format remains exactly 26 lowercase Base36 characters: a
  7-character whole-second timestamp in `0..78_364_164_095` plus 19 characters encoding
  exactly 96 bits from 12 CSPRNG bytes, and the binary form remains exactly 17 bytes
  (5-byte unsigned big-endian timestamp followed by the same 12 bytes, unchanged).
- No version byte, prefix, separator, or field was added. The `pikaid-v1` fixture filename
  remains historical, as documented in `tests/vectors/README.md` and the README.
- The fixtures were not edited. Their bytes are still
  `b0c9dfdd063613424414fef5c9065fbd2f81d645d0ab42b34e27cde715613500` (`pikaid-v1.json`)
  and `4441d4dbaa6c5450ae9cbfb2438c53bc0421bba2b7fcc9ef9b158e5d1de0759e`
  (`pikaid-v1.schema.json`), and no test file changed.
- Evidence: `git diff --stat` shows no change under `src/pikaid/` except the removed
  comment; `shasum -a 256 tests/vectors/*.json`; PHP oracle re-derivation of boundary values.

**Status: satisfied and independently re-verified.**

### REQ-3 — Strict rejection with no normalization or weak fallback

- Unchanged by this pass and re-verified: no trimming, case folding, padding, truncation or
  lossy coercion exists on any decode path; invalid length, non-Base36 characters,
  uppercase, whitespace, non-ASCII, surrogates, wrong binary length, entropy overflow and
  timestamp overflow are rejected; invalid or non-integer timestamps are rejected before
  any entropy is consumed; the CSPRNG is `secrets.token_bytes(12)` with no fallback, and a
  failing or short source raises `EntropySourceError`.
- The pragma removal is a reporting change only: the `except Exception` branch already
  existed and already wrapped source failures; it is now counted because tests do exercise
  it through monkeypatching (`tests/test_generation.py`).
- Evidence: unchanged `src/pikaid/_core.py` logic (`git diff` = one comment line);
  `tests/test_generation.py:151`, `:165`, `:197`, `:222`; PHP oracle and Python
  cross-check mutation/boundary results below.

**Status: satisfied.**

### REQ-4 — API, backward compatibility and error semantics preserved

- The public surface in `src/pikaid/__init__.py` is untouched: same functions, same
  `Pikaid` methods and properties, same constants, same exception classes, same
  `__version__ = "0.1.0"`.
- No error type, message, or trigger condition changed. No signature changed.
- The only source edit is deleting a trailing coverage comment.
- Evidence: `git diff 59eb258..HEAD -- src/pikaid/__init__.py` (empty),
  `git diff 59eb258..HEAD -- src/pikaid/_core.py` (1 line), `tests/test_api.py` (18 tests,
  unchanged) passing on all four interpreters.

**Status: satisfied.**

### REQ-5 — No weakening of CI, test or coverage gates

- No `continue-on-error`, no skipped or xfailed test, no `pragma: no cover` added, no
  removed OS or runtime, no lowered threshold, no altered vector, no vacuous assertion.
  The audit searched `src/`, `tests/`, `.github/` and `pyproject.toml` for
  `skip|xfail|continue-on-error|pragma: no cover`; the only hit was the stale pragma that
  this pass removed.
- The matrix is still 8 entries (Ubuntu 3.11–3.14, macOS 3.11/3.14, Windows 3.11/3.14), and
  `pyproject.toml` still sets `fail_under = 90`. Actual coverage is 100%, so no threshold
  adjustment was needed or made.
- Test count is unchanged at 220; no assertion was relaxed.
- Evidence: `.github/workflows/ci.yml`, `pyproject.toml`, grep output, `git diff` showing no
  test or workflow modification.

**Status: satisfied.**

### REQ-6 — Remote CI green on the final audited commit

- Run [42339421932](https://github.com/pikaid/pikaid-python/actions/runs/42339421932)
  (`CI`, `pull_request`, HEAD `a8627191cfb711ebafa907124d315005f06d738b`) completed with
  **success**; all 10 checks pass.
- The two jobs that previously failed now pass: Windows 3.11
  ([job 128303586223](https://github.com/pikaid/pikaid-python/actions/runs/42339421932/job/128303586223),
  220 passed, 100%) and Windows 3.14
  ([job 128303586296](https://github.com/pikaid/pikaid-python/actions/runs/42339421932/job/128303586296),
  220 passed, 100%). This is the direct proof that the root cause is fixed in the real
  failure environment, not merely on macOS.
- Evidence: `gh run view 42339421932 --json headSha,conclusion` →
  `{"conclusion":"success","headSha":"a8627191..."}`; `gh pr checks 1` → 10 × `pass`.

**Status: satisfied.**

### REQ-7 — Independent verification beyond the test suite

- A PHP conformance oracle built on the vendored pikaid-php v1.2.0 reference implementation
  re-checked all official fixtures and derived 208 additional cases (boundary timestamps
  0, 1, 35, 36, 1295, 1296, 46655, 46656, max−1, max × 8 boundary entropy values including
  the 96-bit maximum; timestamp overflow 2**36, 2**39−1, 2**40−1; entropy overflow; 128
  deterministic LCG cases; ordering across string, binary and timestamp order):
  **1018 checks, 0 failures**.
- Those 208 cases were then verified against this implementation:
  **208 cases, 0 failures**, plus 500 single-bit binary mutations (each must either raise or
  decode to exactly the mutated bytes and differ from the original — no silent
  normalization), 500 single-character string mutations (round-trip and timestamp/entropy
  field behaviour), non-`str` inputs to `is_valid`, out-of-range timestamps,
  non-integer timestamp types, and both extreme accepted values.
- This is an independent second implementation and independent case generation, not a
  restatement of the Python tests.
- Evidence: `.ai/run/oracle/vector_oracle.php` (gitignored validation aid),
  `.ai/run/oracle/python_verify.py`; outputs quoted in Validation below.

**Status: satisfied.**

### REQ-8 — Report content, naming and delivery

- This report follows the mandated section order: Summary; Requirement Coverage; Root
  Cause or Technical Approach; Files Changed; Validation; Deviations and Unresolved Issues;
  Final Status.
- Filename: `.ai/reports/2026-11-07_05-41_pikaid-python_final_release_readiness_hardening.md`
  (no collision existed).
- Delivery: an identical copy is published to the mounted
  `Tohru Drive/pikaid-python/reports/`, verified by reading back the SHA-256 checksum.
  Delivery status is stated separately from `task_result` and is not used to claim code
  correctness.
- Evidence: this file; the delivery section under Deviations and Unresolved Issues.

**Status: satisfied (delivery result recorded separately below).**

## Root Cause or Technical Approach

### The remote failure

`pikaid-v1.json` and `pikaid-v1.schema.json` are LF-only JSON files whose raw bytes are
pinned by SHA-256 in `tests/test_vectors.py`. Git's `core.autocrlf` on Windows converts LF
to CRLF on checkout for files it considers text, which changes the byte stream and therefore
the hash. `main` had no `.gitattributes`, so the Windows runners received CRLF copies and
`test_vector_fixtures_are_pinned` failed there while every other job passed.

Reproduced locally before the fix with
`git -c core.autocrlf=true clone --no-local .`:
`d9df6715349c0e88992452f42380f196a50c49f1768d78c8ff8b8d3bf01f9b04`, 99 CRLF pairs. After
the fix, a fresh `core.autocrlf=true` clone produced the pinned
`b0c9dfdd063613424414fef5c9065fbd2f81d645d0ab42b34e27cde715613500` and
`4441d4dbaa6c5450ae9cbfb2438c53bc0421bba2b7fcc9ef9b158e5d1de0759e`, with 0 CRLF pairs.

### Why the fix is `.gitattributes`, not a weaker test

The invariant worth protecting is "the canonical fixture bytes are the same on every
platform". Three alternatives were rejected:

- Relaxing or platform-gating the hash assertion would delete the guarantee and hide real
  fixture drift.
- Re-generating expectations from the CRLF copy would pin the wrong bytes.
- Reading fixtures in a newline-normalizing way would make the assertion pass while no
  longer proving byte identity, and would change test semantics.

`.gitattributes` instead makes checkout reproduce the committed bytes, which is exactly what
the test already asserts. Rules: `* text=auto eol=lf` for the repository,
`tests/vectors/*.json text eol=lf` for the byte-pinned fixtures, and `*.bat`/`*.cmd` keep
CRLF for future Windows scripts. No other file needs special handling: `uv.lock`,
`pyproject.toml`, `README.md`, `LICENSE` and the Python sources are all legitimately LF, and
the sdist already ships LF copies.

### Secondary findings

- **Duplicate fixtures.** `.ai/audit/pikaid-v1.json` and `.ai/audit/pikaid-v1.schema.json`
  were byte-identical to the canonical files (verified with `cmp` before deletion), so a
  future fixture update could leave the audit copy behind. Only the provenance snapshots
  that exist nowhere else were kept, and `.ai/audit/README.md` now records what each file
  is and which upstream commit it came from. No source, test, packaging or CI file
  references the deleted paths.
- **Unreachable-code marker on reachable code.** `src/pikaid/_core.py` marked
  `except Exception as error:` in `_random_bytes` as `# pragma: no cover - exercised with
  monkeypatching`. The branch *is* exercised (`tests/test_generation.py` monkeypatches
  `secrets.token_bytes` to raise), so the marker understated the measured statement count
  (153) and excluded real code from the coverage denominator. Removing it raises the
  measured surface to 155 statements while coverage stays at 100% — the number is now
  truthful rather than flattering.
- **Prior report correction.** The previous report stated that `.ai/` was untracked. It is
  tracked (`git ls-files .ai` lists the audit snapshots and that report), which is precisely
  why duplicate tracked fixtures mattered. The previous report also reported hosted CI as
  `NOT RUN`; it has now been executed and is green.

### Deliberate non-goals

No version bump, no tag, no PyPI publication, no merge to `main`, no spec change, no new
public API, and no refactor beyond the three items above.

## Files Changed

Commit `6a51856` — `:bug: fix: keep canonical fixtures LF on every checkout`:

| File | Change | Reason |
| --- | --- | --- |
| `.gitattributes` | **added**, 11 lines | Enforce LF on checkout for all text files, explicitly for `tests/vectors/*.json`; keep CRLF for `*.bat`/`*.cmd`. Fixes the Windows-only fixture hash failure. |

Commit `a862719` — `:recycle: refactor: drop duplicate audit fixtures and stale coverage pragma`:

| File | Change | Reason |
| --- | --- | --- |
| `.ai/audit/pikaid-v1.json` | **deleted**, 99 lines | Byte-identical duplicate (`cmp`) of `tests/vectors/pikaid-v1.json`; drift hazard. |
| `.ai/audit/pikaid-v1.schema.json` | **deleted**, 95 lines | Byte-identical duplicate (`cmp`) of `tests/vectors/pikaid-v1.schema.json`; drift hazard. |
| `.ai/audit/README.md` | **added**, 21 lines | Documents the remaining provenance snapshots, their upstream commits, and why the canonical fixtures live only in `tests/vectors/`. |
| `src/pikaid/_core.py` | 1 line changed | Removed a stale `# pragma: no cover` from a branch that tests exercise; no behaviour change; coverage now counts 155 statements honestly. |

Unchanged, deliberately: `src/pikaid/__init__.py`, `src/pikaid/errors.py`, all of `tests/`,
`tests/vectors/*`, `.github/workflows/ci.yml`, `pyproject.toml`, `README.md`, `LICENSE`.

Diff summary: 5 files changed, 33 insertions(+), 195 deletions(-).

## Validation

All commands run from the repository root at `a8627191`.

### Local gates

| Gate | Command | Result |
| --- | --- | --- |
| Test suite + coverage (3.12.11) | `.venv/bin/python -m pytest --cov=pikaid --cov-report=term-missing -q` | **PASS** — 220 passed; 100.00%; 155 stmts, 46 branches, 0 missed, `fail_under=90` satisfied |
| Test suite (3.11.18) | `.venv-3.11/bin/python -m pytest -q` | **PASS** — 220 passed |
| Test suite (3.13.18) | `.venv-3.13/bin/python -m pytest -q` | **PASS** — 220 passed |
| Test suite (3.14.10) | `.venv-3.14/bin/python -m pytest -q` | **PASS** — 220 passed |
| Formatting | `.venv/bin/python -m ruff format --check .` | **PASS** — 18 files already formatted |
| Lint | `.venv/bin/python -m ruff check .` | **PASS** — All checks passed |
| Static typing | `.venv/bin/python -m mypy src` | **PASS** — no issues in 3 source files (strict, `warn_unreachable`) |
| Whitespace/conflict markers | `git diff --check` | **PASS** |

### Windows root cause and fix (real reproduction, not simulation)

| Step | Command | Result |
| --- | --- | --- |
| Before fix | `git -c core.autocrlf=true clone --no-local .` at `59eb258` | **FAIL reproduced** — `pikaid-v1.json` = `d9df6715349c0e88992452f42380f196a50c49f1768d78c8ff8b8d3bf01f9b04`, 99 CRLF pairs |
| After fix | fresh `core.autocrlf=true` clone with `.gitattributes` committed | **PASS** — `b0c9dfdd063613424414fef5c9065fbd2f81d645d0ab42b34e27cde715613500`, `4441d4dbaa6c5450ae9cbfb2438c53bc0421bba2b7fcc9ef9b158e5d1de0759e`, 0 CRLF |
| Fixture integrity | `shasum -a 256 tests/vectors/*.json` | matches the checksums documented in `tests/vectors/README.md` |

### Independent interoperability verification

| Check | Command | Result |
| --- | --- | --- |
| PHP v1.2.0 oracle (official vectors, boundaries, overflow, ordering, 128 LCG cases) | `php .ai/run/oracle/vector_oracle.php` | **PASS** — 1018 checks, 0 failures, 208 derived cases |
| PHP-derived cases against this implementation + adversarial mutations | `.venv/bin/python .ai/run/oracle/python_verify.py` | **PASS** — 208 cases, 0 failures; 500 binary mutations and 500 string mutations, type and boundary assertions |

### Packaging

| Gate | Command | Result |
| --- | --- | --- |
| Build (wheel + sdist) | `.venv/bin/python -m build --outdir .ai/run/dist-final2` | **PASS** — `pikaid-0.1.0-py3-none-any.whl`, `pikaid-0.1.0.tar.gz` |
| Metadata | `.venv/bin/python -m twine check .ai/run/dist-final2/*` | **PASS** — both artifacts PASSED |
| Artifact checksums | `shasum -a 256` | wheel `bcd2845c047507be314cc1d2095cd386220e62e427901bd8379fa51569e6288a`; sdist `1f5670cac420e558fefff1d5c7415d589092d9f4d732ee25375aacf78b963768` |
| Reproducibility | second build, `cmp` both artifacts | **PASS** — byte-identical wheel and sdist |
| Consumer smoke test | clean venv + `pip install` of the wheel | **PASS** — imports from `site-packages`, `0.1.0` on 3.12.11; round trips, known-answer value, max timestamp and `MAX_TIMESTAMP` datetime all correct |
| sdist contents | `tar -tzf` | source, tests, fixtures, README, LICENSE, `pyproject.toml`; no `.ai/`, `.github/`, cache or build artifacts |
| wheel contents | `unzip -l` | `pikaid/{__init__,_core,errors}.py`, `py.typed`, standard `dist-info` |

### Remote CI (authoritative for REQ-6)

Run [42339421932](https://github.com/pikaid/pikaid-python/actions/runs/42339421932),
HEAD `a8627191cfb711ebafa907124d315005f06d738b`, conclusion `success`:

| Check | Result | Duration |
| --- | --- | --- |
| Lint, types, documentation | pass | 22s |
| Build and install the distribution | pass | 22s |
| Test ubuntu-latest / 3.11 | pass | 32s |
| Test ubuntu-latest / 3.12 | pass | 24s |
| Test ubuntu-latest / 3.13 | pass | 28s |
| Test ubuntu-latest / 3.14 | pass | 25s |
| Test macos-latest / 3.11 | pass | 21s |
| Test macos-latest / 3.14 | pass | 20s |
| Test windows-latest / 3.11 | **pass** (previously failed) | 1m7s |
| Test windows-latest / 3.14 | **pass** (previously failed) | 49s |

Windows job logs confirm `220 passed`, `TOTAL 155 0 46 0 100%` and
`Required test coverage of 90.0% reached. Total coverage: 100.00%` on both versions.

## Deviations and Unresolved Issues

- **Independent subagent review was not obtained.** Two attempts (separate sessions) both
  failed with `Model unavailable: profile/small` before producing any output. No review
  content is claimed. Independent verification was instead performed by the PHP v1.2.0
  oracle and the mutation cross-check described above, which is an independent
  implementation rather than a second opinion on the same code.
- **`main` is still red at `59eb258`.** PR
  [#1](https://github.com/pikaid/pikaid-python/pull/1) is open and `MERGEABLE`, but merging
  was outside the authorized scope, so the default branch still fails on Windows until the
  PR is merged. Release readiness therefore applies to the audited commit; it does not yet
  apply to `main`.
- **The report commit itself.** This report is added in a follow-up documentation-only
  commit on the same branch, after the green run above. Because any commit triggers CI, the
  run for that docs-only commit cannot be cited inside the report it contains without an
  endless recursion; its result is reported in the delivery message, and the audited,
  verified code state remains `a8627191`. No source, test, workflow or packaging file
  differs between `a8627191` and the report commit.
- **Drive delivery is separate.** The authoritative report is under `.ai/reports/`; an
  identical copy is written to the mounted
  `Tohru Drive/pikaid-python/reports/` directory, and equality is verified by reading the
  published file back and comparing SHA-256. Mount-level equality proves the file written
  through the mount; it cannot by itself prove Google's cloud synchronization, and a
  delivery failure is reported separately from `task_result`.
- **Branch protection is not enforced.** The GitHub account used has write access but no
  admin role, and the branch-protection API returns 404 for this private repository, so no
  required-check policy is enforced server-side. The green run was therefore obtained and
  cited explicitly rather than assumed from repository settings.
- **Not exercised:** PyPy, free-threaded (`3.14t`) builds, 32-bit platforms, and non-CPython
  interpreters. They are not claimed. The README already states this limitation, and this
  pass did not change it.
- **Not published.** No tag, release, upload, or PyPI metadata was created; the README's
  "not published yet" statement remains accurate.
- No unresolved functional defect is known. The three code-adjacent changes are the only
  source-affecting edits, and all gates pass on all four supported interpreters and on
  GitHub-hosted Linux, macOS and Windows.

## Final Status

**Score: 92 / 100** — One real release blocker (Windows-only CI failure) was reproduced,
diagnosed and fixed at its root rather than masked; the fix is proven in the real failing
environment; the format, API and error semantics are untouched; verification is independent
and adversarial; and packaging is reproducible. The remaining eight points reflect
organizational, not code, gaps: the fix is not merged into `main`, no independent subagent
review was obtainable, and branch protection is not enforced server-side.

**Release readiness: `READY`** for the audited commit `a8627191` on branch
`hardening/final-release-readiness`, contingent on merging PR #1. `main` at `59eb258`
remains **not ready** until that merge happens; that is a process step outside this task's
authorization, not an unresolved code defect.

**task_result: PASS**

All mandatory obligations of this hardening pass were met and evidenced: the defect was
reproduced, root-caused and fixed; no gate was weakened; the full suite passes on 3.11–3.14
with honest 100% coverage; independent interoperability and mutation checks pass; wheel and
sdist are reproducible and consume correctly; and remote CI is green on the final audited
commit including both previously failing Windows jobs. The unavailability of the review
subagent and the unmerged PR are disclosed above and are not counted as successes.
