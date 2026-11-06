"""Official pikaid v1.2.0 interoperability vectors and schema."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from pikaid import (
    MAX_TIMESTAMP,
    Pikaid,
    PikaidError,
    from_binary,
    is_valid,
    is_well_formed,
    parse,
    to_binary,
)

VECTOR_DIR = Path(__file__).parent / "vectors"
VECTORS = json.loads((VECTOR_DIR / "pikaid-v1.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((VECTOR_DIR / "pikaid-v1.schema.json").read_text(encoding="utf-8"))

VECTORS_SHA256 = "b0c9dfdd063613424414fef5c9065fbd2f81d645d0ab42b34e27cde715613500"
SCHEMA_SHA256 = "4441d4dbaa6c5450ae9cbfb2438c53bc0421bba2b7fcc9ef9b158e5d1de0759e"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _case_id(case: dict[str, Any]) -> str:
    return str(case["name"])


def test_vector_fixtures_are_pinned() -> None:
    assert _digest(VECTOR_DIR / "pikaid-v1.json") == VECTORS_SHA256
    assert _digest(VECTOR_DIR / "pikaid-v1.schema.json") == SCHEMA_SHA256


def test_vector_metadata_matches_spec_revision() -> None:
    meta = VECTORS["meta"]
    assert meta["project"] == "pikaid"
    assert meta["spec_revision"] == "1.0.4"
    assert meta["identifier_format"] == "immutable and unversioned"
    assert meta["string_length"] == 26
    assert meta["timestamp"]["max"] == MAX_TIMESTAMP
    assert meta["timestamp"]["chars"] == 7
    assert meta["entropy"]["bytes"] == 12
    assert meta["entropy"]["chars"] == 19
    assert meta["binary"]["bytes"] == 17


def test_vectors_conform_to_published_schema() -> None:
    Draft202012Validator.check_schema(SCHEMA)
    Draft202012Validator(SCHEMA).validate(VECTORS)


@pytest.mark.parametrize("case", VECTORS["valid"], ids=_case_id)
def test_valid_vector_decodes_exactly(case: dict[str, Any]) -> None:
    parsed = parse(case["id"])
    assert parsed.timestamp == case["timestamp"]
    assert parsed.randomness.hex() == case["entropy_hex"]
    assert parsed.randomness_hex == case["entropy_hex"]
    assert parsed.to_string() == case["id"]
    assert str(parsed) == case["id"]

    expected_binary = bytes.fromhex(case["bin_hex"])
    assert len(expected_binary) == 17
    assert parsed.to_binary() == expected_binary
    assert to_binary(case["id"]) == expected_binary
    assert to_binary(parsed) == expected_binary

    assert from_binary(expected_binary) == parsed
    assert Pikaid.from_binary(expected_binary) == parsed
    assert from_binary(expected_binary).to_string() == case["id"]

    assert is_valid(case["id"])
    assert is_well_formed(case["id"])


@pytest.mark.parametrize("case", VECTORS["invalid"]["string"], ids=_case_id)
def test_invalid_string_vector_is_rejected(case: dict[str, Any]) -> None:
    value = case["id"]
    with pytest.raises(PikaidError):
        parse(value)
    with pytest.raises(PikaidError):
        to_binary(value)
    assert is_valid(value) is False
    # The historical "entropy-overflow" vector is well formed (length and
    # alphabet) but semantically invalid (more than 96 bits of randomness).
    assert is_well_formed(value) is (case["name"] == "entropy-overflow")


@pytest.mark.parametrize("case", VECTORS["invalid"]["binary"], ids=_case_id)
def test_invalid_binary_vector_is_rejected(case: dict[str, Any]) -> None:
    value = bytes.fromhex(case["bin_hex"])
    with pytest.raises(PikaidError):
        from_binary(value)
    with pytest.raises(PikaidError):
        Pikaid.from_binary(value)
