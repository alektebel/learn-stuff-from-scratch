"""
Checker for the analytical performance models — the four files that need no GPU.

    python3 check_perf.py --all

Separate from this directory's CUDA work on purpose. Those kernels need
hardware and a profiler; these four are arithmetic you should be able to do
BEFORE writing a kernel, and check the profiler against afterwards.

SKELETON. Checks named, bodies unwritten. See ../../TODO.md section 15.

Sourced from Fregly, *AI Systems Performance Engineering* (O'Reilly) — chapters
6 to 12. What could be lifted honestly is the part that is arithmetic. The rest
of that book is hardware measurement and needs the hardware; see this
directory's README for the split.
"""

import math
import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def check_arithmetic_intensity() -> None:
    """FLOPs per byte, computed for kernels whose answer is known.

    TODO: assert a SAXPY is memory-bound (intensity well under 1) and a large
    dense matmul is compute-bound, on the SAME hardware parameters. Then assert
    the intensity of a matmul GROWS with tile size — that growth is the entire
    reason tiling works, and a check on one size cannot see it.
    """
    raise NotImplementedError


def check_ridge_point() -> None:
    """The ridge is peak FLOPs / peak bandwidth, and it moves with the hardware.

    TODO: assert the ridge point is computed from the two peaks rather than
    hard-coded; assert a kernel below it cannot exceed bandwidth x intensity no
    matter how much arithmetic you remove; and assert `speedup_ceiling` returns
    1.0 for a kernel already at the roof. Optimising a kernel that is already
    at the roof is the week of work that produces nothing.
    """
    raise NotImplementedError


def check_occupancy_binding_constraint() -> None:
    """Registers, shared memory or block size — whichever runs out first.

    TODO: build three cases, each limited by a DIFFERENT resource, and assert
    `binding_constraint` names the right one in each. A calculator that only
    ever checks registers is right about two thirds of the time and useless.
    """
    raise NotImplementedError


def check_occupancy_is_not_the_goal() -> None:
    """Higher occupancy is not always faster.

    TODO: construct a case where cutting occupancy by using more registers per
    thread raises throughput, because instruction-level parallelism hides the
    latency with fewer warps (Volkov & Demmel, SC 2008). Assert the model
    reproduces it. A check that only rewards occupancy has taught the wrong
    lesson.
    """
    raise NotImplementedError


def check_transaction_count() -> None:
    """One warp instruction, N memory transactions, and N is what costs you.

    TODO: assert contiguous aligned access by 32 lanes gives the minimum
    transaction count; that a stride of 32 gives one per lane; and that a
    MISALIGNED but contiguous access costs one extra rather than doubling. That
    last case is the one people over-estimate.
    """
    raise NotImplementedError


def check_aos_vs_soa() -> None:
    """The same data, two layouts, different transaction counts.

    TODO: assert array-of-structs and struct-of-arrays give the same result and
    different costs when a kernel reads ONE field — and assert the advantage
    reverses when it reads every field. Both directions, or the check is an
    opinion.
    """
    raise NotImplementedError


def check_bank_conflicts() -> None:
    """32 banks, and a stride that maps many lanes onto one.

    TODO: assert stride 1 is conflict-free, stride 32 is a 32-way conflict, and
    padding the row by one element fixes it. Assert the broadcast case — every
    lane reading the SAME address — is NOT a conflict, which is the exception
    people get wrong.
    """
    raise NotImplementedError


def check_pipelining_ceiling() -> None:
    """Overlap turns a sum into a max, and then stops helping.

    TODO: assert serial time is transfer + compute, that pipelined time
    approaches max(transfer, compute), and that adding chunks past a computable
    point gains nothing. Assert `optimal_chunks` returns that point rather than
    'more is better'.
    """
    raise NotImplementedError


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("roofline.py", "FLOPs per byte, and why tiling works",
     check_arithmetic_intensity),
    ("roofline.py", "the ridge point, and the ceiling on any speedup",
     check_ridge_point),
    ("occupancy.py", "which resource runs out first",
     check_occupancy_binding_constraint),
    ("occupancy.py", "when LOWER occupancy is faster",
     check_occupancy_is_not_the_goal),
    ("coalescing.py", "one instruction, N transactions", check_transaction_count),
    ("coalescing.py", "AoS vs SoA, and where it reverses", check_aos_vs_soa),
    ("coalescing.py", "32 banks, and the broadcast exception",
     check_bank_conflicts),
    ("pipelining.py", "a sum becomes a max, then stops", check_pipelining_ceiling),
]


def run_one(check):
    try:
        check(); return PASS, ""
    except NotImplementedError:
        return TODO, ""
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:                       # noqa: BLE001
        return ERROR, f"{type(exc).__name__}: {exc}"


def main(argv: List[str]) -> int:
    wanted = [int(a) for a in argv if a.isdigit()]
    print(f"\n{BOLD}CUDA performance models — progress check{RESET}")
    print(f"{GREY}no GPU required; these are the numbers you compute first{RESET}\n")
    passed = 0
    for i, (filename, title, check) in enumerate(CHECKS, 1):
        if wanted and i not in wanted:
            continue
        status, detail = run_one(check)
        mark = {PASS: f"{GREEN}✓{RESET}", TODO: f"{GREY}·{RESET}"}.get(
            status, f"{RED}✗{RESET}")
        print(f"  {mark} {i:>2}. {filename:<14} {title}")
        if status == TODO:
            print(f"      {GREY}CHECK NOT WRITTEN — see the TODO in its docstring{RESET}")
        elif status != PASS:
            print(f"      {RED}{detail}{RESET}")
        passed += status == PASS
    print(f"\n  {passed}/{len(CHECKS)} passing\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
