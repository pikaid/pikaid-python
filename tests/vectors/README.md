# Vendored interoperability fixtures

These files are unmodified copies of the official pikaid fixtures from the PHP
reference implementation:

- Repository: `pikaid/pikaid-php`
- Reference: `v1.2.0`
- Commit: `e3f843edeb5157a5d2d25196cac0d69580810a95`
- Source: `tests/vectors/pikaid-v1.json` and `tests/vectors/pikaid-v1.schema.json`

SHA-256 checksums are asserted by `tests/test_vectors.py`:

```text
b0c9dfdd063613424414fef5c9065fbd2f81d645d0ab42b34e27cde715613500  pikaid-v1.json
4441d4dbaa6c5450ae9cbfb2438c53bc0421bba2b7fcc9ef9b158e5d1de0759e  pikaid-v1.schema.json
```

The `pikaid-v1` filename is historical. The identifier format is immutable and
unversioned; the fixtures record specification revision 1.0.4 in their
metadata. The canonical specification is
`pikaid/pikaid-specs` revision 1.0.4, commit
`17014d76f568c3ac9f9ce2927c1a018fdbc36d1d`.
