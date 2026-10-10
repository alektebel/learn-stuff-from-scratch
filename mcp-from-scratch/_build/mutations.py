"""Mutation test for mcp-from-scratch.

Each entry is (description, old_text, new_text, expected_test). The runner copies the
module into a scratch directory, replaces the reference solution with a mutant, and
runs the contract there. A mutant is CAUGHT when pytest exits non-zero (the contract
rejects it) and MISSED when the suite still passes (the contract proves nothing about
that mechanism). Every mutation must be CAUGHT.

    /tmp/opencode/hlvenv/bin/python mcp-from-scratch/_build/mutations.py

The `expected_test` column is documentation, not an assertion: the whole suite runs.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MODULE = Path(__file__).resolve().parent.parent
SOLUTION = MODULE / "solutions" / "mcp_server.py"

MUTATIONS: list[tuple[str, str, str, str]] = [
    (
        "initialize echoes the requested revision instead of the pinned one",
        '            "protocolVersion": PINNED_REVISION,',
        '            "protocolVersion": requested,',
        "test_07",
    ),
    (
        "initialize no longer fails closed on a revision it does not know",
        "        if requested not in SUPPORTED_REVISIONS:\n            raise RpcError(",
        "        if False:\n            raise RpcError(",
        "test_08",
    ),
    (
        "a notification gets a response instead of none",
        "            except RpcError:\n                pass\n            return None",
        "            except RpcError:\n                pass\n"
        '            return {"jsonrpc": JSONRPC, "id": None, "result": {}}',
        "test_11",
    ),
    (
        "an unknown method returns a result instead of -32601",
        'raise RpcError(METHOD_NOT_FOUND, f"unknown method {method!r}")',
        "return {}",
        "test_11",
    ),
    (
        "an unknown tool raises a protocol error instead of an isError result",
        "            return self._text(\n"
        '                f"unknown tool {name!r}; available tools: {available}", is_error=True)',
        '            raise RpcError(METHOD_NOT_FOUND, f"unknown tool {name!r}")',
        "test_12",
    ),
    (
        "validation ignores additional properties (a smuggled sql argument passes)",
        "        extra = sorted(key for key in arguments if key not in properties)\n"
        "        if extra:\n            raise RpcError(",
        "        extra = []\n        if extra:\n            raise RpcError(",
        "test_18",
    ),
    (
        "validation ignores missing required arguments",
        "        if missing:\n            raise RpcError(",
        "        if False:\n            raise RpcError(",
        "test_13",
    ),
    (
        "validation ignores an argument of the wrong type",
        '            if expected == "string" and not isinstance(value, str):',
        "            if False:",
        "test_13",
    ),
    (
        "a retry is not stored, so it re-runs and surfaces the duplicate reference",
        "        if replay_key is not None:\n"
        "            self._idempotency[replay_key] = result\n        return result",
        "        return result",
        "test_15",
    ),
    (
        "the per-session sequence policy is never consulted",
        "        self.session.observe(identity, name)",
        "        pass  # observe disabled",
        "test_17",
    ),
    (
        "the caller's identity is dropped before the ERP sees it",
        '                float(arguments["amount"]),\n                identity=identity,',
        '                float(arguments["amount"]),\n                identity=None,',
        "test_16",
    ),
    (
        "a malformed HTTP body is answered with 500 instead of 400",
        'RpcError(PARSE_ERROR, "parse error: body is not valid JSON"))\n            return 400,',
        'RpcError(PARSE_ERROR, "parse error: body is not valid JSON"))\n            return 500,',
        "test_14",
    ),
]


def run_mutant(source: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(MODULE / "fake_erp.py", work / "fake_erp.py")
        shutil.copytree(MODULE / "tests", work / "tests")
        (work / "mcp_server.py").write_text(source)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=work, capture_output=True, text=True,
        )
        return proc.returncode != 0, proc.stdout.strip().splitlines()[-1] if proc.stdout else ""


def main() -> int:
    original = SOLUTION.read_text()
    caught = missed = 0
    for description, old, new, expected in MUTATIONS:
        occurrences = original.count(old)
        if occurrences != 1:
            print(f"[BAD ] {description}: old text occurs {occurrences} times, needs 1")
            missed += 1
            continue
        is_caught, summary = run_mutant(original.replace(old, new, 1))
        print(f"[{'CAUGHT' if is_caught else 'MISSED'}] {description} ({expected})")
        if not is_caught:
            print(f"         suite still green: {summary}")
        caught += is_caught
        missed += not is_caught
    print(f"\n{caught} caught, {missed} missed, {len(MUTATIONS)} total")
    return 1 if missed else 0


if __name__ == "__main__":
    raise SystemExit(main())
