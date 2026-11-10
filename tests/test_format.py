"""Format, encoding, conversion, ordering, and boundary tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

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
    Pikaid,
)

from .support import encode_base36, make_id

ALL_ZERO_BINARY = bytes(17)
MAX_RANDOMNESS_BYTES = b"\xff" * RANDOMNESS_BYTES


def test_public_constants_match_the_specification() -> None:
    assert ALPHABET == "0123456789abcdefghijklmnopqrstuvwxyz"
    assert STRING_LENGTH == 26
    assert BINARY_LENGTH == 17
    assert TIMESTAMP_CHARS == 7
    assert RANDOMNESS_CHARS == 19
    assert TIMESTAMP_BYTES == 5
    assert RANDOMNESS_BYTES == 12
    assert MAX_TIMESTAMP == 78_364_164_095
    assert MAX_RANDOMNESS == (1 << 96) - 1


@pytest.mark.parametrize(
    ("timestamp", "prefix"),
    [
        (0, "0000000"),
        (1, "0000001"),
        (9, "0000009"),
        (10, "000000a"),
        (35, "000000z"),
        (36, "0000010"),
        (36**2, "0000100"),
        (36**6, "1000000"),
        (MAX_TIMESTAMP, "zzzzzzz"),
    ],
)
def test_timestamp_prefix_is_fixed_width_base36(timestamp: int, prefix: str) -> None:
    value = Pikaid(timestamp=timestamp, randomness=bytes(RANDOMNESS_BYTES))
    expected = prefix + "0" * RANDOMNESS_CHARS
    assert value.to_string() == expected
    assert value.to_string()[:TIMESTAMP_CHARS] == encode_base36(timestamp, TIMESTAMP_CHARS)


@pytest.mark.parametrize(
    ("randomness", "suffix"),
    [
        (bytes(RANDOMNESS_BYTES), "0" * RANDOMNESS_CHARS),
        (b"\x00" * 11 + b"\x01", "0" * 18 + "1"),
        (b"\x00" * 11 + b"\x09", "0" * 18 + "9"),
        (b"\x00" * 11 + b"\x0a", "0" * 18 + "a"),
        (b"\x00" * 11 + b"\x23", "0" * 18 + "z"),
        (b"\x00" * 11 + b"\x24", "0" * 17 + "10"),
        (MAX_RANDOMNESS_BYTES, "7oiylpimjg5u2ca1ypr"),
    ],
)
def test_randomness_suffix_is_fixed_width_base36(randomness: bytes, suffix: str) -> None:
    value = Pikaid(timestamp=0, randomness=randomness)
    assert value.to_string() == "0000000" + suffix
    assert value.to_string()[TIMESTAMP_CHARS:] == encode_base36(
        int.from_bytes(randomness, "big"), RANDOMNESS_CHARS
    )


def test_zero_padding_is_preserved_in_both_directions() -> None:
    value = Pikaid(timestamp=0, randomness=b"\x00" * 11 + b"\x01")
    assert value.to_string() == "00000000000000000000000001"
    assert value.to_binary() == ALL_ZERO_BINARY[:16] + b"\x01"
    assert value.to_binary().hex() == "00" * 16 + "01"
    assert value.to_binary()[:TIMESTAMP_BYTES] == b"\x00" * 5


def test_binary_layout_is_five_byte_timestamp_then_unchanged_randomness() -> None:
    randomness = bytes(range(12))
    value = Pikaid(timestamp=0x0102030405, randomness=randomness)
    binary = value.to_binary()
    assert len(binary) == BINARY_LENGTH
    assert binary == b"\x01\x02\x03\x04\x05" + randomness
    assert binary[:TIMESTAMP_BYTES] == b"\x01\x02\x03\x04\x05"
    assert binary[TIMESTAMP_BYTES:] == randomness


def test_binary_timestamp_is_unsigned_big_endian() -> None:
    value = Pikaid(timestamp=MAX_TIMESTAMP, randomness=MAX_RANDOMNESS_BYTES)
    binary = value.to_binary()
    assert binary[:TIMESTAMP_BYTES] == bytes.fromhex("123ede3fff")
    assert int.from_bytes(binary[:TIMESTAMP_BYTES], "big") == MAX_TIMESTAMP
    assert binary[TIMESTAMP_BYTES:] == MAX_RANDOMNESS_BYTES
    # Official max-values vector.
    assert binary.hex() == "123ede3fffffffffffffffffffffffffff"
    assert value.to_string() == "zzzzzzz7oiylpimjg5u2ca1ypr"


def test_all_zero_value() -> None:
    value = Pikaid(timestamp=0, randomness=bytes(RANDOMNESS_BYTES))
    assert value.to_string() == "0" * STRING_LENGTH
    assert value.to_binary() == ALL_ZERO_BINARY
    assert Pikaid.parse("0" * STRING_LENGTH) == value
    assert Pikaid.from_binary(ALL_ZERO_BINARY) == value


@pytest.mark.parametrize(
    ("timestamp", "randomness"),
    [
        (0, bytes(RANDOMNESS_BYTES)),
        (0, MAX_RANDOMNESS_BYTES),
        (1, b"\x00" * 11 + b"\x01"),
        (MAX_TIMESTAMP, bytes(RANDOMNESS_BYTES)),
        (MAX_TIMESTAMP, MAX_RANDOMNESS_BYTES),
        (1_700_000_000, bytes.fromhex("00112233445566778899aabb")),
        (36**3 + 36**2 + 36 + 1, bytes.fromhex("0123456789abcdef01234567")),
    ],
)
def test_string_binary_round_trips_are_lossless(timestamp: int, randomness: bytes) -> None:
    value = Pikaid(timestamp=timestamp, randomness=randomness)
    text = value.to_string()
    binary = value.to_binary()

    assert len(text) == STRING_LENGTH
    assert text == make_id(timestamp, randomness)
    assert len(binary) == BINARY_LENGTH

    assert Pikaid.parse(text) == value
    assert Pikaid.from_binary(binary) == value
    assert Pikaid.from_binary(Pikaid.parse(text).to_binary()) == value
    assert Pikaid.parse(Pikaid.from_binary(binary).to_string()) == value


def test_timestamp_and_randomness_are_extracted_precisely() -> None:
    timestamp = 1_700_000_000
    randomness = bytes.fromhex("00112233445566778899aabb")
    value = Pikaid.from_binary(bytes.fromhex("006553f10000112233445566778899aabb"))
    assert value.timestamp == timestamp
    assert value.randomness == randomness
    assert value.randomness_hex == "00112233445566778899aabb"
    assert value.to_string() == "0s44we8002loz3po6mcf6vsn23"


def test_datetime_is_timezone_aware_utc() -> None:
    value = Pikaid(timestamp=0, randomness=bytes(RANDOMNESS_BYTES))
    assert value.datetime == datetime(1970, 1, 1, tzinfo=UTC)
    assert value.datetime.utcoffset() == timedelta(0)


def test_maximum_timestamp_maps_to_specification_date() -> None:
    value = Pikaid(timestamp=MAX_TIMESTAMP, randomness=bytes(RANDOMNESS_BYTES))
    decoded = value.datetime
    assert (decoded.year, decoded.month, decoded.day) == (4453, 4, 5)
    assert (decoded.hour, decoded.minute, decoded.second) == (15, 21, 35)
    assert decoded.tzinfo is UTC


@pytest.mark.parametrize(
    ("earlier", "later"),
    [
        (0, 1),
        (1, 2),
        (1_700_000_000, 1_700_000_001),
        (0, MAX_TIMESTAMP),
        (MAX_TIMESTAMP - 1, MAX_TIMESTAMP),
    ],
)
def test_different_seconds_sort_chronologically(earlier: int, later: int) -> None:
    # The earlier value deliberately has maximal randomness and the later value
    # minimal randomness: the timestamp still decides the order.
    first = Pikaid(timestamp=earlier, randomness=MAX_RANDOMNESS_BYTES)
    second = Pikaid(timestamp=later, randomness=bytes(RANDOMNESS_BYTES))

    assert first < second
    assert first.to_string() < second.to_string()
    assert first.to_binary() < second.to_binary()


def test_same_second_order_follows_randomness_not_creation_time() -> None:
    low = Pikaid(timestamp=1_700_000_000, randomness=bytes(RANDOMNESS_BYTES))
    high = Pikaid(timestamp=1_700_000_000, randomness=MAX_RANDOMNESS_BYTES)

    created = [high, low]
    assert sorted(created) == [low, high]
    assert low < high
    assert low.to_string() < high.to_string()
    assert low.to_binary() < high.to_binary()


def test_string_and_binary_order_agree_across_values() -> None:
    values = [
        Pikaid(timestamp=timestamp, randomness=randomness)
        for timestamp in (0, 1, 35, 36, 1_700_000_000, MAX_TIMESTAMP)
        for randomness in (bytes(RANDOMNESS_BYTES), MAX_RANDOMNESS_BYTES)
    ]
    by_value = sorted(values)
    by_string = sorted(values, key=lambda value: value.to_string())
    by_binary = sorted(values, key=lambda value: value.to_binary())
    assert by_value == by_string == by_binary
