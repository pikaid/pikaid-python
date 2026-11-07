# Audit provenance snapshots

These files are read-only provenance for the audit recorded in
`.ai/reports/`. They are not part of the published package and the library
does not read them at runtime or from tests.

| File | Source |
| --- | --- |
| `Pikaid.php`, `PikaidException.php`, `composer.json`, `php-ci.yml`, `php-tests-README.md`, `php-tree.json` | `pikaid/pikaid-php` v1.2.0, commit `e3f843edeb5157a5d2d25196cac0d69580810a95` |
| `spec-README.md`, `spec-LICENSE` | `pikaid/pikaid-specs` revision 1.0.4, commit `17014d76f568c3ac9f9ce2927c1a018fdbc36d1d` |

The PHP implementation is used as an independent interoperability oracle: its
official vectors are re-checked, and boundary plus deterministic pseudo-random
cases are derived from it and then verified against the Python implementation.
PHP is not a Python test dependency, so that check is a release-validation
step, not part of the automated test suite.

The canonical, byte-pinned interoperability fixtures live in `tests/vectors/`
and are asserted by `tests/test_vectors.py`. Byte-identical copies that
previously existed here were removed to avoid fixture drift; the canonical
files and their SHA-256 checksums are documented in `tests/vectors/README.md`.
