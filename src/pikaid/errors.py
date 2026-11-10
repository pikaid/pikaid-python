"""Exceptions raised by :mod:`pikaid`."""

from __future__ import annotations

__all__ = [
    "EntropySourceError",
    "InvalidPikaidError",
    "InvalidTimestampError",
    "PikaidError",
]


class PikaidError(Exception):
    """Base class for every error raised by :mod:`pikaid`."""


class InvalidPikaidError(PikaidError, ValueError):
    """Raised when a string or binary value is not a valid pikaid.

    The message explains which part of the value failed validation.  Invalid
    input is never truncated, padded, or silently normalized.
    """


class InvalidTimestampError(PikaidError, ValueError):
    """Raised when a timestamp is outside ``0..MAX_TIMESTAMP``.

    Attributes:
        timestamp: The rejected integer value.
    """

    def __init__(self, timestamp: int, message: str) -> None:
        super().__init__(message)
        self.timestamp = timestamp


class EntropySourceError(PikaidError, RuntimeError):
    """Raised when the operating-system CSPRNG cannot provide 12 bytes.

    Generation fails closed: no identifier is returned when the random source
    raises or returns an unexpected amount of data.
    """
