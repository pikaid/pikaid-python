"""Public API surface, value semantics, and documentation examples."""

from __future__ import annotations

import dataclasses
import pickle
from datetime import UTC, datetime

import pytest

import pikaid
from pikaid import (
    ALPHABET,
    BINARY_LENGTH,
    MAX_RANDOMNESS,
    MAX_TIMESTAMP,
    RANDOMNESS_BYTES,
    RANDOMNESS_CHARS,
    STRING_LENGTH,
    TIMESTAMP_BYTES,
    TIMESTAMP_CHARS,
    EntropySourceError,
    InvalidPikaidError,
    InvalidTimestampError,
    Pikaid,
    PikaidError,
    from_binary,
    generate,
    generate_binary,
    is_valid,
    is_well_formed,
    parse,
    to_binary,
)

from .support import make_id

SAMPLE_TIMESTAMP = 1_700_000_000
SAMPLE_RANDOMNESS = bytes.fromhex("00112233445566778899aabb")
SAMPLE_ID = "0s44we8002loz3po6mcf6vsn23"
SAMPLE_BINARY = bytes.fromhex("006553f10000112233445566778899aabb")

EXPECTED_EXPORTS = {
    "ALPHABET",
    "BINARY_LENGTH",
    "MAX_RANDOMNESS",
    "MAX_TIMESTAMP",
    "RANDOMNESS_BYTES",
    "RANDOMNESS_CHARS",
    "STRING_LENGTH",
    "TIMESTAMP_BYTES",
    "TIMESTAMP_CHARS",
    "EntropySourceError",
    "InvalidPikaidError",
    "InvalidTimestampError",
    "Pikaid",
    "PikaidError",
    "from_binary",
    "generate",
    "generate_binary",
    "is_valid",
    "is_well_formed",
    "parse",
    "to_binary",
}


def test_module_exports_are_declared_and_importable() -> None:
    assert set(pikaid.__all__) == EXPECTED_EXPORTS | {"__version__"}
    for name in pikaid.__all__:
        assert hasattr(pikaid, name), name
    assert isinstance(pikaid.__version__, str)
    assert pikaid.__version__ == "1.0.0"


def test_star_import_matches_public_contract() -> None:
    namespace: dict[str, object] = {}
    exec("from pikaid import *", namespace)
    assert set(namespace) - {"__builtins__"} == EXPECTED_EXPORTS | {"__version__"}


def test_constants_are_consistent_with_each_other() -> None:
    assert STRING_LENGTH == TIMESTAMP_CHARS + RANDOMNESS_CHARS
    assert BINARY_LENGTH == TIMESTAMP_BYTES + RANDOMNESS_BYTES
    assert len(ALPHABET) == 36
    assert MAX_TIMESTAMP == 36**TIMESTAMP_CHARS - 1
    assert MAX_RANDOMNESS == (1 << (8 * RANDOMNESS_BYTES)) - 1


def test_parse_returns_value_object_and_module_functions_agree() -> None:
    value = parse(SAMPLE_ID)
    assert isinstance(value, Pikaid)
    assert value == Pikaid(timestamp=SAMPLE_TIMESTAMP, randomness=SAMPLE_RANDOMNESS)
    assert Pikaid.parse(SAMPLE_ID) == value
    assert from_binary(SAMPLE_BINARY) == value
    assert Pikaid.from_binary(SAMPLE_BINARY) == value
    assert to_binary(SAMPLE_ID) == SAMPLE_BINARY
    assert to_binary(value) == SAMPLE_BINARY
    assert value.to_string() == SAMPLE_ID
    assert str(value) == SAMPLE_ID
    assert value.to_binary() == SAMPLE_BINARY


def test_generation_helpers_return_the_documented_types() -> None:
    text = generate(timestamp=SAMPLE_TIMESTAMP)
    binary = generate_binary(timestamp=SAMPLE_TIMESTAMP)

    assert type(text) is str
    assert type(binary) is bytes
    assert len(text) == STRING_LENGTH
    assert len(binary) == BINARY_LENGTH
    assert parse(text).timestamp == SAMPLE_TIMESTAMP
    assert from_binary(binary).timestamp == SAMPLE_TIMESTAMP


def test_value_object_repr_and_str() -> None:
    value = Pikaid(timestamp=SAMPLE_TIMESTAMP, randomness=SAMPLE_RANDOMNESS)
    assert repr(value) == (
        f"Pikaid(timestamp={SAMPLE_TIMESTAMP}, randomness={SAMPLE_RANDOMNESS!r})"
    )
    assert str(value) == SAMPLE_ID
    assert f"identifier: {value}" == f"identifier: {SAMPLE_ID}"


