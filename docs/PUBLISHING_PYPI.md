# PyPI release setup

This repository publishes to PyPI **only on stable Git tags** via
[PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/).
The release workflow is `.github/workflows/publish-pypi.yml`. No API token is
stored in GitHub.

## One-time configuration

1. On PyPI, register or select the package named **pikaid**. For a new project,
   register a pending trusted publisher instead of using a manual upload.
2. Set the publisher to GitHub owner **pikaid**, repository **pikaid-python**,
   workflow filename **publish-pypi.yml**, environment **pypi**.
3. Create the GitHub environment named **pypi** (repository Settings ->
   Environments). Protect it against untrusted branches/tags as appropriate.
4. Confirm the account controls the package name and that the Trusted Publisher
   is enabled.

## Every release

1. Update the package version in both `pyproject.toml` and
   `src/pikaid/__init__.py` in the source commit. Preserve the existing tests
   and verification checks.
2. Verify CI succeeds, then tag that commit with a stable tag
   such as `v1.0.1` and publish the GitHub release.
3. GitHub automatically validates formatting, types, tests with 100% coverage,
   builds exactly one wheel and source distribution, and publishes using OIDC.

GitHub releases do **not** overwrite a previously published PyPI version.
The Git tag and both version declarations must match. A failed release must
be diagnosed and corrected in a new source commit and version rather than
bypassing tests.

**No manual upload or per-release PyPI login is necessary after setup.**
