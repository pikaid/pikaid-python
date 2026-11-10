"""Property-based round-trip, ordering, and validation-oracle tests."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from pikaid import (
    ALPHABET,
    MAX_RANDOMNESS,
    MAX_TIMESTAMP,
    RANDOMNESS_BYTES,
    STRING_LENGTH,
    Pikaid,
    from_binary,
    is_valid,
    is_well_formed,
    parse,
    to_binary,
)

from .support import encode_base36, make_id

TIMESTAMPS = st.integers(min_value=0, max_value=MAX_TIMESTAMP)
RANDOMNESS = st.binary(min_size=RANDOMNESS_BYTES, max_size=RANDOMNESS_BYTES)
IDENTIFIER_CHARS = st.text(alphabet=ALPHABET, min_size=STRING_LENGTH, max_size=STRING_LENGTH)


@settings(max_examples=300, deadline=None)
@given(TIMESTAMPS, RANDOMNESS)
def test_string_and_binary_round_trip(timestamp: int, randomness: bytes) -> None:
    value = Pikaid(timestamp=timestamp, randomness=randomness)
    text = value.to_string()
    binary = value.to_binary()

    assert text == make_id(timestamp, randomness)
    assert text == encode_base36(timestamp, 7) + encode_base36(
        int.from_bytes(randomness, "big"), 19
    )
    assert binary == timestamp.to_bytes(5, "big") + randomness

    assert parse(text) == value
    assert from_binary(binary) == value
    assert to_binary(text) == binary
    assert from_binary(to_binary(text)) == value
    assert parse(from_binary(binary).to_string()) == value


@settings(max_examples=300, deadline=None)
@given(TIMESTAMPS, RANDOMNESS, TIMESTAMPS, RANDOMNESS)
def test_ordering_agrees_across_string_binary_and_value_forms(
    left_timestamp: int,
    left_randomness: bytes,
    right_timestamp: int,
    right_randomness: bytes,
) -> None:
    left = Pikaid(timestamp=left_timestamp, randomness=left_randomness)
    right = Pikaid(timestamp=right_timestamp, randomness=right_randomness)

    assert (left < right) == (left.to_string() < right.to_string())
    assert (left < right) == (left.to_binary() < right.to_binary())
    assert (left == right) == (left.to_binary() == right.to_binary())
    assert (left == right) == (left.to_string() == right.to_string())


@settings(max_examples=300, deadline=None)
@given(IDENTIFIER_CHARS)
def test_validity_matches_independent_range_check(value: str) -> None:
    # Seven Base36 timestamp characters cannot exceed MAX_TIMESTAMP, so full
    # validity for a correctly shaped string depends only on the randomness
    # suffix fitting in 96 bits.
    expected_valid = int(value[7:], 36) <= MAX_RANDOMNESS
    assert is_valid(value) is expected_valid
    assert is_well_formed(value) is True

    if expected_valid:
        parsed = parse(value)
        assert parsed.timestamp == int(value[:7], 36)
        assert int.from_bytes(parsed.randomness, "big") == int(value[7:], 36)
    else:
        assert not is_valid(value)


@settings(max_examples=150, deadline=None)
@given(st.text(max_size=40))
def test_well_formed_matches_independent_shape_check(value: str) -> None:
    expected = len(value) == STRING_LENGTH and all(character in ALPHABET for character in value)
    assert is_well_formed(value) is expected
    if not expected:
        assert is_valid(value) is False
