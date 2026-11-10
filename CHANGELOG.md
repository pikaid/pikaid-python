# Changelog

All notable changes to this project are documented in this file.

The identifier format itself is **immutable and unversioned**; this file tracks
only the Python package. The canonical format definition is
[pikaid specification revision 1.0.4](https://github.com/pikaid/pikaid-specs/tree/v1.0.4).

## [1.0.0] - 2026-11-07

First stable version of the package. Prepared for publication; **not yet
uploaded to any package index** (see the status note in the README).

### Added

- `generate`, `generate_binary`, `parse`, `is_valid`, `is_well_formed`,
  `to_binary`, `from_binary`, and the immutable `Pikaid` value type.
- The 26-character lowercase Base36 text form and the 17-byte binary form
  (5-byte big-endian timestamp plus the 12 entropy bytes unchanged).
- Strict validation: no trimming, padding, or case folding; timestamps outside
  `0..78_364_164_095` and randomness above `2**96 - 1` are rejected.
- CSPRNG-backed generation through `secrets.token_bytes(12)` with fail-closed
  `EntropySourceError` behavior when the source raises or returns the wrong
  amount of data.
- A `py.typed` marker, no runtime dependencies, and support for CPython
  3.11–3.14.

### Notes

- CPython 3.11–3.14 is verified locally on macOS. The CI workflow configures
  Linux, macOS, and Windows for 3.11–3.14, but the hosted jobs have not executed
  yet, so Linux and Windows runtime support remains unverified. PyPy and
  free-threaded builds have not been verified.
- No Git tag, registry upload, or signed artifact exists for this version yet.
