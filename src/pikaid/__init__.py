"""Official Python implementation of the pikaid identifier format.

pikaid is an immutable, unversioned 26-character lowercase Base36 identifier:
a 7-character whole-second Unix timestamp followed by 19 characters encoding
96 bits of cryptographic randomness.  Its binary form is exactly 17 bytes.

Typical usage::

    from pikaid import generate, is_valid, parse, to_binary, from_binary

    value = generate()
    assert is_valid(value)
    parsed = parse(value)
    assert from_binary(to_binary(value)) == parsed

The canonical specification is pikaid-specs revision 1.0.4.
"""

from __future__ import annotations

from ._core import (
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
    from_binary,
    generate,
    generate_binary,
    is_valid,
    is_well_formed,
    parse,
    to_binary,
)
from .errors import (
    EntropySourceError,
    InvalidPikaidError,
    InvalidTimestampError,
    PikaidError,
)

__version__ = "1.0.0"

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
    "EntropySourceError",
    "InvalidPikaidError",
    "InvalidTimestampError",
    "Pikaid",
    "PikaidError",
    "__version__",
    "from_binary",
    "generate",
    "generate_binary",
    "is_valid",
    "is_well_formed",
    "parse",
    "to_binary",
]
