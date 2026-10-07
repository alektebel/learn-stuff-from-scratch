"""
Progress checker for the GPU memory-system templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every expected count is computed here from the pattern, in closed form, so the checker
never asks your own code for the answer.
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


# ---------------------------------------------------------------------------
# Steps 1-4: coalescing.py
# ---------------------------------------------------------------------------

def check_coalescing_sectors() -> None:
    from coalescing import LINE_BYTES, SECTOR_BYTES, sector_of, sectors_touched

    assert SECTOR_BYTES == 32, "the transfer granularity is a 32-byte sector"
    assert LINE_BYTES == 128, "a cache line is four sectors"
    assert sector_of(0) == 0 and sector_of(31) == 0 and sector_of(32) == 1
    assert sector_of(63) == 1 and sector_of(64) == 2 and sector_of(1000) == 31
    assert sectors_touched([]) == 0, "a warp with no active threads touches no sector"
    assert sectors_touched([0, 31, 32, 63]) == 2, "0-31 is one sector, 32-63 is the next"


def check_coalescing_contiguous() -> None:
    from coalescing import (WARP, efficiency, is_fully_coalesced, sectors_touched,
                            transferred_bytes)

    addrs = [t * 4 for t in range(WARP)]
    got = sectors_touched(addrs)
    assert got == 4, (
        f"32 threads reading consecutive float32 span 128 bytes = 4 sectors; got {got}")
    assert transferred_bytes(addrs) == 128
    assert efficiency(addrs) == 1.0, "consecutive float32 is the fully coalesced case"
    assert is_fully_coalesced(addrs)


def check_coalescing_strided() -> None:
    from coalescing import WARP, efficiency, sectors_touched

    stride8 = [t * 8 for t in range(WARP)]
    got = sectors_touched(stride8)
    assert got == 8, (
        f"stride-8-byte float32 spans 0..248, touching sectors 0..7 = 8, not 4; got {got}. "
        "Counting 128-byte lines instead of 32-byte sectors gives 2 here and hides that "
        "half of every sector is unused")
    assert efficiency(stride8) == 0.5

    stride32 = [t * 32 for t in range(WARP)]
    got = sectors_touched(stride32)
    assert got == 32, (
        f"one thread per 32-byte sector touches all 32 sectors; got {got}")
    assert efficiency(stride32) == 0.125


def check_coalescing_order_offset() -> None:
    from coalescing import WARP, efficiency, sectors_touched

    forward = [t * 4 for t in range(WARP)]
    assert sectors_touched(list(reversed(forward))) == 4, (
        "which sectors are touched does not depend on the order of the threads")
    misaligned = [7 + t * 4 for t in range(WARP)]
    got = sectors_touched(misaligned)
    assert got == 5, (
        f"a contiguous warp starting at byte 7 crosses 5 sector boundaries, not 4; got {got}")
    assert abs(efficiency(misaligned) - 0.8) < 1e-12
    far = [t * 8 for t in range(16)] + [4096 + t * 8 for t in range(16)]
    assert sectors_touched(far) == 8, "two half-warps in distant regions cost their own sectors"


# ---------------------------------------------------------------------------
# Steps 5-8: banks.py
# ---------------------------------------------------------------------------

def check_bank_mapping() -> None:
    from banks import BANKS, WARP, bank_of

    assert BANKS == 32 and WARP == 32
    assert [bank_of(w) for w in (0, 31, 32, 33, 63, 64)] == [0, 31, 0, 1, 31, 0]


def check_banks_row_vs_column() -> None:
    from banks import column_words, is_conflict_free, row_words, serialisation_degree

    row = row_words(0, 32)
    assert row == list(range(32))
    got = serialisation_degree(row)
    assert got == 1, (
        f"a row read of a 32x32 tile is conflict-free (thread c hits bank c); got degree "
        f"{got}")
    assert is_conflict_free(row)

    col = column_words(0, 32, 32)
    got = serialisation_degree(col)
    assert got == 32, (
        f"a column read of a 32x32 tile is a 32-way conflict: thread r reads word "
        f"r*32+col, and r*32 % 32 == 0, so all 32 threads hit one bank on 32 different "
        f"words. Got degree {got}. Counting distinct banks (there is only one) instead of "
        "distinct words per bank hides exactly this bug")
    assert not is_conflict_free(col)


def check_banks_padding() -> None:
    from banks import column_words, is_conflict_free, serialisation_degree, tile_words

    for col in (0, 1, 17, 31):
        padded = column_words(col, 32, 32, pad=1)
        got = serialisation_degree(padded)
        assert got == 1, (
            f"padding a 32x32 tile to 32x33 makes column {col} conflict-free "
            f"(bank = (r*33 + col) % 32 = (r + col) % 32); got degree {got}")
        assert is_conflict_free(padded)
    assert tile_words(32, 32) == 1024
    assert tile_words(32, 32, pad=1) == 1056
    extra = tile_words(32, 32, pad=1) - tile_words(32, 32)
    assert extra == 32, (
        f"padding costs one word per row: 32 extra words (128 bytes), 3.125% of the tile; "
        f"got {extra}")


def check_banks_broadcast_and_degree() -> None:
    from banks import serialisation_degree

    got = serialisation_degree([5] * 32)
    assert got == 1, (
        f"32 threads reading the SAME word is a broadcast, one cycle, not a conflict; got {got}")
    assert serialisation_degree([5, 37] * 16) == 2, (
        "two distinct words in one bank serialise to 2 cycles")
    assert serialisation_degree([5, 37, 69, 101] * 8) == 4
    two_each = list(range(32)) + [w + 32 for w in range(32)]
    got = serialisation_degree(two_each)
    assert got == 2, (
        f"every bank has two words: the cost is the slowest bank (2), not the total (64); "
        f"got {got}")


# ---------------------------------------------------------------------------
# Steps 9-12: occupancy.py
# ---------------------------------------------------------------------------

def check_occupancy_register_allocation() -> None:
    from occupancy import DEFAULT_SM_LIMITS, registers_per_block, round_up

    assert DEFAULT_SM_LIMITS.max_warps_per_sm == 48
    assert registers_per_block(32, 256) == 8192, (
        "32 regs x 32 threads x 8 warps (a 256-thread block) = 8192 registers")
    assert registers_per_block(64, 256) == 16384
    assert registers_per_block(32, 100) == 4096, (
        "100 threads round up to 4 warps: a 100-thread block allocates as 128")
    got = registers_per_block(33, 256)
    assert got == 10240, (
        f"33 registers round up to 40 (allocation granularity 8) per warp: 40 x 32 x 8 = "
        f"10240, not 33 x 32 x 8 = 8448; got {got}")
    assert round_up(33, 8) == 40


def check_occupancy_block_caps() -> None:
    from occupancy import block_caps, round_up

    caps = block_caps(32, 0, 256)
    assert caps == {"threads": 6, "registers": 8, "shared_memory": 16, "blocks": 16}, caps
    assert block_caps(64, 0, 256)["registers"] == 4
    assert block_caps(32, 16384, 256)["shared_memory"] == 3, "49152 / 16384 = 3 blocks"
    assert round_up(20000, 256) == 20224, (
        "shared memory is reserved in 256-byte units")
    assert block_caps(32, 20000, 256)["shared_memory"] == 2


def check_occupancy_register_limit() -> None:
    from occupancy import active_warps, limiting_resource, max_active_blocks, occupancy

    got = max_active_blocks(128, 0, 256)
    assert got == 2, (
        f"128 regs x 32 threads x 8 warps = 32768 registers per block; a 64K register file "
        f"fits only 2 blocks, not the 6 the thread limit allows; got {got}")
    assert limiting_resource(128, 0, 256) == "registers"
    assert active_warps(128, 0, 256) == 16, "2 resident blocks x 8 warps = 16 active warps"
    got = occupancy(128, 0, 256)
    assert abs(got - 16 / 48) < 1e-12, (
        f"occupancy = 16 active warps / 48 max warps = 1/3; got {got:.3f}. An occupancy "
        "calculator that ignores the register limit reports 6 blocks and 100% here")


def check_occupancy_other_limits() -> None:
    from occupancy import active_warps, limiting_resource, max_active_blocks, occupancy

    assert max_active_blocks(32, 0, 256) == 6 and occupancy(32, 0, 256) == 1.0
    assert limiting_resource(32, 0, 256) == "threads"
    got = max_active_blocks(32, 16384, 256)
    assert got == 3, (
        f"shared memory caps blocks at 49152 / 16384 = 3 before the thread limit of 6; got {got}")
    assert limiting_resource(32, 16384, 256) == "shared_memory"
    assert active_warps(32, 16384, 256) == 24
    assert abs(occupancy(32, 16384, 256) - 0.5) < 1e-12
    assert max_active_blocks(32, 0, 1024) == 1, (
        "1536 max threads / 1024 per block = 1 block, even though registers allow 2")
    assert limiting_resource(32, 0, 1024) == "threads"


# ---------------------------------------------------------------------------
# Steps 13-16: roofline.py
# ---------------------------------------------------------------------------

def check_roofline_ridge() -> None:
    from roofline import ridge_point

    assert ridge_point(1e13, 1e12) == 10.0
    assert ridge_point(6e13, 2e12) == 30.0
    assert abs(ridge_point(9.6e12, 1.5e12) - 6.4) < 1e-9


def check_roofline_attainable() -> None:
    from roofline import attainable_flops, attainable_fraction

    peak, bandwidth = 1e13, 1e12
    got = attainable_flops(2.0, peak, bandwidth)
    assert got == 2e12, (
        f"below the ridge the memory roof binds: 2 flop/byte x 1 TB/s = 2 TFLOP/s, not "
        f"the 10 TFLOP/s peak; got {got}")
    assert attainable_flops(10.0, peak, bandwidth) == 1e13
    assert attainable_flops(20.0, peak, bandwidth) == 1e13
    assert attainable_flops(2.0, peak, bandwidth) != peak, (
        "returning peak compute for every kernel ignores the memory roof")
    assert abs(attainable_fraction(2.0, peak, bandwidth) - 0.2) < 1e-12


def check_roofline_classification() -> None:
    from roofline import bottleneck, is_memory_bound

    peak, bandwidth = 1e13, 1e12
    assert is_memory_bound(2.0, peak, bandwidth) and not is_memory_bound(20.0, peak, bandwidth)
    assert not is_memory_bound(10.0, peak, bandwidth), (
        "at the ridge point both roofs are equal, so neither one is the bottleneck")
    assert bottleneck(2.0, peak, bandwidth) == "memory"
    assert bottleneck(20.0, peak, bandwidth) == "compute"


def check_roofline_kernels() -> None:
    from roofline import arithmetic_intensity, attainable_flops, bottleneck, ridge_point

    peak, bandwidth = 1e13, 1e12
    ai_add = arithmetic_intensity(1, 3 * 4)
    assert abs(ai_add - 1 / 12) < 1e-12, "vector add: 1 flop per 12 bytes (2 reads + 1 write)"
    assert bottleneck(ai_add, peak, bandwidth) == "memory"
    n = 1024
    ai_mm = arithmetic_intensity(2 * n ** 3, 3 * n ** 2 * 4)
    assert abs(ai_mm - n / 6) < 1e-9
    assert bottleneck(ai_mm, peak, bandwidth) == "compute", (
        "matmul at N=1024 has AI = N/6 ~ 171 flop/byte, far above the ridge of 10")
    assert attainable_flops(ai_add, peak, bandwidth) == ai_add * bandwidth
    assert attainable_flops(ai_mm, peak, bandwidth) == peak
    assert ridge_point(peak, bandwidth) == 10.0


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("coalescing.py", "byte address -> 32-byte sector", check_coalescing_sectors),
    ("coalescing.py", "contiguous float32: 4 sectors, 100%", check_coalescing_contiguous),
    ("coalescing.py", "strided: 8 and 32 sectors", check_coalescing_strided),
    ("coalescing.py", "order and offset invariance", check_coalescing_order_offset),
    ("banks.py", "word index -> bank", check_bank_mapping),
    ("banks.py", "row vs column of a 32x32 tile", check_banks_row_vs_column),
    ("banks.py", "padding to 33 removes the conflict", check_banks_padding),
    ("banks.py", "broadcast and multi-way degree", check_banks_broadcast_and_degree),
    ("occupancy.py", "registers per block, warp rounding", check_occupancy_register_allocation),
    ("occupancy.py", "one cap per resource", check_occupancy_block_caps),
    ("occupancy.py", "the register limit binds", check_occupancy_register_limit),
    ("occupancy.py", "shared-memory and thread limits", check_occupancy_other_limits),
    ("roofline.py", "the ridge point", check_roofline_ridge),
    ("roofline.py", "attainable flops below and above the ridge", check_roofline_attainable),
    ("roofline.py", "memory-bound vs compute-bound", check_roofline_classification),
    ("roofline.py", "vector add and matmul on the roofline", check_roofline_kernels),
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
    print(f"\n{BOLD}GPU Memory System From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the GPU memory model.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
