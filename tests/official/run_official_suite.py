#!/usr/bin/env python3
"""Run the *pinned* official PikaID conformance suite against the real library.

This driver is test tooling, not part of the distributed package.  It never
encodes, decodes, validates or generates identifiers itself: every behavioral
assertion is made by the upstream suite through ``tests/official/adapter.py``,
which in turn calls the public ``pikaid`` API.

The suite is pinned to an immutable upstream commit.  The driver fails closed if
the checkout is not exactly that commit, if ``SHA256SUMS`` does not match, or if
the suite identity (status / suite revision / specification revision) is wrong.

Typical CI use::

    git init suite
    git -C suite remote add origin https://github.com/pikaid/pikaid-specs.git
    git -C suite -c core.autocrlf=false fetch --depth 1 origin <pinned-sha>
    git -C suite -c core.autocrlf=false checkout FETCH_HEAD
    python tests/official/run_official_suite.py \
        --suite suite/conformance \
        --report-json conformance-report.json \
        -- python tests/official/adapter.py

Exit codes are propagated from the upstream runner: ``0`` means every automated
check passed (with ``--automated-only``); it is **not** a conformance
certification and does not replace the independent security review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Immutable provenance pins.  Keep these in one place so a report can cite them.
PINNED_SUITE_COMMIT = "059780cc0e5b113443812720d95c630649bf3aa3"
PINNED_STATUS = "OFFICIAL"
PINNED_SUITE_REVISION = "1.0.0"
PINNED_SPEC_REVISION = "1.0.4"

EXPECTED_FIXTURES = {
    "valid": 596,
    "invalid-string": 258,
    "invalid-binary": 33,
    "ordering": 186,
    "generation": 12,
    "properties": 15,
}
#: Every file listed in the pinned ``SHA256SUMS``.  A missing entry is a
#: fail-closed error even when the remaining files still verify.
EXPECTED_CHECKSUMMED_FILES = 31


class SuiteError(RuntimeError):
    """The pinned suite cannot be trusted or a required capability is missing."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_suite_identity(conformance: Path) -> dict[str, Any]:
    """Validate checksums, manifest identity and fixture inventory."""
    sums_path = conformance / "SHA256SUMS"
    if not sums_path.is_file():
        raise SuiteError(f"missing checksum file: {sums_path}")

    verified = 0
    for raw_line in sums_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            expected, relative = line.split(None, 1)
        except ValueError as error:
            raise SuiteError(f"malformed SHA256SUMS line: {raw_line!r}") from error
        relative = relative.lstrip("*")
        target = conformance / relative
        if not target.is_file():
            raise SuiteError(f"checksum lists a missing file: {relative}")
        actual = _sha256(target)
        if actual != expected:
            raise SuiteError(
                f"checksum mismatch for {relative}: expected {expected}, got {actual} "
                "(check for CRLF conversion or a modified checkout)"
            )
        verified += 1

    if verified != EXPECTED_CHECKSUMMED_FILES:
        raise SuiteError(
            f"SHA256SUMS lists {verified} files, expected the pinned {EXPECTED_CHECKSUMMED_FILES}; "
            "a dropped entry would silently stop covering that file"
        )

    manifest = json.loads((conformance / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != PINNED_STATUS:
        raise SuiteError(f"suite status is {manifest.get('status')!r}, expected {PINNED_STATUS!r}")
    if manifest.get("package_revision") != PINNED_SUITE_REVISION:
        raise SuiteError(
            f"suite revision is {manifest.get('package_revision')!r}, "
            f"expected {PINNED_SUITE_REVISION!r}"
        )
    if manifest.get("spec_revision") != PINNED_SPEC_REVISION:
        raise SuiteError(
            f"spec revision is {manifest.get('spec_revision')!r}, expected {PINNED_SPEC_REVISION!r}"
        )

    inventory: dict[str, int] = {}
    for fixture in manifest.get("fixtures", []):
        relative = fixture["path"]
        declared = int(fixture["cases"])
        data = json.loads((conformance / relative).read_text(encoding="utf-8"))
        observed = len(data["cases"])
        if observed != declared:
            raise SuiteError(f"{relative}: manifest declares {declared} cases, found {observed}")
        inventory[Path(relative).stem] = observed

    if inventory != EXPECTED_FIXTURES:
        raise SuiteError(f"fixture inventory changed: {inventory} != {EXPECTED_FIXTURES}")

    commit = _git_commit(conformance)
    if commit is None:
        raise SuiteError(
            "the suite is not inside a Git checkout, so the immutable commit pin cannot be verified"
        )
    if commit != PINNED_SUITE_COMMIT:
        raise SuiteError(
            f"suite commit is {commit}, expected the immutable pin {PINNED_SUITE_COMMIT}"
        )

    return {
        "suite_commit": commit,
        "suite_commit_pinned": PINNED_SUITE_COMMIT,
        "suite_revision": PINNED_SUITE_REVISION,
        "spec_revision": PINNED_SPEC_REVISION,
        "status": PINNED_STATUS,
        "checksummed_files": verified,
        "fixtures": inventory,
        "fixture_total": sum(inventory.values()),
    }


def _git_commit(directory: Path) -> str | None:
    """Return HEAD when ``directory`` is the ``conformance`` dir of a Git checkout.

    Only the checkout that directly contains ``conformance`` counts.  Walking
    further up would silently adopt an unrelated enclosing repository (for
    example when a copied fixture tree lives under this project's own checkout)
    and report the wrong commit.
    """
    suite_root = directory.parent
    if not (suite_root / ".git").exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "-C", str(suite_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=str(cwd), env=env, capture_output=True, text=True)
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n", flush=True)
    if completed.stderr:
        print(
            completed.stderr,
            end="" if completed.stderr.endswith("\n") else "\n",
            file=sys.stderr,
            flush=True,
        )
    return completed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--suite",
        type=Path,
        default=(
            Path(os.environ["PIKAID_CONFORMANCE_SUITE"])
            if os.environ.get("PIKAID_CONFORMANCE_SUITE")
            else None
        ),
        help="path to the pinned $pikaid-specs/conformance directory (or PIKAID_CONFORMANCE_SUITE)",
    )
    parser.add_argument(
        "--report-json", type=Path, default=None, help="write the runner's JSON report here"
    )
    parser.add_argument(
        "--out-dir", type=Path, default=None, help="directory for intermediate reports"
    )
    parser.add_argument(
        "--node",
        default=shutil.which("node"),
        help="node executable for the independent BigInt oracle",
    )
    parser.add_argument(
        "--skip-suite-self-tests", action="store_true", help="skip the suite's own unit tests"
    )
    parser.add_argument(
        "adapter",
        nargs=argparse.REMAINDER,
        help="-- adapter command (must invoke the real library); required",
    )
    args = parser.parse_args(argv)

    conformance = args.suite
    if conformance is None:
        parser.error("--suite (or PIKAID_CONFORMANCE_SUITE) is required")
    conformance = conformance.resolve()
    if not (conformance / "manifest.json").is_file():
        parser.error(f"{conformance} is not an official conformance directory")

    adapter = args.adapter
    if adapter and adapter[0] == "--":
        adapter = adapter[1:]
    if not adapter:
        parser.error("pass the real adapter command after --")
    # The runner executes the adapter from the suite directory, so resolve
    # caller-relative executable paths (e.g. .venv/bin/python, adapter.py)
    # against the directory this driver was invoked from.  ``normpath`` instead
    # of ``resolve`` keeps virtual-environment symlinks intact: resolving
    # ``venv/bin/python`` to the base interpreter would lose the venv's
    # site-packages.
    invocation_cwd = Path.cwd()
    adapter = [
        str(Path(os.path.normpath(invocation_cwd / token)))
        if not Path(token).is_absolute() and (invocation_cwd / token).exists()
        else token
        for token in adapter
    ]

    # Reports are also given relative to the caller, but the upstream runner runs
    # with the suite directory as its working directory.  Resolve them first so a
    # relative ``--report-json`` never lands inside the pinned checkout.
    report_json = args.report_json.resolve() if args.report_json else None
    out_dir = args.out_dir.resolve() if args.out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    python = sys.executable
    env = dict(os.environ)
    # Keep the bridge deterministic and quiet: never write .pyc beside the suite.
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")

    identity = verify_suite_identity(conformance)
    print("pinned suite identity: " + json.dumps(identity, sort_keys=True), flush=True)

    steps: list[dict[str, Any]] = []

    def record(name: str, completed: subprocess.CompletedProcess[str]) -> None:
        steps.append({"step": name, "returncode": completed.returncode})
        if completed.returncode != 0:
            raise SuiteError(f"step failed: {name} (exit {completed.returncode})")

    record(
        "verify_vectors",
        _run(
            [
                python,
                str(conformance / "tools" / "verify_vectors.py"),
                "--expect-status",
                PINNED_STATUS,
                "--expect-package-revision",
                PINNED_SUITE_REVISION,
                "--expect-spec-revision",
                PINNED_SPEC_REVISION,
            ],
            cwd=conformance,
            env=env,
        ),
    )

    if not args.skip_suite_self_tests:
        record(
            "suite_self_tests",
            _run(
                [python, "-m", "unittest", "discover", "-s", "tools/tests", "-v"],
                cwd=conformance,
                env=env,
            ),
        )

    if not args.node:
        raise SuiteError("node is required for the independent BigInt oracle")
    record(
        "node_oracle",
        _run(
            [args.node, str(conformance / "tools" / "verify_oracle_node.mjs")],
            cwd=conformance,
            env=env,
        ),
    )

    # Reports were already resolved against the caller's directory above.
    runner_report = report_json or (out_dir / "adapter-report.json" if out_dir else None)
    runner_command = [
        python,
        str(conformance / "tools" / "run_adapter.py"),
        "--automated-only",
    ]
    if runner_report is not None:
        runner_report.parent.mkdir(parents=True, exist_ok=True)
        runner_command += ["--report-json", str(runner_report)]
    runner_command += ["--", *adapter]
    completed = _run(runner_command, cwd=conformance, env=env)
    steps.append({"step": "official_runner", "returncode": completed.returncode})
    if completed.returncode != 0:
        raise SuiteError(f"official runner failed with exit {completed.returncode}")

    summary: dict[str, Any] = {
        "identity": identity,
        "steps": steps,
        "adapter": adapter,
        "report_json": str(runner_report) if runner_report else None,
    }
    if runner_report is not None and runner_report.is_file():
        summary["runner_report"] = json.loads(runner_report.read_text(encoding="utf-8"))
    print("official conformance run summary: " + json.dumps(summary, sort_keys=True), flush=True)
    print("AUTOMATED PASS ONLY: independent human security review is still required.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SuiteError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
