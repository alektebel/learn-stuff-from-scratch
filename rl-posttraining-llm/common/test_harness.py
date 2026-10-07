"""
test_harness.py — a tiny, zero-dependency test runner for the phase tests.

Why not pytest? Because the whole course is stdlib-only and must run anywhere
with `python test_phaseN.py`. This harness adds one thing pytest doesn't give
you for free and that matters a lot here: a **TODO** status. When you haven't
implemented a function yet it raises `NotImplementedError`, and the harness
reports that as "not implemented yet" instead of a scary red failure. So you can
run the tests from minute one and use them as a checklist.

Statuses:
  PASS  — your implementation meets the requirement
  FAIL  — implemented, but the behaviour is wrong (read the message)
  TODO  — not implemented yet (raised NotImplementedError)
  ERROR — crashed for another reason (a bug, or a typo)

Exit code is 0 only when there are no FAILs and no ERRORs, so you can wire this
into CI once you're done. TODOs alone don't fail the run — they're progress
markers, and the summary tells you how many are left.
"""
from __future__ import annotations

import traceback
from typing import Callable


class Checker:
    """Collects check results for one phase and prints a readable report."""

    def __init__(self, phase: str) -> None:
        self.phase = phase
        self.results: list[tuple[str, str, str]] = []  # (status, name, detail)

    def check(self, name: str, fn: Callable[[], None]) -> None:
        """Run one requirement check. `fn` should assert; returning is a pass."""
        try:
            fn()
        except NotImplementedError:
            self.results.append(("TODO", name, "not implemented yet"))
        except AssertionError as exc:
            self.results.append(("FAIL", name, str(exc) or "assertion failed"))
        except Exception as exc:  # noqa: BLE001
            detail = f"{type(exc).__name__}: {exc}"
            self.results.append(("ERROR", name, detail))
            self._last_traceback = traceback.format_exc()
        else:
            self.results.append(("PASS", name, ""))

    def summary(self) -> int:
        """Print the report. Returns a process exit code (0 = nothing broken)."""
        icons = {"PASS": "[PASS]", "FAIL": "[FAIL]", "TODO": "[TODO]", "ERROR": "[ERR ]"}
        print(f"\n=== {self.phase} ===")
        for status, name, detail in self.results:
            line = f"  {icons[status]} {name}"
            if detail:
                line += f"\n         -> {detail}"
            print(line)

        counts = {s: 0 for s in icons}
        for status, _, _ in self.results:
            counts[status] += 1
        total = len(self.results)
        print(
            f"\n  {counts['PASS']}/{total} passing"
            f"  |  {counts['TODO']} todo"
            f"  |  {counts['FAIL']} failing"
            f"  |  {counts['ERROR']} errored"
        )
        if counts["TODO"] and not (counts["FAIL"] or counts["ERROR"]):
            print("  Keep going — implement the TODOs and re-run.")
        if counts["PASS"] == total:
            print("  All requirements met for this phase. Move on.")
        return 0 if not (counts["FAIL"] or counts["ERROR"]) else 1


# --------------------------------------------------------------------------- #
# Assertion helpers used across the phase tests.
# --------------------------------------------------------------------------- #
def approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def assert_between(x: float, lo: float, hi: float, what: str = "value") -> None:
    assert lo <= x <= hi, f"{what} = {x!r}, expected within [{lo}, {hi}]"


def assert_close(a: float, b: float, tol: float = 1e-6, what: str = "value") -> None:
    assert approx(a, b, tol), f"{what} = {a!r}, expected ~{b!r} (tol {tol})"


def assert_is_probs(p, n: int, what: str = "probs") -> None:
    assert len(p) == n, f"{what} has length {len(p)}, expected {n}"
    assert all(x >= 0 for x in p), f"{what} contains a negative entry: {p}"
    assert approx(sum(p), 1.0, 1e-6), f"{what} sums to {sum(p)}, expected 1.0"


def load_student_module(phase_dir: str, module_name: str):
    """Import the learner's template module from its phase directory.

    Keeps the phase tests importable no matter what directory you run them from.
    """
    import importlib.util
    import os
    import sys

    common = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    if common not in sys.path:
        sys.path.insert(0, common)

    path = os.path.join(phase_dir, module_name + ".py")
    assert os.path.exists(path), f"cannot find {path}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Register BEFORE executing: @dataclass looks the defining module up in
    # sys.modules while it processes the class, and blows up if it isn't there.
    sys.modules[module_name] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return mod
