"""
Progress checker for database-internals.

SKELETON. Checks named, bodies unwritten. See ../../TODO.md section 14.

Everything here builds on week-09/database-engine. If `executor.py` and
`planner.py` are not finished, nothing in this directory has a baseline to be
measured against, and the measurements ARE the content.
"""

import math
import pathlib
import random
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def check_independence_assumption() -> None:
    """Assuming independence understates selectivity on correlated columns.

    TODO: build a table where two columns are perfectly correlated, estimate
    `a=1 AND b=1` under independence, and assert the estimate is WRONG by a
    stated factor. Then assert it is right on genuinely independent columns.
    A check that only uses independent data proves nothing.
    """
    raise NotImplementedError


def check_error_compounds() -> None:
    """Estimation error grows multiplicatively with join count.

    TODO: build 1-, 2-, 3- and 4-way joins over correlated data; measure
    estimated vs actual cardinality at each; assert the error factor GROWS with
    join count rather than staying flat. This is the Leis et al. result and it
    is the reason optimisers pick bad plans while computing costs correctly.
    """
    raise NotImplementedError


def check_plan_regret() -> None:
    """A correct cost model plus wrong inputs still picks the wrong plan.

    TODO: feed the planner true cardinalities and then estimated ones, and
    assert the chosen plan DIFFERS and that the estimated-input plan is
    measurably slower. Attribute the loss to the estimate, not the model.
    """
    raise NotImplementedError


def check_hyperloglog() -> None:
    """Distinct count within a stated error bound, in constant space.

    TODO: assert the estimate is within the theoretical bound for the register
    count, across several true cardinalities including 0 and 1 -- the small
    range is where the naive formula is worst and needs its correction.
    """
    raise NotImplementedError


def check_count_min() -> None:
    """Count-Min OVERESTIMATES and never underestimates.

    TODO: assert every estimate >= true frequency (the one-sided guarantee),
    and that the overestimate stays within the width/depth bound. A sketch that
    is merely 'close' has lost the property that makes it usable.
    """
    raise NotImplementedError


def check_compression() -> None:
    """A column compresses because it is homogeneous; a row does not.

    TODO: compare RLE, dictionary and frame-of-reference ratios on sorted,
    low-cardinality and dense-integer columns, and assert each wins on the
    shape it is for. Then assert the SAME data laid out by row compresses
    measurably worse.
    """
    raise NotImplementedError


def check_late_materialization() -> None:
    """Stay compressed as long as possible.

    TODO: assert a selective query touches fewer bytes with late
    materialization than with early, and -- the part people miss -- assert the
    advantage REVERSES above some selectivity. Find that crossover.
    """
    raise NotImplementedError


def check_vectorized_overhead() -> None:
    """Per-tuple interpretation cost falls as the batch grows, then flattens.

    TODO: sweep batch size 1, 8, 64, 1024, 8192 and assert overhead per tuple
    falls sharply and then FLATTENS -- and that very large batches get no
    better (or get worse). A monotonic curve means you are not measuring the
    thing that made X100 fast.
    """
    raise NotImplementedError


def check_grace_hash_join() -> None:
    """The build side does not fit, and the join still works.

    TODO: constrain memory below the build side, assert a plain hash join
    would exceed it, assert Grace partitions and completes, and assert the I/O
    cost matches 3(|R|+|S|) rather than something better. Then assert SKEW
    breaks it -- one huge partition still does not fit.
    """
    raise NotImplementedError


def check_concurrency_crossover() -> None:
    """2PL, OCC and MVCC each win somewhere; the crossover is the answer.

    TODO: sweep the conflict rate and measure throughput and abort rate for all
    three. Assert OCC beats 2PL at low contention and LOSES at high contention,
    and that the crossover is a specific rate you can name. Assert MVCC readers
    never block. A check at one contention level proves nothing.
    """
    raise NotImplementedError


def check_deadlock_detection() -> None:
    """2PL can deadlock; the wait-for graph must find the cycle.

    TODO: construct a genuine cycle, assert it is detected, assert exactly one
    victim is aborted, and assert a non-cyclic wait chain is NOT reported. A
    detector that aborts on any wait is a detector that has removed 2PL's only
    advantage.
    """
    raise NotImplementedError


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("estimation.py", "independence, and what correlation costs",
     check_independence_assumption),
    ("estimation.py", "error compounds with every join", check_error_compounds),
    ("estimation.py", "right model, wrong inputs, wrong plan", check_plan_regret),
    ("sketches.py", "distinct count in constant space", check_hyperloglog),
    ("sketches.py", "one-sided error, and why that matters", check_count_min),
    ("columnar.py", "three encodings, three shapes", check_compression),
    ("columnar.py", "late materialization, and where it reverses",
     check_late_materialization),
    ("vectorized.py", "the batch-size curve flattens", check_vectorized_overhead),
    ("joins.py", "when the build side does not fit", check_grace_hash_join),
    ("concurrency.py", "2PL vs OCC vs MVCC, and the crossover",
     check_concurrency_crossover),
    ("concurrency.py", "a cycle, and exactly one victim",
     check_deadlock_detection),
]


def run_one(check):
    try:
        check(); return PASS, ""
    except NotImplementedError:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, where
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:                       # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}Database Internals — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<14} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<14} {title}")
            print(f"      {GREY}"
                  f"{('not implemented yet — ' + detail) if detail else 'CHECK NOT WRITTEN — see the TODO in its docstring'}"
                  f"{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<14} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")

    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()

    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you can now read a query plan and say why.{RESET}")
        print(f"  {GREY}Now run each file's own demo.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}Write the CHECK first (in check.py), then "
              f"{filename}. There is no solutions/ here.{RESET}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
