"""CSPRNG-backed generation, determinism, failure, and sanity tests."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable

import pytest

import pikaid._core as core
from pikaid import (
    BINARY_LENGTH,
    MAX_TIMESTAMP,
    RANDOMNESS_BYTES,
    STRING_LENGTH,
    EntropySourceError,
    InvalidTimestampError,
    Pikaid,
    generate,
    generate_binary,
    is_valid,
    parse,
)

FIXED_TIMESTAMP = 1_700_000_000
FIXED_ENTROPY = bytes.fromhex("00112233445566778899aabb")
FIXED_ID = "0s44we8002loz3po6mcf6vsn23"
FIXED_BINARY = bytes.fromhex("006553f10000112233445566778899aabb")


def _fix_clock(monkeypatch: pytest.MonkeyPatch, timestamp: int = FIXED_TIMESTAMP) -> None:
    monkeypatch.setattr(core, "_now_seconds", lambda: timestamp)


def _fix_entropy(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    calls: list[int] = []

    def token_bytes(count: int) -> bytes:
        calls.append(count)
        return FIXED_ENTROPY

    monkeypatch.setattr(secrets, "token_bytes", token_bytes)
    return calls


def test_generate_with_fixed_clock_and_entropy_matches_official_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fix_clock(monkeypatch)
    calls = _fix_entropy(monkeypatch)

    assert generate() == FIXED_ID
    assert calls == [RANDOMNESS_BYTES]


def test_generate_with_explicit_timestamp_matches_official_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fix_entropy(monkeypatch)
    assert generate(timestamp=FIXED_TIMESTAMP) == FIXED_ID
    assert calls == [RANDOMNESS_BYTES]


def test_generate_binary_with_explicit_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fix_entropy(monkeypatch)
    assert generate_binary(timestamp=FIXED_TIMESTAMP) == FIXED_BINARY
    assert len(generate_binary(timestamp=FIXED_TIMESTAMP)) == BINARY_LENGTH


def test_generate_binary_without_timestamp_uses_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fix_clock(monkeypatch)
    _fix_entropy(monkeypatch)
    assert generate_binary() == FIXED_BINARY


def test_value_object_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    _fix_clock(monkeypatch)
    _fix_entropy(monkeypatch)
    generated = Pikaid.generate()
    assert isinstance(generated, Pikaid)
    assert generated.timestamp == FIXED_TIMESTAMP
    assert generated.randomness == FIXED_ENTROPY
    assert generated.to_string() == FIXED_ID
    assert generated.to_binary() == FIXED_BINARY


def test_generate_at_timestamp_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    _fix_entropy(monkeypatch)

    for timestamp in (0, 1, MAX_TIMESTAMP):
        value = generate(timestamp=timestamp)
        assert parse(value).timestamp == timestamp
        assert is_valid(value)


def test_default_clock_uses_current_whole_seconds() -> None:
    before = time.time_ns() // 1_000_000_000
    value = generate()
    after = time.time_ns() // 1_000_000_000

    parsed = parse(value)
    assert before - 1 <= parsed.timestamp <= after + 1
    assert len(value) == STRING_LENGTH
    assert len(parsed.randomness) == RANDOMNESS_BYTES


def test_generated_identifier_is_canonical_and_round_trips() -> None:
    value = generate()
    parsed = parse(value)
    assert len(value) == STRING_LENGTH
    assert value == value.lower()
    assert all(character in "0123456789abcdefghijklmnopqrstuvwxyz" for character in value)
    assert len(parsed.to_binary()) == BINARY_LENGTH
    assert Pikaid.from_binary(parsed.to_binary()) == parsed


def test_many_generated_values_within_one_second_are_distinct_and_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fix_clock(monkeypatch)
    values = [generate() for _ in range(1_000)]

    assert len(set(values)) == len(values)
    assert all(len(value) == STRING_LENGTH for value in values)
    assert all(value.startswith("0s44we8") for value in values)
    assert all(is_valid(value) for value in values)
    assert len({parse(value).randomness for value in values}) == len(values)


def test_generation_requests_exactly_twelve_entropy_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fix_clock(monkeypatch)
    calls = _fix_entropy(monkeypatch)
    generate()
    generate_binary()
    assert calls == [RANDOMNESS_BYTES, RANDOMNESS_BYTES]


def test_invalid_supplied_timestamp_fails_before_entropy_is_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(count: int) -> bytes:
        raise AssertionError("the entropy source must not be consulted")

    monkeypatch.setattr(secrets, "token_bytes", forbidden)

    for timestamp in (-1, MAX_TIMESTAMP + 1, 2**40):
        with pytest.raises(InvalidTimestampError):
            generate(timestamp=timestamp)


@pytest.mark.parametrize("timestamp", [True, False, 1.0, "1700000000", object()])
def test_non_integer_timestamp_is_rejected_before_entropy(
    monkeypatch: pytest.MonkeyPatch, timestamp: object
) -> None:
    def forbidden(count: int) -> bytes:
        raise AssertionError("the entropy source must not be consulted")

    monkeypatch.setattr(secrets, "token_bytes", forbidden)
    with pytest.raises(TypeError):
        generate(timestamp=timestamp)  # type: ignore[arg-type]


@pytest.mark.parametrize("now", [-1, MAX_TIMESTAMP + 1])
def test_out_of_range_clock_fails_closed(monkeypatch: pytest.MonkeyPatch, now: int) -> None:
    _fix_clock(monkeypatch, now)
    with pytest.raises(InvalidTimestampError):
        generate()


def test_non_integer_clock_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core, "_now_seconds", lambda: 1.5)
    with pytest.raises(TypeError):
        generate()


def _raise_os_error(count: int) -> bytes:
    raise OSError("simulated CSPRNG failure")


def _raise_runtime_error(count: int) -> bytes:
    raise RuntimeError("simulated CSPRNG failure")


@pytest.mark.parametrize("source", [_raise_os_error, _raise_runtime_error])
def test_cryptographic_source_failure_is_wrapped_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    source: Callable[[int], bytes],
) -> None:
    _fix_clock(monkeypatch)
    monkeypatch.setattr(secrets, "token_bytes", source)

    with pytest.raises(EntropySourceError) as caught:
        generate()
    assert isinstance(caught.value.__cause__, (OSError, RuntimeError))
    assert isinstance(caught.value, RuntimeError)


@pytest.mark.parametrize(
    "source",
    [
        lambda count: b"\x00" * (count - 1),
        lambda count: b"\x00" * (count + 1),
        lambda count: b"\x00" * count * 2,
        lambda count: bytearray(count),
        lambda count: "0" * count,
        lambda count: None,
    ],
    ids=["short", "long", "double", "bytearray", "str", "none"],
)
def test_malformed_entropy_source_output_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    source: Callable[[int], object],
) -> None:
    _fix_clock(monkeypatch)
    monkeypatch.setattr(secrets, "token_bytes", source)

    with pytest.raises(EntropySourceError):
        generate()
    with pytest.raises(EntropySourceError):
        generate_binary()
