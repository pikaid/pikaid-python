"""Shared test helpers: independent oracles and fixture locations."""

from __future__ import annotations

from pathlib import Path

VECTOR_DIR = Path(__file__).parent / "vectors"
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def encode_base36(value: int, width: int) -> str:
    """Independent, test-side Base36 encoder used as an oracle.

    This intentionally does not import the implementation under test.
    """
    if value < 0:
        raise ValueError("value must be non-negative")
    digits = ""
    remaining = value
    while remaining:
        remaining, digit = divmod(remaining, 36)
        digits = ALPHABET[digit] + digits
    if len(digits) > width:
        raise ValueError("value does not fit in width")
    return digits.rjust(width, "0")


def make_id(timestamp: int, randomness: bytes) -> str:
    """Build the expected string form independently of the package."""
    if len(randomness) != 12:
        raise ValueError("randomness must be 12 bytes")
    return encode_base36(timestamp, 7) + encode_base36(int.from_bytes(randomness, "big"), 19)
