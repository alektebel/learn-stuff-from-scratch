"""
Progress checker for the KV-cache monitor templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 2         # run only step 2
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure):
that is simply the next thing to write. Nothing here imports solutions/. The
simulations are tiny and bounded (max_steps), so this cannot hang.
"""

import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def _config(blocks: int = 8, block_size: int = 4, bpt: int = 4):
    from kv import ServingConfig
    return ServingConfig(bytes_per_token=bpt, block_size=block_size, total_blocks=blocks)


# ---------------------------------------------------------------------------
# Steps 1-2: the block pool
# ---------------------------------------------------------------------------

def check_blocks_needed() -> None:
    from allocator import blocks_needed

    cases = [(0, 16, 0), (1, 16, 1), (16, 16, 1), (17, 16, 2), (64, 16, 4), (5, 4, 2)]
    for length, block_size, want in cases:
        got = blocks_needed(length, block_size)
        assert got == want, (
            f"blocks_needed({length}, {block_size}) = {got}, expected {want}: a sequence "
            "claims a WHOLE block for its last partial one, so this is ceil(length/block_size)")
    for bad in (-1,):
        try:
            blocks_needed(bad, 16)
            raise AssertionError("blocks_needed(-1, 16) returned; a negative length must raise")
        except ValueError:
            pass
    try:
        blocks_needed(10, 0)
        raise AssertionError("blocks_needed(10, 0) returned; a zero block size must raise")
    except ValueError:
        pass


def check_allocator_invariants() -> None:
    from allocator import BlockAllocator

    pool = BlockAllocator(4)
    assert pool.used_blocks == 0 and pool.free_blocks == 4, (
        f"a fresh pool of 4 reports used={pool.used_blocks} free={pool.free_blocks}")
    pool.allocate(3)
    assert pool.used_blocks == 3 and pool.free_blocks == 1, (
        f"after allocate(3): used={pool.used_blocks} free={pool.free_blocks}")
    assert pool.fits(1) and not pool.fits(2), (
        "with 1 block free, fits(1) must be True and fits(2) False")
    assert abs(pool.utilisation - 0.75) < 1e-9, (
        f"utilisation of 3/4 blocks is {pool.utilisation}, expected 0.75")
    try:
        pool.allocate(2)
        raise AssertionError(
            "allocate(2) with 1 block free returned: the pool must raise, not over-allocate")
    except ValueError:
        pass
    pool.release(3)
    assert pool.used_blocks == 0, f"release(3) left used={pool.used_blocks}"
    try:
        pool.release(1)
        raise AssertionError(
            "release(1) on an empty pool returned: releasing more than is used must raise")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Steps 3-4: the step loop
# ---------------------------------------------------------------------------

def check_fitting_workload() -> None:
    from kv import MODELS, Request, bytes_per_token
    from simulator import simulate

    # provided arithmetic, for reference: this is the number capacity.py derives
    assert bytes_per_token(MODELS["Llama-3-8B"]) == 131072, (
        "bytes per token for Llama-3-8B must be 131072 (2 x 32 layers x 8 KV heads x "
        "128 head_dim x 2 bytes) — use KV heads, not the 32 query heads")

    config = _config(blocks=8, block_size=4)   # 8 blocks, 4 tokens each
    reqs = [Request("a", 0, 8, 8), Request("b", 0, 8, 8)]  # each peaks at 16 tokens = 4 blocks
    timeline = simulate(reqs, config)
    assert timeline.completed == 2, (
        f"both requests fit the pool but completed={timeline.completed}")
    assert timeline.preemptions == 0, (
        f"two 4-block sequences fit 8 blocks, so there should be no preemption; "
        f"got {timeline.preemptions}")
    assert not timeline.oom and not timeline.rejected, (
        f"oom={timeline.oom} rejected={timeline.rejected}: a fitting workload must not fail")
    assert timeline.peak_blocks == 8, (
        f"both sequences reach 4 blocks together, so the peak should be 8; "
        f"got {timeline.peak_blocks}. Are sequences released before they finish, or grown "
        "after completion?")


def check_over_subscribed_workload() -> None:
    from kv import Request
    from simulator import simulate

    config = _config(blocks=8, block_size=4)
    reqs = [Request("a", 0, 8, 8), Request("b", 0, 8, 8), Request("c", 0, 8, 8)]
    timeline = simulate(reqs, config)  # no cap: three 4-block sequences cannot coexist in 8
    assert timeline.completed == 3, (
        f"each request fits alone, so all three must eventually complete; "
        f"completed={timeline.completed}")
    assert timeline.preemptions >= 1, (
        "three 4-block sequences need 12 blocks of an 8-block pool; the scheduler must "
        f"PREEMPT to make room, not queue forever; preemptions={timeline.preemptions}")
    assert not timeline.oom, (
        "the simulator failed to make progress: preempting should free room, and every "
        "request fits on its own")
    assert timeline.peak_blocks <= 8, (
        f"used {timeline.peak_blocks} of 8 blocks: the pool must never be over-allocated")
    assert timeline.rejected == (), (
        f"rejected={timeline.rejected}: only a request longer than the whole pool is rejected, "
        "and these fit")


# ---------------------------------------------------------------------------
# Step 5: the monitor
# ---------------------------------------------------------------------------

def check_monitor_reads_the_timeline() -> None:
    from monitor import peak_utilisation, recommend_max_num_seqs, steps_above
    from kv import Request
    from simulator import simulate

    config = _config(blocks=8, block_size=4)
    reqs = [Request(x, 0, 8, 8) for x in "abc"]
    timeline = simulate(reqs, config)

    assert abs(peak_utilisation(timeline) - 1.0) < 1e-9, (
        f"the pool reaches 8/8 blocks, so peak utilisation is 1.0; got "
        f"{peak_utilisation(timeline)}")
    assert steps_above(timeline, 0.9) >= 1, (
        "the pool is full for several steps, so steps_above(0.9) must count them; "
        f"got {steps_above(timeline, 0.9)}")

    cap = recommend_max_num_seqs(reqs, config)
    assert 1 <= cap < len(reqs), (
        f"recommended cap {cap}: with 8 blocks, three concurrent 4-block sequences preempt, "
        "so the answer must be lower than 3 (and at least 1)")
    at = simulate(reqs, config, max_num_seqs=cap)
    assert at.preemptions == 0 and at.completed == 3, (
        f"the recommended cap {cap} still preempts ({at.preemptions}) or dropped work "
        f"(completed={at.completed}); the recommendation must be preemption-free")
    over = simulate(reqs, config, max_num_seqs=cap + 1)
    assert over.preemptions >= 1, (
        f"one more than the recommended cap ({cap + 1}) should PREEMPT — if it does not, the "
        "recommendation was not the largest preemption-free cap")


# ---------------------------------------------------------------------------

CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("allocator.py", "blocks_needed rounds up to whole blocks", check_blocks_needed),
    ("allocator.py", "the pool never over-allocates or over-releases", check_allocator_invariants),
    ("simulator.py", "a workload that fits completes with no preemption", check_fitting_workload),
    ("simulator.py", "an over-subscribed workload preempts, not crashes",
     check_over_subscribed_workload),
    ("monitor.py", "utilisation, headroom and a preemption-free cap",
     check_monitor_reads_the_timeline),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}KV-cache monitor — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<12} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<12} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<12} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — the pool is accounted for and preempts before it crashes.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