def test_value_objects_compare_equal_and_hash_consistently() -> None:
    first = Pikaid(timestamp=SAMPLE_TIMESTAMP, randomness=SAMPLE_RANDOMNESS)
    second = parse(SAMPLE_ID)
    third = Pikaid(timestamp=SAMPLE_TIMESTAMP, randomness=bytes(12))

    assert first == second
    assert hash(first) == hash(second)
    assert first != third
    assert len({first, second, third}) == 2


def test_value_objects_are_ordered() -> None:
    early = Pikaid(timestamp=1, randomness=bytes(12))
    late = Pikaid(timestamp=2, randomness=bytes(12))

    assert early < late
    assert early <= late
    assert late > early
    assert late >= early
    assert sorted([late, early]) == [early, late]
    assert (early == late) is False
    assert (early < early) is False


def test_value_objects_are_immutable() -> None:
    value = Pikaid(timestamp=SAMPLE_TIMESTAMP, randomness=SAMPLE_RANDOMNESS)
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.timestamp = 0  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.randomness = bytes(12)  # type: ignore[misc]
    assert dataclasses.is_dataclass(value)


def test_value_objects_survive_pickling() -> None:
    value = Pikaid(timestamp=SAMPLE_TIMESTAMP, randomness=SAMPLE_RANDOMNESS)
    restored = pickle.loads(pickle.dumps(value))
    assert restored == value
    assert restored.to_string() == SAMPLE_ID
    assert hash(restored) == hash(value)


def test_datetime_property_is_aware_utc() -> None:
    value = Pikaid(timestamp=SAMPLE_TIMESTAMP, randomness=SAMPLE_RANDOMNESS)
    assert value.datetime == datetime.fromtimestamp(SAMPLE_TIMESTAMP, tz=UTC)
    assert value.datetime.tzinfo is UTC
    assert value.datetime.year == 2023


def test_randomness_hex_property() -> None:
    value = Pikaid(timestamp=0, randomness=SAMPLE_RANDOMNESS)
    assert value.randomness_hex == "00112233445566778899aabb"
    assert len(value.randomness_hex) == RANDOMNESS_BYTES * 2


def test_is_valid_and_is_well_formed_return_real_booleans() -> None:
    assert is_valid(SAMPLE_ID) is True
    assert is_well_formed(SAMPLE_ID) is True
    assert is_valid("not-a-pikaid") is False
    assert is_well_formed("not-a-pikaid") is False
    assert is_valid(None) is False
    assert is_well_formed(None) is False


def test_classmethods_and_module_functions_share_behavior() -> None:
    class_value = Pikaid.parse(SAMPLE_ID)
    module_value = parse(SAMPLE_ID)
    assert class_value == module_value
    assert class_value.to_binary() == to_binary(SAMPLE_ID)
    assert Pikaid.from_binary(SAMPLE_BINARY) == from_binary(SAMPLE_BINARY)


def test_error_hierarchy_is_exposed_and_catchable_by_base_class() -> None:
    assert issubclass(InvalidPikaidError, PikaidError)
    assert issubclass(InvalidTimestampError, PikaidError)
    assert issubclass(EntropySourceError, PikaidError)
    assert issubclass(PikaidError, Exception)

    with pytest.raises(PikaidError):
        parse("bad")
    with pytest.raises(PikaidError):
        Pikaid(timestamp=-1, randomness=bytes(12))


def test_supported_binary_input_conversions_are_lossless() -> None:
    expected = parse(SAMPLE_ID)
    assert from_binary(SAMPLE_BINARY) == expected
    assert from_binary(bytearray(SAMPLE_BINARY)) == expected
    assert from_binary(memoryview(SAMPLE_BINARY)) == expected


def test_docstring_examples_match_documented_output() -> None:
    # These values also appear in README.md and are covered by doctests there.
    assert generate(timestamp=SAMPLE_TIMESTAMP) not in {""}
    assert make_id(SAMPLE_TIMESTAMP, SAMPLE_RANDOMNESS) == SAMPLE_ID
    assert parse(SAMPLE_ID).timestamp == SAMPLE_TIMESTAMP
    assert parse(SAMPLE_ID).randomness_hex == SAMPLE_RANDOMNESS.hex()


def test_package_metadata_version_matches_module_version() -> None:
    from importlib.metadata import version

    assert version("pikaid") == pikaid.__version__
