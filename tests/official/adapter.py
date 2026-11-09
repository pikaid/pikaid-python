#!/usr/bin/env python3
"""Test-only JSON-Lines bridge between the official PikaID conformance suite and
the real ``pikaid`` public API.

This file is *not* part of the distributed package and is never imported by
``pikaid`` itself.  It contains no identifier encoding, decoding, validation or
randomness logic: every operation delegates to a public function, class or
method, so the official suite exercises the library under test.

Protocol: https://github.com/pikaid/pikaid-specs/blob/059780cc0e5b113443812720d95c630649bf3aa3/conformance/docs/JSONL_ADAPTER_PROTOCOL.md

Invoke with, for example:

    python tests/official/adapter.py

One UTF-8 JSON object is read from stdin per line and exactly one JSON object is
written to stdout per request, flushed.  Diagnostics go to stderr only.
"""

from __future__ import annotations

import json
import re
import secrets
import sys
from collections.abc import Callable
from datetime import UTC
from typing import Any

import pikaid

PROTOCOL_VERSION = 1

CAPABILITIES = [
    # Mandatory operations.
    "generate_string",
    "text_to_binary",
    "binary_to_text",
    # Conditional operations, all backed by real public API.
    "boolean_validation",
    "format_only_validation",
    "parse_components",
    "parse_datetime",
    "generate_with_timestamp",
    "generate_binary",
    "generate_binary_with_timestamp",
    "public_compare",
    "csprng_failure_injection",
]

_HEX_34 = re.compile(r"[0-9a-f]{34}")

# Documented input-validation exceptions raised by the library.  ``TypeError``
# is intentionally excluded: the wire layer below already rejects non-string /
# non-integer arguments, so any ``TypeError`` escaping the library would be an
# unexpected internal failure, not a conformance rejection.
_INVALID_INPUT_ERRORS = (
    pikaid.InvalidPikaidError,
    pikaid.InvalidTimestampError,
)


class Rejected(Exception):
    """A documented invalid-input rejection mapped to ``invalid_input``."""


class EntropyUnavailable(Exception):
    """The library's CSPRNG failed and generation correctly failed closed."""


class Unsupported(Exception):
    """The request names an operation this bridge does not implement."""


# -- test-only CSPRNG fault seam ---------------------------------------------
# The production package has no RNG injection API and this bridge adds none.
# Fault injection is implemented entirely inside this test process by replacing
# ``secrets.token_bytes``, which is the real function the library calls.  That
# keeps the genuine ``_random_bytes`` failure path under test.

_REAL_TOKEN_BYTES: Callable[[int], bytes] = secrets.token_bytes


def _broken_token_bytes(count: int) -> bytes:
    raise OSError("injected CSPRNG failure (test-only)")


def _set_fault(active: bool) -> None:
    secrets.token_bytes = _broken_token_bytes if active else _REAL_TOKEN_BYTES


# -- operation handlers ------------------------------------------------------


def _require_str(arguments: dict[str, Any], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str):
        raise Rejected(f"argument {name!r} must be a string")
    return value


def _require_int(arguments: dict[str, Any], name: str) -> int:
    value = arguments.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise Rejected(f"argument {name!r} must be an integer")
    return value


def op_generate_string(arguments: dict[str, Any]) -> Any:
    return pikaid.generate()


def op_generate_with_timestamp(arguments: dict[str, Any]) -> Any:
    return pikaid.generate(_require_int(arguments, "timestamp_seconds"))


def op_generate_binary(arguments: dict[str, Any]) -> Any:
    return pikaid.generate_binary().hex()


def op_generate_binary_with_timestamp(arguments: dict[str, Any]) -> Any:
    return pikaid.generate_binary(_require_int(arguments, "timestamp_seconds")).hex()


def op_text_to_binary(arguments: dict[str, Any]) -> Any:
    return pikaid.to_binary(_require_str(arguments, "text")).hex()


def op_binary_to_text(arguments: dict[str, Any]) -> Any:
    binary_hex = _require_str(arguments, "binary_hex")
    if _HEX_34.fullmatch(binary_hex) is None:
        # Wire-format enforcement only: exactly 17 bytes of lowercase hex.
        raise Rejected("binary_hex must be exactly 34 lowercase hexadecimal digits")
    return pikaid.from_binary(bytes.fromhex(binary_hex)).to_string()


