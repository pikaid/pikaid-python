"""Execute the README examples and check documentation claims."""

from __future__ import annotations

import doctest
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"


def test_readme_examples_execute_cleanly() -> None:
    failures, attempted = doctest.testfile(
        str(README),
        module_relative=False,
        optionflags=doctest.ELLIPSIS,
    )
    # A fixed count prevents a broken/empty extraction from passing silently.
    assert attempted == 30
    assert failures == 0


def test_readme_preserves_branding_and_does_not_claim_publication() -> None:
    text = README.read_text(encoding="utf-8")
    assert "pikaid" in text
    assert "Small · Sortable · Secure ID generator" in text
    assert "not yet published" in text
    assert "pip install pikaid" not in text


def test_readme_pins_the_normative_specification_and_vectors() -> None:
    text = README.read_text(encoding="utf-8")
    assert "1.0.4" in text
    assert "17014d76f568c3ac9f9ce2927c1a018fdbc36d1d" in text
    assert "e3f843edeb5157a5d2d25196cac0d69580810a95" in text
