"""Strict validation and error-path tests."""

from __future__ import annotations

import pytest

from pikaid import (
    MAX_RANDOMNESS,
    MAX_TIMESTAMP,
    RANDOMNESS_BYTES,
    STRING_LENGTH,
    EntropySourceError,
    InvalidPikaidError,
    InvalidTimestampError,
    Pikaid,
    PikaidError,
    from_binary,
    is_valid,
    is_well_formed,
    parse,
    to_binary,
)

from .support import encode_base36, make_id

VALID = "0" * STRING_LENGTH
MAX_RANDOMNESS_SUFFIX = encode_base36(MAX_RANDOMNESS, 19)
OVERFLOW_SUFFIX = encode_base36(MAX_RANDOMNESS + 1, 19)


@pytest.mark.parametrize(
    "value",
    [
        None,
        0,
        1.5,
        b"0" * STRING_LENGTH,
        bytearray(b"0" * STRING_LENGTH),
        memoryview(b"0" * STRING_LENGTH),
        ["0" * STRING_LENGTH],
        {"value": "0" * STRING_LENGTH},
        object(),
    ],
)
def test_parse_rejects_non_string_types(value: object) -> None:
    with pytest.raises(TypeError):
        parse(value)  # type: ignore[arg-type]
    assert is_valid(value) is False
    assert is_well_formed(value) is False


@pytest.mark.parametrize(
    "value",
    [
        "",
        "0",
        "0" * 25,
        "0" * 27,
        "0" * 100,
        "0" * 26 + "\n",
        "\n" + "0" * 26,
    ],
)
def test_wrong_lengths_are_rejected(value: str) -> None:
    with pytest.raises(InvalidPikaidError, match="26"):
        parse(value)
    assert is_valid(value) is False
    assert is_well_formed(value) is False


@pytest.mark.parametrize("position", range(STRING_LENGTH))
def test_uppercase_is_rejected_at_every_position(position: int) -> None:
    value = "0" * position + "A" + "0" * (STRING_LENGTH - position - 1)
    with pytest.raises(InvalidPikaidError):
        parse(value)
    assert is_valid(value) is False
    assert is_well_formed(value) is False


@pytest.mark.parametrize(
    "character",
    ["-", "_", " ", "\t", "\n", "\x00", ".", "/", ":", "@", "[", "`", "{", "~", "!"],
)
def test_non_base36_ascii_is_rejected(character: str) -> None:
    value = "0" * (STRING_LENGTH - 1) + character
    with pytest.raises(InvalidPikaidError):
        parse(value)
    assert is_valid(value) is False
    assert is_well_formed(value) is False


@pytest.mark.parametrize(
    "character",
    ["\u00e9", "\u00c9", "\uff10", "\u017f", "\u041a", "\u4e2d", "\u200b", "\ud800"],
)
def test_non_ascii_is_rejected(character: str) -> None:
    value = "0" * (STRING_LENGTH - 1) + character
    with pytest.raises(InvalidPikaidError):
        parse(value)
    assert is_valid(value) is False
    assert is_well_formed(value) is False


def test_invalid_character_error_names_the_position() -> None:
    with pytest.raises(InvalidPikaidError, match=r"position 7"):
        parse("0000000" + "Z" + "0" * 18)


def test_maximum_randomness_is_valid() -> None:
    value = "0000000" + MAX_RANDOMNESS_SUFFIX
    assert len(value) == STRING_LENGTH
    parsed = parse(value)
    assert parsed.timestamp == 0
    assert parsed.randomness == b"\xff" * RANDOMNESS_BYTES
    assert is_valid(value) is True
    assert is_well_formed(value) is True


def test_randomness_above_96_bits_is_rejected_despite_valid_shape() -> None:
    value = "0000000" + OVERFLOW_SUFFIX
    assert len(value) == STRING_LENGTH
    assert is_well_formed(value) is True
    assert is_valid(value) is False
    with pytest.raises(InvalidPikaidError, match="96"):
        parse(value)
    with pytest.raises(InvalidPikaidError, match="96"):
        to_binary(value)


@pytest.mark.parametrize(
    "suffix",
    [
        "z" * 19,
        "zzzzzzzzzzzzzzzzzz1",
        "zzzzzzzzzzzzzzzzzzy",
        "7oiylpimjg5u2ca1yps",
    ],
)
def test_various_randomness_overflows_are_rejected(suffix: str) -> None:
    assert len(suffix) == 19
    value = "0000000" + suffix
    assert is_well_formed(value) is True
    assert is_valid(value) is False
    with pytest.raises(InvalidPikaidError):
        parse(value)


def test_maximum_timestamp_in_text_form_is_valid() -> None:
    value = "zzzzzzz" + "0" * 19
    parsed = parse(value)
    assert parsed.timestamp == MAX_TIMESTAMP
    assert is_valid(value) is True
    assert is_well_formed(value) is True


def test_well_formed_is_strictly_weaker_than_valid() -> None:
    assert is_well_formed("0" * 26) is True
    assert is_valid("0" * 26) is True
    assert is_well_formed("0000000" + OVERFLOW_SUFFIX) is True
    assert is_valid("0000000" + OVERFLOW_SUFFIX) is False
    assert is_well_formed("0" * 25) is False
    assert is_well_formed("0" * 26 + "A") is False


@pytest.mark.parametrize("length", [0, 1, 16, 18, 32, 34])
def test_binary_with_wrong_length_is_rejected(length: int) -> None:
    value = bytes(length)
    with pytest.raises(InvalidPikaidError, match="17"):
        from_binary(value)
    with pytest.raises(InvalidPikaidError, match="17"):
        Pikaid.from_binary(value)