def op_boolean_validation(arguments: dict[str, Any]) -> Any:
    return bool(pikaid.is_valid(_require_str(arguments, "text")))


def op_format_only_validation(arguments: dict[str, Any]) -> Any:
    return bool(pikaid.is_well_formed(_require_str(arguments, "text")))


def op_parse_components(arguments: dict[str, Any]) -> Any:
    value = pikaid.parse(_require_str(arguments, "text"))
    return {
        "timestamp_seconds": value.timestamp,
        "randomness_hex": value.randomness_hex,
        "datetime_utc": value.datetime.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }


def op_public_compare(arguments: dict[str, Any]) -> Any:
    left = pikaid.parse(_require_str(arguments, "a"))
    right = pikaid.parse(_require_str(arguments, "b"))
    return (left > right) - (left < right)


def op_inject_fault(arguments: dict[str, Any]) -> Any:
    if arguments.get("fault") != "csprng_failure":
        raise Unsupported("only the csprng_failure fault is implemented")
    active = arguments.get("active")
    if not isinstance(active, bool):
        raise Rejected("argument 'active' must be a boolean")
    _set_fault(active)
    return {"fault": "csprng_failure", "active": active}


OPERATIONS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "generate_string": op_generate_string,
    "text_to_binary": op_text_to_binary,
    "binary_to_text": op_binary_to_text,
    "boolean_validation": op_boolean_validation,
    "format_only_validation": op_format_only_validation,
    "parse_components": op_parse_components,
    "generate_with_timestamp": op_generate_with_timestamp,
    "generate_binary": op_generate_binary,
    "generate_binary_with_timestamp": op_generate_binary_with_timestamp,
    "public_compare": op_public_compare,
    "inject_fault": op_inject_fault,
}


# -- protocol ----------------------------------------------------------------


def _write(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        return {
            "request_id": 0,
            "ok": False,
            "error": {"category": "internal_error", "message": "request must be a JSON object"},
        }
    request_id = request.get("request_id")
    if isinstance(request_id, bool) or not isinstance(request_id, int):
        request_id = 0
    operation = request.get("operation")
    arguments = request.get("arguments")

    if operation == "hello":
        return {
            "request_id": request_id,
            "ok": True,
            "value": {"protocol_version": PROTOCOL_VERSION, "capabilities": CAPABILITIES},
        }
    if not isinstance(arguments, dict):
        return {
            "request_id": request_id,
            "ok": False,
            "error": {"category": "invalid_input", "message": "arguments must be an object"},
        }
    handler = OPERATIONS.get(operation) if isinstance(operation, str) else None
    if handler is None:
        return {
            "request_id": request_id,
            "ok": False,
            "error": {
                "category": "unsupported_operation",
                "message": f"unsupported operation {operation!r}",
            },
        }

    try:
        value = handler(arguments)
    except Rejected as error:
        return {
            "request_id": request_id,
            "ok": False,
            "error": {"category": "invalid_input", "message": str(error)},
        }
    except _INVALID_INPUT_ERRORS as error:
        return {
            "request_id": request_id,
            "ok": False,
            "error": {"category": "invalid_input", "message": f"{type(error).__name__}: {error}"},
        }
    except pikaid.EntropySourceError as error:
        return {
            "request_id": request_id,
            "ok": False,
            "error": {
                "category": "entropy_unavailable",
                "message": f"{type(error).__name__}: {error}",
            },
        }
    # Unexpected failures must not be reported as input rejection.
    except Exception as error:
        return {
            "request_id": request_id,
            "ok": False,
            "error": {
                "category": "internal_error",
                "message": f"{type(error).__name__}: {error}",
            },
        }
    return {"request_id": request_id, "ok": True, "value": value}


def main() -> int:
    print(
        f"pikaid conformance adapter: pikaid {pikaid.__version__} from {pikaid.__file__}",
        file=sys.stderr,
    )
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError as error:
            _write(
                {
                    "request_id": 0,
                    "ok": False,
                    "error": {
                        "category": "internal_error",
                        "message": f"invalid JSON request: {error}",
                    },
                }
            )
            continue
        _write(handle(request))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
