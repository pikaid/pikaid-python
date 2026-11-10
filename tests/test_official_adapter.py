"""Protocol tests for the test-only JSON-Lines conformance bridge.

These tests exercise ``tests/official/adapter.py`` as a real subprocess over the
wire, exactly as the official runner does.  They never re-implement encoding or
validation: every assertion checks that the bridge faithfully forwards the
public ``pikaid`` API and maps its documented exceptions to protocol errors.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import pikaid

ADAPTER = Path(__file__).parent / "official" / "adapter.py"

EXPECTED_CAPABILITIES = {
    "generate_string",
    "text_to_binary",
    "binary_to_text",
    "boolean_validation",
    "format_only_validation",
    "parse_components",
    "parse_datetime",
    "generate_with_timestamp",
    "generate_binary",
    "generate_binary_with_timestamp",
    "public_compare",
    "csprng_failure_injection",
}


def _adapter_env() -> dict[str, str]:
    """Make the subprocess import the same installed package under test."""
    env = dict(os.environ)
    package_root = Path(pikaid.__file__).resolve().parent.parent
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{package_root}{os.pathsep}{existing}" if existing else str(package_root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _run(requests: list[dict[str, Any] | str], *, timeout: float = 60.0) -> list[dict[str, Any]]:
    lines = [request if isinstance(request, str) else json.dumps(request) for request in requests]
    completed = subprocess.run(
        [sys.executable, str(ADAPTER)],
        input="\n".join(lines) + "\n",
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_adapter_env(),
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    responses = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    assert len(responses) == len(requests)
    return responses


def _ok(response: dict[str, Any]) -> Any:
    assert response["ok"] is True, response
    return response["value"]


def _error(response: dict[str, Any]) -> dict[str, str]:
    assert response["ok"] is False, response
    return response["error"]


def test_hello_advertises_protocol_v1_and_every_capability() -> None:
    (response,) = _run([{"request_id": 7, "operation": "hello", "arguments": {}}])

    assert response["request_id"] == 7
    value = _ok(response)
    assert value["protocol_version"] == 1
    assert set(value["capabilities"]) == EXPECTED_CAPABILITIES
    assert len(value["capabilities"]) == len(set(value["capabilities"]))


def test_mandatory_operations_round_trip_text_and_binary() -> None:
    responses = _run(
        [
            {"request_id": 1, "operation": "generate_string", "arguments": {}},
            {"request_id": 2, "operation": "text_to_binary", "arguments": {"text": "0" * 26}},
            {
                "request_id": 3,
                "operation": "binary_to_text",
                "arguments": {"binary_hex": "00" * 17},
            },
        ]
    )

    generated = _ok(responses[0])
    assert isinstance(generated, str) and len(generated) == 26
    assert pikaid.is_valid(generated)

    assert _ok(responses[1]) == "00" * 17
    assert _ok(responses[2]) == "0" * 26


def test_generation_with_explicit_timestamp_and_binary_forms() -> None:
    timestamp = 1_700_000_000
    responses = _run(
        [
            {
                "request_id": 1,
                "operation": "generate_with_timestamp",
                "arguments": {"timestamp_seconds": timestamp},
            },
            {
                "request_id": 2,
                "operation": "generate_binary_with_timestamp",
                "arguments": {"timestamp_seconds": timestamp},
            },
            {"request_id": 3, "operation": "generate_binary", "arguments": {}},
        ]
    )

    value = _ok(responses[0])
    assert len(value) == 26
    assert pikaid.parse(value).timestamp == timestamp

    binary_hex = _ok(responses[1])
    assert len(binary_hex) == 34
    assert int(binary_hex[:10], 16) == timestamp
    assert pikaid.from_binary(bytes.fromhex(binary_hex)).timestamp == timestamp

    assert len(_ok(responses[2])) == 34


def test_validation_capabilities_return_real_library_results() -> None:
    valid = "0" * 26
    responses = _run(
        [
            {"request_id": 1, "operation": "boolean_validation", "arguments": {"text": valid}},
            {
                "request_id": 2,
                "operation": "boolean_validation",
                "arguments": {"text": "0" * 27},
            },
            {"request_id": 3, "operation": "format_only_validation", "arguments": {"text": valid}},
            {
                "request_id": 4,
                "operation": "format_only_validation",
                "arguments": {"text": "0" * 27},
            },
        ]
    )

    assert _ok(responses[0]) is True
    assert _ok(responses[1]) is False
    assert _ok(responses[2]) is True
    assert _ok(responses[3]) is False


def test_parse_components_and_compare_use_public_api() -> None:
    low, high = "0" * 26, "1" + "0" * 25
    responses = _run(
        [
            {"request_id": 1, "operation": "parse_components", "arguments": {"text": low}},
            {
                "request_id": 2,
                "operation": "public_compare",
                "arguments": {"a": low, "b": high},
            },
        ]
    )

    components = _ok(responses[0])
    assert components["timestamp_seconds"] == 0
    assert components["randomness_hex"] == "0" * 24
    assert components["datetime_utc"] == "1970-01-01T00:00:00Z"
    assert _ok(responses[1]) == -1


def test_documented_invalid_values_map_to_invalid_input() -> None:
    responses = _run(
        [
            {"request_id": 1, "operation": "text_to_binary", "arguments": {"text": "short"}},
            {
                "request_id": 2,
                "operation": "text_to_binary",
                "arguments": {"text": "z" * 26},
            },
            {
                "request_id": 3,
                "operation": "binary_to_text",
                "arguments": {"binary_hex": "00"},
            },
            {
                "request_id": 4,
                "operation": "generate_with_timestamp",
                "arguments": {"timestamp_seconds": -1},
            },
        ]
    )

    for response in responses:
        assert _error(response)["category"] == "invalid_input", response


def test_csprng_failure_injection_proves_generation_fails_closed() -> None:
    responses = _run(
        [
            {
                "request_id": 1,
                "operation": "inject_fault",
                "arguments": {"fault": "csprng_failure", "active": True},
            },
            {"request_id": 2, "operation": "generate_string", "arguments": {}},
            {"request_id": 3, "operation": "generate_binary", "arguments": {}},
            {
                "request_id": 4,
                "operation": "inject_fault",
                "arguments": {"fault": "csprng_failure", "active": False},
            },
            {"request_id": 5, "operation": "generate_string", "arguments": {}},
        ]
    )

    assert _ok(responses[0]) == {"fault": "csprng_failure", "active": True}
    assert _error(responses[1])["category"] == "entropy_unavailable"
    assert _error(responses[2])["category"] == "entropy_unavailable"
    assert _ok(responses[3]) == {"fault": "csprng_failure", "active": False}
    assert pikaid.is_valid(_ok(responses[4]))


def test_unknown_operation_and_malformed_requests_are_reported_not_fatal() -> None:
    responses = _run(
        [
            {"request_id": 1, "operation": "no_such_operation", "arguments": {}},
            {"request_id": 2, "operation": "text_to_binary", "arguments": []},
            {"request_id": 3, "operation": "generate_string"},
            "{not json",
            {"request_id": 5, "operation": "hello", "arguments": {}},
        ]
    )

    assert _error(responses[0])["category"] == "unsupported_operation"
    assert _error(responses[1])["category"] == "invalid_input"
    assert _error(responses[2])["category"] == "invalid_input"
    assert responses[3]["ok"] is False
    assert _ok(responses[4])["protocol_version"] == 1


def test_boolean_arguments_are_not_accepted_as_integers() -> None:
    (response,) = _run(
        [
            {
                "request_id": 1,
                "operation": "generate_with_timestamp",
                "arguments": {"timestamp_seconds": True},
            }
        ]
    )

    assert _error(response)["category"] == "invalid_input"


@pytest.mark.parametrize(
    ("operation", "public_function"),
    [("generate_string", "generate"), ("generate_binary", "generate_binary")],
)
def test_unexpected_internal_errors_are_not_mislabelled_as_rejections(
    operation: str, public_function: str
) -> None:
    """A broken library call must surface as ``internal_error``, never ``invalid_input``."""
    script = f"""
import json, sys
sys.path.insert(0, {str(ADAPTER.parent)!r})
import adapter
import pikaid

def explode(*args, **kwargs):
    raise RuntimeError("synthetic internal failure")

setattr(pikaid, {public_function!r}, explode)
sys.stdin = iter([json.dumps({{"request_id": 1, "operation": {operation!r}, "arguments": {{}}}})])
adapter.main()
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
        env=_adapter_env(),
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    response = json.loads(completed.stdout.strip())
    assert response["error"]["category"] == "internal_error"


def test_adapter_contains_no_identifier_logic() -> None:
    """The bridge must delegate; it must not encode, decode or validate itself."""
    source = ADAPTER.read_text(encoding="utf-8")
    forbidden = ("def _encode", "def _decode", "base36", "int.from_bytes(", "to_bytes(")
    for token in forbidden:
        assert token not in source, token
