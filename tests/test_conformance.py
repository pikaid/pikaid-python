"""Pinned cross-representation conformance matrix and adversarial corpus.

The expected text and binary values in ``CONFORMANCE`` are literal known
answers.  They are additionally recomputed with the independent oracle in
``tests.support``, which never imports :mod:`pikaid`; the production encoder is
never used to derive an expectation.

The same rows are exercised through every relevant public entrypoint so that
``parse``, ``Pikaid.parse``, ``from_binary``, ``Pikaid.from_binary``,
``to_binary``, ``is_valid``, ``is_well_formed``, ``generate``,
``generate_binary`` and ``Pikaid.generate`` agree on the same input value.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from itertools import combinations
from typing import Any

import pytest

from pikaid import (
    ALPHABET,
    BINARY_LENGTH,
    MAX_RANDOMNESS,
    MAX_TIMESTAMP,
    RANDOMNESS_BYTES,
    STRING_LENGTH,
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

from .support import encode_base36, make_id

# (name, timestamp, entropy hex, expected 26-character text, expected 17-byte hex)
CONFORMANCE: list[tuple[str, int, str, str, str]] = [
    (
        "zero",
        0,
        "000000000000000000000000",
        "00000000000000000000000000",
        "0000000000000000000000000000000000",
    ),
    (
        "one",
        1,
        "000000000000000000000001",
        "00000010000000000000000001",
        "0000000001000000000000000000000001",
    ),
    (
        "max",
        78_364_164_095,
        "ffffffffffffffffffffffff",
        "zzzzzzz7oiylpimjg5u2ca1ypr",
        "123ede3fffffffffffffffffffffffffff",
    ),
    (
        "sample-1700000000",
        1_700_000_000,
        "00112233445566778899aabb",
        "0s44we8002loz3po6mcf6vsn23",
        "006553f10000112233445566778899aabb",
    ),
    (
        "leading-zero-entropy",
        1_700_000_000,
        "000000000000000000000001",
        "0s44we80000000000000000001",
        "006553f100000000000000000000000001",
    ),
    (
        "all-ff-entropy",
        1_700_000_000,
        "ffffffffffffffffffffffff",
        "0s44we87oiylpimjg5u2ca1ypr",
        "006553f100ffffffffffffffffffffffff",
    ),
    (
        "near-max-timestamp",
        78_364_164_094,
        "000000000000000000000000",
        "zzzzzzy0000000000000000000",
        "123ede3ffe000000000000000000000000",
    ),
    (
        "near-min-timestamp",
        2,
        "000000000000000000000000",
        "00000020000000000000000000",
        "0000000002000000000000000000000000",
    ),
    (
        "timestamp-36-pow-6",
        2_176_782_336,
        "0123456789abcdef01234567",
        "10000000188skr4f4jv458xrhj",
        "0081bf10000123456789abcdef01234567",
    ),
    (
        "seeded-0",
        47_189_264_460,
        "85a0587392e4c2feb06d1c39",
        "lof9pho40c9py4kttk2xim5veh",
        "0afcb3084c85a0587392e4c2feb06d1c39",
    ),
    (
        "seeded-1",
        42_499_548_079,
        "4490bd623bc9ea8dde26c603",
        "jiv4t672229tc1dm988xc4248z",
        "09e52ba3af4490bd623bc9ea8dde26c603",
    ),
    (
        "seeded-2",
        10_416_234_166,
        "69a1afda4f2ab96cc58c23b3",
        "4s9k1py363ne9u147qh697ve0j",
        "026cdb1eb669a1afda4f2ab96cc58c23b3",
    ),
    (
        "seeded-3",
        16_961_536_391,
        "24c32600175b9d5ff0c0154c",
        "7sigl8n13pk58dyfamir734y8c",
        "03f2fc818724c32600175b9d5ff0c0154c",
    ),
    (
        "ascending-early",
        1_700_000_000,
        "000000000000000000000000",
        "0s44we80000000000000000000",
        "006553f100000000000000000000000000",
    ),
    (
        "ascending-late",
        1_700_000_001,
        "000000000000000000000000",
        "0s44we90000000000000000000",
        "006553f101000000000000000000000000",
    ),
]

ROW_IDS = [row[0] for row in CONFORMANCE]


def _randomness(row: tuple[str, int, str, str, str]) -> bytes:
    return bytes.fromhex(row[2])


@pytest.mark.parametrize(
    ("name", "timestamp", "entropy_hex", "text", "binary_hex"), CONFORMANCE, ids=ROW_IDS
)
def test_known_answers_match_independent_oracle(
    name: str,
    timestamp: int,
    entropy_hex: str,
    text: str,
    binary_hex: str,
) -> None:
    randomness = bytes.fromhex(entropy_hex)
    binary = bytes.fromhex(binary_hex)

    # The oracle is implemented from the specification only; it does not import
    # pikaid and cannot mask a production encoder/decoder bug.
    assert make_id(timestamp, randomness) == text
    assert timestamp.to_bytes(5, "big") + randomness == binary
    assert encode_base36(timestamp, 7) == text[:7]
    assert encode_base36(int.from_bytes(randomness, "big"), 19) == text[7:]

    assert len(text) == STRING_LENGTH
    assert all(character in ALPHABET for character in text)
    assert len(binary) == BINARY_LENGTH


@pytest.mark.parametrize(
    ("name", "timestamp", "entropy_hex", "text", "binary_hex"), CONFORMANCE, ids=ROW_IDS
)
def test_public_entrypoints_agree_on_pinned_value(
    name: str,
    timestamp: int,
    entropy_hex: str,
    text: str,
    binary_hex: str,
) -> None:
    randomness = bytes.fromhex(entropy_hex)
    binary = bytes.fromhex(binary_hex)
    value = Pikaid(timestamp=timestamp, randomness=randomness)

    assert value.to_string() == text
    assert str(value) == text
    assert value.to_binary() == binary

    assert parse(text) == value
    assert Pikaid.parse(text) == value
    assert from_binary(binary) == value
    assert Pikaid.from_binary(binary) == value
    assert from_binary(bytearray(binary)) == value
    assert from_binary(memoryview(binary)) == value

    assert to_binary(text) == binary
    assert to_binary(value) == binary
    assert is_valid(text) is True
    assert is_well_formed(text) is True

    decoded = parse(text)
    assert decoded.timestamp == timestamp
    assert decoded.randomness == randomness
    assert decoded.randomness_hex == entropy_hex
    assert decoded.datetime == datetime(1970, 1, 1, tzinfo=UTC) + timedelta(seconds=timestamp)


@pytest.mark.parametrize(
    ("name", "timestamp", "entropy_hex", "text", "binary_hex"), CONFORMANCE, ids=ROW_IDS
)
def test_generation_entrypoints_use_pinned_timestamp_and_entropy(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    timestamp: int,
    entropy_hex: str,
    text: str,
    binary_hex: str,
) -> None:
    randomness = bytes.fromhex(entropy_hex)
    requested: list[int] = []

    def fixed_entropy(count: int) -> bytes:
        requested.append(count)
        return randomness

    monkeypatch.setattr(secrets, "token_bytes", fixed_entropy)

    assert generate(timestamp=timestamp) == text
    assert generate_binary(timestamp=timestamp) == bytes.fromhex(binary_hex)
    assert Pikaid.generate(timestamp=timestamp) == Pikaid(
        timestamp=timestamp, randomness=randomness
    )
    assert requested == [RANDOMNESS_BYTES, RANDOMNESS_BYTES, RANDOMNESS_BYTES]


def test_matrix_ordering_agrees_across_value_text_and_binary_forms() -> None:
    values = [Pikaid(timestamp=row[1], randomness=_randomness(row)) for row in CONFORMANCE]
    expected_text = {row[3] for row in CONFORMANCE}
    expected_binary = {bytes.fromhex(row[4]) for row in CONFORMANCE}

    assert {value.to_string() for value in values} == expected_text
    assert {value.to_binary() for value in values} == expected_binary

    for left, right in combinations(values, 2):
        assert (left < right) == (left.to_string() < right.to_string())
        assert (left < right) == (left.to_binary() < right.to_binary())
        assert (left == right) == (left.to_string() == right.to_string())
        assert (left == right) == (left.to_binary() == right.to_binary())


def test_ascending_and_descending_rows_sort_chronologically() -> None:
    ordered = sorted(CONFORMANCE, key=lambda row: (row[1], _randomness(row)))
    texts = [row[3] for row in ordered]
    binaries = [bytes.fromhex(row[4]) for row in ordered]
    values = [Pikaid(timestamp=row[1], randomness=_randomness(row)) for row in ordered]

    assert texts == sorted(texts)
    assert binaries == sorted(binaries)
    assert values == sorted(values)
    assert texts[0] == "00000000000000000000000000"
    assert texts[-1] == "zzzzzzz7oiylpimjg5u2ca1ypr"


INVALID_TEXT: list[tuple[str, str]] = [
    ("empty", ""),
    ("one-character", "0"),
    ("25-characters", "0" * 25),
    ("27-characters", "0" * 27),
    ("1000-characters", "0" * 1000),
    ("uppercase-first", "A" + "0" * 25),
    ("uppercase-last", "0" * 25 + "A"),
    ("latin-non-ascii", "0" * 25 + "\u00e9"),
    ("fullwidth-digit", "0" * 25 + "\uff10"),
    ("zero-width-space", "0" * 25 + "\u200b"),
    ("nul", "0" * 25 + "\x00"),
    ("space", "0" * 25 + " "),
    ("carriage-return", "0" * 25 + "\r"),
    ("line-feed", "0" * 25 + "\n"),
    ("crlf-suffix", "0" * 24 + "\r\n"),
    ("tab", "0" * 25 + "\t"),
    ("punctuation", "0" * 25 + "-"),
    ("suffix-2-pow-96", "0000000" + encode_base36(2**96, 19)),
    ("suffix-2-pow-96-plus-1", "0000000" + encode_base36(2**96 + 1, 19)),
    ("suffix-36-pow-19-minus-1", "0000000" + "z" * 19),
    ("suffix-max-plus-one", "0000000" + encode_base36(MAX_RANDOMNESS + 1, 19)),
]

INVALID_TEXT_IDS = [case[0] for case in INVALID_TEXT]


@pytest.mark.parametrize(("name", "value"), INVALID_TEXT, ids=INVALID_TEXT_IDS)
def test_invalid_text_is_rejected_by_every_text_entrypoint(name: str, value: str) -> None:
    expected_shape = len(value) == STRING_LENGTH and all(
        character in ALPHABET for character in value
    )

    with pytest.raises(PikaidError):
        parse(value)
    with pytest.raises(PikaidError):
        Pikaid.parse(value)
    with pytest.raises(PikaidError):
        to_binary(value)

    assert is_valid(value) is False
    assert is_well_formed(value) is expected_shape


@pytest.mark.parametrize(
    "value",
    [None, 0, 1.5, True, b"0" * 26, bytearray(b"0" * 26), memoryview(b"0" * 26), [], {}, object()],
)
def test_invalid_text_types_are_rejected(value: object) -> None:
    with pytest.raises(TypeError):
        parse(value)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Pikaid.parse(value)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        to_binary(value)  # type: ignore[arg-type]
    assert is_valid(value) is False
    assert is_well_formed(value) is False


INVALID_BINARY: list[tuple[str, bytes]] = [
    ("empty", b""),
    ("one-byte", b"\x00"),
    ("16-bytes", bytes(16)),
    ("18-bytes", bytes(18)),
    ("32-bytes", bytes(32)),
    (
        "timestamp-max-plus-one",
        (MAX_TIMESTAMP + 1).to_bytes(5, "big") + bytes(RANDOMNESS_BYTES),
    ),
    (
        "timestamp-2-pow-40-minus-1",
        (2**40 - 1).to_bytes(5, "big") + bytes(RANDOMNESS_BYTES),
    ),
    ("timestamp-all-ff", b"\xff" * 5 + bytes(RANDOMNESS_BYTES)),
]

INVALID_BINARY_IDS = [case[0] for case in INVALID_BINARY]


@pytest.mark.parametrize(("name", "value"), INVALID_BINARY, ids=INVALID_BINARY_IDS)
def test_invalid_binary_is_rejected_by_every_binary_entrypoint(name: str, value: bytes) -> None:
    with pytest.raises(PikaidError):
        from_binary(value)
    with pytest.raises(PikaidError):
        Pikaid.from_binary(value)


@pytest.mark.parametrize("value", [None, 0, 1.5, True, "0" * 17, [0] * 17, (0,) * 17, object()])
def test_invalid_binary_types_are_rejected(value: object) -> None:
    with pytest.raises(TypeError):
        from_binary(value)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Pikaid.from_binary(value)  # type: ignore[arg-type]


def test_shape_only_check_does_not_imply_semantic_validity() -> None:
    overflow = "0000000" + encode_base36(2**96, 19)
    assert is_well_formed(overflow) is True
    assert is_valid(overflow) is False
    with pytest.raises(PikaidError):
        parse(overflow)
    with pytest.raises(PikaidError):
        to_binary(overflow)


@pytest.mark.parametrize(
    "timestamp",
    [-1, MAX_TIMESTAMP + 1, 2**40, 2**63, 10**100, -(10**100)],
)
def test_timestamp_range_is_enforced_for_values_and_generation(
    monkeypatch: pytest.MonkeyPatch, timestamp: int
) -> None:
    def forbidden(count: int) -> bytes:
        raise AssertionError("entropy must not be read for an invalid timestamp")

    monkeypatch.setattr(secrets, "token_bytes", forbidden)

    with pytest.raises(PikaidError):
        Pikaid(timestamp=timestamp, randomness=bytes(RANDOMNESS_BYTES))
    with pytest.raises(PikaidError):
        generate(timestamp=timestamp)
    with pytest.raises(PikaidError):
        generate_binary(timestamp=timestamp)
    with pytest.raises(PikaidError):
        Pikaid.generate(timestamp=timestamp)


@pytest.mark.parametrize("timestamp", [True, False, 1.0, "1700000000", object()])
def test_non_integer_timestamp_is_rejected_without_entropy(
    monkeypatch: pytest.MonkeyPatch, timestamp: Any
) -> None:
    def forbidden(count: int) -> bytes:
        raise AssertionError("entropy must not be read for an invalid timestamp")

    monkeypatch.setattr(secrets, "token_bytes", forbidden)
    with pytest.raises(TypeError):
        generate(timestamp=timestamp)
    with pytest.raises(TypeError):
        generate_binary(timestamp=timestamp)
    with pytest.raises(TypeError):
        Pikaid.generate(timestamp=timestamp)


def test_mutable_binary_input_is_copied_not_aliased() -> None:
    binary = bytearray.fromhex("006553f10000112233445566778899aabb")
    parsed = from_binary(binary)
    binary[:] = b"\x00" * len(binary)

    assert parsed.to_binary().hex() == "006553f10000112233445566778899aabb"
    assert parsed.timestamp == 1_700_000_000
    assert parsed.randomness.hex() == "00112233445566778899aabb"
