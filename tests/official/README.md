# Official conformance integration

This directory is **test tooling only**. It is shipped in the source distribution
(so `pytest tests` works from an sdist checkout) but is not part of the `pikaid`
package and is never imported by it.

## Pinned provenance

| Item | Value |
| --- | --- |
| Repository | `pikaid/pikaid-specs` |
| Commit | `059780cc0e5b113443812720d95c630649bf3aa3` |
| Suite status | `OFFICIAL` |
| Suite revision | `1.0.0` |
| Specification revision | `1.0.4` |
| Fixture inventory | 596 valid / 258 invalid-string / 33 invalid-binary / 186 ordering / 12 generation / 15 properties = **1,100 rows** |

The pins live in `run_official_suite.py`; the suite is never fetched from a
mutable branch. The driver fails closed unless the suite is a Git checkout whose
`HEAD` is exactly that commit, all 31 entries in `SHA256SUMS` match, the manifest
identity is correct, and the observed fixture counts equal the declared
inventory.

## What runs

`run_official_suite.py` executes, in order:

1. `verify_vectors.py --expect-status OFFICIAL --expect-package-revision 1.0.0
   --expect-spec-revision 1.0.4`
2. the suite's own `unittest` corpus (`tools/tests`, 52 tests)
3. the independent Node.js `BigInt` oracle (`tools/verify_oracle_node.mjs`)
4. `run_adapter.py --automated-only --report-json <path> -- <adapter-command>`

`adapter.py` is a JSON-Lines bridge (protocol v1). It contains no identifier
encoding, decoding or validation logic: each operation calls a public `pikaid`
function or method, and only the library's documented rejection exceptions are
mapped to `invalid_input`. Unexpected failures become `internal_error` so they
can never masquerade as a legitimate rejection. Fault injection replaces
`secrets.token_bytes` inside the adapter process only, which is the real
function the library calls; the production package gains no RNG seam.

Exit `0` means **automated checks passed**. It is not a conformance
certification: the suite still lists `P-GENERATE-RNG-SOURCE` and
`P-GENERATE-RNG-FAILURE` as manual audit items.

## Local invocation

```sh
git init .ai/conformance-cache/pikaid-specs
git -C .ai/conformance-cache/pikaid-specs remote add origin \
  https://github.com/pikaid/pikaid-specs.git
git -C .ai/conformance-cache/pikaid-specs -c core.autocrlf=false \
  fetch --depth 1 origin 059780cc0e5b113443812720d95c630649bf3aa3
git -C .ai/conformance-cache/pikaid-specs -c core.autocrlf=false \
  checkout --detach FETCH_HEAD

PIKAID_CONFORMANCE_SUITE=.ai/conformance-cache/pikaid-specs/conformance \
  python tests/official/run_official_suite.py \
  --report-json .ai/off-report.json \
  -- .venv/bin/python tests/official/adapter.py
```

The driver needs `jsonschema` (the suite's own tools import it), `node`, and a
Python that can import `pikaid`. CI installs the wheel or sdist into a clean
virtual environment and passes that interpreter as the adapter command, so the
installed artifact is what gets tested.

## Why the native suite is retained

The 329 pre-existing native tests are not replaced by the official suite. They
cover Python-specific failure modes the cross-language fixtures cannot express:
constructor invariants (`Pikaid` field validation), exception identity and
messages, non-string/non-integer argument handling, `is_valid` versus
`is_well_formed` semantics, clock/entropy monkeypatch seams, the mutation
negative control, README examples, and the vendored PHP-reference fixtures with
their checksums. Removing them would lose failure-mode coverage even though the
1,100 official rows overlap on canonical conversions. The official suite is
added as a separate integration layer; no native test was deleted or weakened.
