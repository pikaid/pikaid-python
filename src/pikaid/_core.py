"""Core pikaid value type, encoding, decoding, and generation.

The public names in this module are re-exported from :mod:`pikaid`.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .errors import EntropySourceError, InvalidPikaidError, InvalidTimestampError

__all__ = [
    "ALPHABET",
    "BINARY_LENGTH",
    "MAX_RANDOMNESS",
    "MAX_TIMESTAMP",
    "RANDOMNESS_BYTES",
    "RANDOMNESS_CHARS",
    "STRING_LENGTH",
    "TIMESTAMP_BYTES",
    "TIMESTAMP_CHARS",
    "Pikaid",
    "from_binary",
    "generate",
    "generate_binary",
    "is_valid",
    "is_well_formed",
    "parse",
    "to_binary",
]

#: Lowercase Base36 alphabet in ascending digit order.
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"

#: Total width of the canonical string form.
STRING_LENGTH = 26
#: Fixed width of the timestamp prefix in the string form.
TIMESTAMP_CHARS = 7
#: Fixed width of the randomness suffix in the string form.
RANDOMNESS_CHARS = 19

#: Total size of the canonical binary form.
BINARY_LENGTH = 17
#: Width of the big-endian timestamp field in the binary form.
TIMESTAMP_BYTES = 5
#: Number of raw randomness bytes.
RANDOMNESS_BYTES = 12

#: Largest valid timestamp: ``36**7 - 1`` (4453-04-05 15:21:35 UTC).
MAX_TIMESTAMP = 36**TIMESTAMP_CHARS - 1
#: Largest valid randomness value: ``2**96 - 1``.
MAX_RANDOMNESS = (1 << (RANDOMNESS_BYTES * 8)) - 1

_RADIX = len(ALPHABET)
_CHAR_VALUES = {character: value for value, character in enumerate(ALPHABET)}
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _ensure_timestamp(timestamp: object) -> int:
    """Validate a caller-supplied timestamp without lossy coercion."""
    if isinstance(timestamp, bool) or not isinstance(timestamp, int):
        raise TypeError(f"timestamp must be an int, not {type(timestamp).__name__}")
    if timestamp < 0:
        raise InvalidTimestampError(
            timestamp,
            f"timestamp {timestamp} is negative; pikaid timestamps start at 0",
        )
    if timestamp > MAX_TIMESTAMP:
        raise InvalidTimestampError(
            timestamp,
            f"timestamp {timestamp} exceeds the maximum {MAX_TIMESTAMP} (36**7 - 1)",
        )
    return timestamp


def _encode_base36(value: int, width: int) -> str:
    """Encode a non-negative integer as fixed-width lowercase Base36."""
    digits: list[str] = []
    remaining = value
    while remaining:
        remaining, digit = divmod(remaining, _RADIX)
        digits.append(ALPHABET[digit])
    return "".join(reversed(digits)).rjust(width, "0")


def _decode_base36(text: str, field: str) -> int:
    """Decode already-validated lowercase Base36 text."""
    value = 0
    for position, character in enumerate(text):
        digit = _CHAR_VALUES.get(character)
        if digit is None:
            raise InvalidPikaidError(
                f"invalid character {character!r} in {field} at position {position}; "
                "expected lowercase base36 [0-9a-z]"
            )
        value = value * _RADIX + digit
    return value


def _validate_string_shape(value: str) -> None:
    if len(value) != STRING_LENGTH:
        raise InvalidPikaidError(
            f"pikaid must be exactly {STRING_LENGTH} characters, got {len(value)}"
        )
    for position, character in enumerate(value):
        if character not in _CHAR_VALUES:
            raise InvalidPikaidError(
                f"invalid character {character!r} at position {position}; "
                "expected lowercase base36 [0-9a-z]"
            )


def _parse_string(value: str) -> tuple[int, bytes]:
    _validate_string_shape(value)

    # Seven Base36 digits cannot exceed MAX_TIMESTAMP, but run the shared range
    # validator so the rule is enforced in one place for both representations.
    timestamp = _ensure_timestamp(_decode_base36(value[:TIMESTAMP_CHARS], "timestamp"))

    randomness = _decode_base36(value[TIMESTAMP_CHARS:], "randomness")
    if randomness > MAX_RANDOMNESS:
        raise InvalidPikaidError(
            "randomness suffix exceeds 96 bits (2**96 - 1); "
            "the value is outside the valid pikaid range"
        )

    return timestamp, randomness.to_bytes(RANDOMNESS_BYTES, "big")


def _random_bytes(count: int) -> bytes:
    """Read exactly ``count`` bytes from the operating-system CSPRNG.

    Any source failure, wrong type, or wrong length becomes
    :class:`~pikaid.EntropySourceError` so generation fails closed.
    """
    try:
        data = secrets.token_bytes(count)
    except Exception as error:  # pragma: no cover - exercised with monkeypatching
        raise EntropySourceError(
            "the cryptographic random number generator failed; no pikaid was generated"
        ) from error
    if not isinstance(data, bytes):
        raise EntropySourceError(
            "the cryptographic random number generator returned "
            f"{type(data).__name__}, expected bytes"
        )
    if len(data) != count:
        raise EntropySourceError(
            f"the cryptographic random number generator returned {len(data)} bytes, "
            f"expected {count}"
        )
    return data


def _now_seconds() -> int:
    """Return the current Unix time as whole seconds."""
    return time.time_ns() // 1_000_000_000


def _generate(timestamp: int | None) -> tuple[int, bytes]:
    if timestamp is None:
        timestamp = _now_seconds()
    timestamp = _ensure_timestamp(timestamp)
    return timestamp, _random_bytes(RANDOMNESS_BYTES)


@dataclass(frozen=True, order=True)
class Pikaid:
    """An immutable, validated pikaid value.

    Args:
        timestamp: Whole Unix seconds in ``0..MAX_TIMESTAMP``.
        randomness: Exactly 12 raw entropy bytes.

    The value compares and hashes by ``(timestamp, randomness)``, which is the
    same unsigned bytewise order as the 17-byte binary form.  Two identifiers
    created in the same second are ordered by randomness, not by creation time.
    """

    timestamp: int
    randomness: bytes

    def __post_init__(self) -> None:
        _ensure_timestamp(self.timestamp)
        if not isinstance(self.randomness, bytes):
            raise TypeError(f"randomness must be bytes, not {type(self.randomness).__name__}")
        if len(self.randomness) != RANDOMNESS_BYTES:
            raise InvalidPikaidError(
                f"randomness must be exactly {RANDOMNESS_BYTES} bytes, got {len(self.randomness)}"
            )

    @classmethod
    def generate(cls, timestamp: int | None = None) -> Pikaid:
        """Create a new value using the CSPRNG and the current or supplied time."""
        generated_timestamp, randomness = _generate(timestamp)
        return cls(timestamp=generated_timestamp, randomness=randomness)

    @classmethod
    def parse(cls, value: str) -> Pikaid:
        """Strictly decode a 26-character pikaid string."""
        if not isinstance(value, str):
            raise TypeError(f"pikaid string must be str, not {type(value).__name__}")
        timestamp, randomness = _parse_string(value)
        return cls(timestamp=timestamp, randomness=randomness)

    @classmethod
    def from_binary(cls, value: bytes | bytearray | memoryview) -> Pikaid:
        """Strictly decode a 17-byte pikaid binary value."""
        if not isinstance(value, (bytes, bytearray, memoryview)):
            raise TypeError(
                f"binary pikaid must be bytes, bytearray, or memoryview, not {type(value).__name__}"
            )
        raw = bytes(value)
        if len(raw) != BINARY_LENGTH:
            raise InvalidPikaidError(
                f"binary pikaid must be exactly {BINARY_LENGTH} bytes, got {len(raw)}"
            )
        timestamp = int.from_bytes(raw[:TIMESTAMP_BYTES], "big")
        if timestamp > MAX_TIMESTAMP:
            raise InvalidTimestampError(
                timestamp,
                f"binary timestamp {timestamp} exceeds the maximum {MAX_TIMESTAMP} (36**7 - 1)",
            )
        return cls(timestamp=timestamp, randomness=raw[TIMESTAMP_BYTES:])

    @property
    def randomness_hex(self) -> str:
        """The 12 randomness bytes as 24 lowercase hexadecimal characters."""
        return self.randomness.hex()

    @property
    def datetime(self) -> datetime:
        """The timestamp as a timezone-aware UTC :class:`datetime.datetime`.

        The value is computed arithmetically from the Unix epoch, so it works
        across platforms even for the maximum timestamp in year 4453.
        """
        return _EPOCH + timedelta(seconds=self.timestamp)

    def to_string(self) -> str:
        """Return the canonical 26-character lowercase Base36 form."""
        return _encode_base36(self.timestamp, TIMESTAMP_CHARS) + _encode_base36(
            int.from_bytes(self.randomness, "big"),
            RANDOMNESS_CHARS,
        )

    def to_binary(self) -> bytes:
        """Return the canonical 17-byte big-endian binary form."""
        return self.timestamp.to_bytes(TIMESTAMP_BYTES, "big") + self.randomness

    def __str__(self) -> str:
        return self.to_string()


def generate(timestamp: int | None = None) -> str:
    """Generate a pikaid string.

    Args:
        timestamp: Whole Unix seconds.  ``None`` (the default) uses the current
            UTC time.  Explicit values must be in ``0..MAX_TIMESTAMP``.

    Raises:
        InvalidTimestampError: If ``timestamp`` is outside the valid range.
        TypeError: If ``timestamp`` is not an integer or is a ``bool``.
        EntropySourceError: If the CSPRNG fails; no value is returned.
    """
    return Pikaid.generate(timestamp).to_string()


def generate_binary(timestamp: int | None = None) -> bytes:
    """Generate a pikaid directly in its 17-byte binary form."""
    return Pikaid.generate(timestamp).to_binary()


def parse(value: str) -> Pikaid:
    """Strictly parse a pikaid string, raising on any spec violation."""
    return Pikaid.parse(value)


def from_binary(value: bytes | bytearray | memoryview) -> Pikaid:
    """Strictly parse a 17-byte pikaid binary value."""
    return Pikaid.from_binary(value)


def to_binary(value: str | Pikaid) -> bytes:
    """Convert a pikaid string or :class:`Pikaid` to 17 bytes."""
    if isinstance(value, Pikaid):
        return value.to_binary()
    if not isinstance(value, str):
        raise TypeError(f"value must be a pikaid string or Pikaid, not {type(value).__name__}")
    return Pikaid.parse(value).to_binary()


def is_valid(value: object) -> bool:
    """Return whether ``value`` is a fully valid pikaid string.

    This is the semantic check: exact length, lowercase Base36 alphabet, and a
    randomness suffix within 96 bits.  Non-string values return ``False``.
    """
    if not isinstance(value, str):
        return False
    try:
        _parse_string(value)
    except (InvalidPikaidError, InvalidTimestampError):
        return False
    return True


def is_well_formed(value: object) -> bool:
    """Return whether ``value`` has the pikaid *shape* (length and alphabet).

    This deliberately does **not** check whether the randomness suffix fits in
    96 bits.  Use :func:`is_valid` for full specification validity.
    """
    if not isinstance(value, str) or len(value) != STRING_LENGTH:
        return False
    return all(character in _CHAR_VALUES for character in value)