@pytest.mark.parametrize(
    "value",
    [
        "0" * 34,
        None,
        0,
        1.5,
        [0] * 17,
        tuple([0] * 17),
        object(),
    ],
)
def test_from_binary_rejects_non_bytes_types(value: object) -> None:
    with pytest.raises(TypeError):
        from_binary(value)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Pikaid.from_binary(value)  # type: ignore[arg-type]


def test_from_binary_accepts_bytes_like_objects() -> None:
    binary = bytes.fromhex("006553f10000112233445566778899aabb")
    expected = Pikaid(
        timestamp=1_700_000_000,
        randomness=bytes.fromhex("00112233445566778899aabb"),
    )
    assert from_binary(bytearray(binary)) == expected
    assert from_binary(memoryview(binary)) == expected
    assert from_binary(binary) == expected


@pytest.mark.parametrize(
    "timestamp_bytes",
    [
        (MAX_TIMESTAMP + 1).to_bytes(5, "big"),
        b"\xff" * 5,
        b"\x80\x00\x00\x00\x00",
    ],
)
def test_binary_timestamp_overflow_is_rejected(timestamp_bytes: bytes) -> None:
    value = timestamp_bytes + bytes(RANDOMNESS_BYTES)
    with pytest.raises(InvalidTimestampError):
        from_binary(value)
    with pytest.raises(InvalidTimestampError):
        Pikaid.from_binary(value)


def test_binary_timestamp_maximum_is_accepted() -> None:
    value = MAX_TIMESTAMP.to_bytes(5, "big") + b"\xff" * RANDOMNESS_BYTES
    parsed = from_binary(value)
    assert parsed.timestamp == MAX_TIMESTAMP
    assert parsed.randomness == b"\xff" * RANDOMNESS_BYTES
    assert parsed.to_string() == "zzzzzzz7oiylpimjg5u2ca1ypr"
    assert parsed.to_binary() == value


def test_to_binary_rejects_non_string_non_pikaid_values() -> None:
    for value in (None, 0, 1.5, b"0" * 17, bytearray(17), ["0" * 26]):
        with pytest.raises(TypeError):
            to_binary(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("timestamp", "randomness", "error"),
    [
        (-1, bytes(RANDOMNESS_BYTES), InvalidTimestampError),
        (MAX_TIMESTAMP + 1, bytes(RANDOMNESS_BYTES), InvalidTimestampError),
        (2**40, bytes(RANDOMNESS_BYTES), InvalidTimestampError),
        (True, bytes(RANDOMNESS_BYTES), TypeError),
        (False, bytes(RANDOMNESS_BYTES), TypeError),
        (1.0, bytes(RANDOMNESS_BYTES), TypeError),
        ("1700000000", bytes(RANDOMNESS_BYTES), TypeError),
        (None, bytes(RANDOMNESS_BYTES), TypeError),
        (0, b"", InvalidPikaidError),
        (0, b"\x00" * 11, InvalidPikaidError),
        (0, b"\x00" * 13, InvalidPikaidError),
        (0, bytearray(RANDOMNESS_BYTES), TypeError),
        (0, memoryview(bytes(RANDOMNESS_BYTES)), TypeError),
        (0, "0" * RANDOMNESS_BYTES, TypeError),
        (0, 0, TypeError),
        (0, [0] * RANDOMNESS_BYTES, TypeError),
    ],
)
def test_value_constructor_rejects_invalid_fields(
    timestamp: object, randomness: object, error: type[Exception]
) -> None:
    with pytest.raises(error):
        Pikaid(timestamp=timestamp, randomness=randomness)  # type: ignore[arg-type]


def test_error_messages_are_actionable() -> None:
    with pytest.raises(InvalidPikaidError, match="exactly 26"):
        parse("0" * 25)
    with pytest.raises(InvalidPikaidError, match="position 0"):
        parse("A" + "0" * 25)
    with pytest.raises(InvalidPikaidError, match="96"):
        parse("0000000" + "z" * 19)
    with pytest.raises(InvalidPikaidError, match="exactly 17"):
        from_binary(b"\x00" * 16)
    with pytest.raises(InvalidTimestampError, match="78364164095"):
        from_binary((MAX_TIMESTAMP + 1).to_bytes(5, "big") + bytes(12))


def test_error_hierarchy_is_predictable() -> None:
    assert issubclass(InvalidPikaidError, PikaidError)
    assert issubclass(InvalidPikaidError, ValueError)
    assert issubclass(InvalidTimestampError, PikaidError)
    assert issubclass(InvalidTimestampError, ValueError)
    assert issubclass(EntropySourceError, PikaidError)
    assert issubclass(EntropySourceError, RuntimeError)

    with pytest.raises(InvalidTimestampError) as caught:
        Pikaid(timestamp=-5, randomness=bytes(RANDOMNESS_BYTES))
    assert caught.value.timestamp == -5


def test_str_subclass_is_accepted() -> None:
    class Identifier(str):
        pass

    value = make_id(0, bytes(RANDOMNESS_BYTES))
    parsed = parse(Identifier(value))
    assert parsed.to_string() == value


def test_internal_base36_decoder_rejects_invalid_characters() -> None:
    # Defence in depth: the decoder is fed only shape-validated text in normal
    # use, so exercise its guard directly.
    from pikaid._core import _decode_base36

    with pytest.raises(InvalidPikaidError, match="invalid character 'A'"):
        _decode_base36("00A", "timestamp")
