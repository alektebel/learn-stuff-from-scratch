"""
Progress checker for the allocator templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.
"""

import random
import shutil
import sys
import pathlib
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")

UTILISATION_FLOOR = 0.75


# ---------------------------------------------------------------------------
# Step 1 (accept): 16-byte alignment, non-overlapping payloads
# ---------------------------------------------------------------------------

def check_alignment_no_overlap() -> None:
    from allocator import ALIGN, HeapAllocator

    h = HeapAllocator(4096)
    sizes = [16, 1, 15, 17, 33, 16, 48, 100, 7, 200, 16, 15, 64, 3, 256]
    allocs = []
    for i, n in enumerate(sizes):
        p = h.malloc(n)
        assert p is not None, (
            f"malloc({n}) returned None after only {len(allocs)} live allocations on a "
            f"{h.arena_size}-byte arena: the heap is being over-consumed or not split")
        assert p % ALIGN == 0, (
            f"malloc({n}) returned offset {p}, not a multiple of {ALIGN}: payloads must start "
            f"at a multiple of {ALIGN} (header size {ALIGN} from a {ALIGN}-aligned block)")
        assert ALIGN <= p < h.arena_size, f"malloc({n}) returned {p}, outside the arena"
        allocs.append((p, n))

    # The requested ranges must not overlap. Sorting by start catches an allocator that
    # hands the same address out twice or returns a pointer inside another block.
    ranges = sorted((p, p + n) for p, n in allocs)
    for (a0, a1), (b0, b1) in zip(ranges, ranges[1:]):
        assert a1 <= b0, f"allocations overlap: [{a0}, {a1}) and [{b0}, {b1})"

    # The physical blocks must tile the arena. First fit carves from the front, so the
    # allocations are the leading blocks; at most one free tail may remain.
    blocks = h.blocks()
    allocated = [b for b in blocks if b.allocated]
    free = [b for b in blocks if not b.allocated]
    assert len(allocated) == len(allocs), (
        f"{len(allocs)} allocations produced {len(allocated)} allocated blocks: a free block "
        f"appeared in the middle of the run instead of only at the tail")
    assert len(free) <= 1, f"expected at most a free tail block, found {len(free)} free blocks"
    off = ALIGN
    for b in allocated:
        assert b.offset == off, f"blocks are not contiguous: expected a block at {off}, got {b.offset}"
        off += b.size
    for (p, n), b in zip(allocs, allocated):
        assert b.payload == p, f"block at {b.offset} starts its payload at {b.payload}, malloc said {p}"
        assert b.capacity >= n, f"malloc({n}) returned a block with only {b.capacity} payload bytes"

    # Write a distinct pattern into every allocation: if two payloads overlap, one write
    # clobbers another and the read-back differs.
    for i, (p, n) in enumerate(allocs):
        h.write(p, bytes([i + 1]) * n)
    for i, (p, n) in enumerate(allocs):
        got = h.read(p, n)
        assert got == bytes([i + 1]) * n, (
            f"allocation {i} ({n} bytes at {p}) was corrupted by a later write: payloads overlap")


# ---------------------------------------------------------------------------
# Step 2 (accept): freed blocks are reused, adjacent free blocks coalesce
# ---------------------------------------------------------------------------

def check_reuse_and_coalesce() -> None:
    from allocator import HeapAllocator

    h = HeapAllocator(4096)
    a, b, c = h.malloc(64), h.malloc(64), h.malloc(64)
    assert None not in (a, b, c) and a < b < c, f"expected three increasing blocks, got {a}, {b}, {c}"

    h.free(b)
    d = h.malloc(64)
    assert d == b, (
        f"after freeing the block at {b}, a same-size request returned {d}: first fit must reuse "
        f"the earliest free block that fits, not carve a new one from the tail")

    h.free(d)
    h.free(a)
    h.free(c)
    free_blocks = [blk for blk in h.blocks() if not blk.allocated]
    assert len(free_blocks) == 1, (
        f"freeing the three adjacent blocks (plus the tail) left {len(free_blocks)} free blocks: "
        f"adjacent free blocks must coalesce into one")
    assert free_blocks[0].payload == a, (
        f"the coalesced free block should start its payload at {a}, got {free_blocks[0].payload}")

    # One request that only fits because the three 64-byte blocks merged.
    e = h.malloc(192)
    assert e == a, f"a 192-byte request should fit the coalesced block at {a}, got {e}"


# ---------------------------------------------------------------------------
# Step 3 (accept): a stress run keeps utilisation above the stated floor
# ---------------------------------------------------------------------------

def check_stress_utilisation() -> None:
    from allocator import HeapAllocator

    rng = random.Random(20240613)
    h = HeapAllocator(65536)
    sizes = [16, 32, 48, 64, 80, 128, 256, 512]
    live = []
    peak = 0.0
    while True:
        n = rng.choice(sizes)
        p = h.malloc(n)
        if p is None:
            break
        live.append((p, n))
        peak = max(peak, h.utilization())

    assert len(live) >= 100, (
        f"the stress run fit only {len(live)} blocks; a first-fit allocator with boundary tags "
        f"should fit hundreds (are blocks being split?)")
    assert peak >= UTILISATION_FLOOR, (
        f"peak utilisation {peak:.3f} is below the floor {UTILISATION_FLOOR}: allocated payload "
        f"should be most of a {h.arena_size}-byte arena (are oversized blocks being handed out?)")

    # Reuse: free every third block, then request the same sizes again. The freed holes are
    # exactly large enough, so every request must be served from them.
    freed = live[::3]
    for p, n in freed:
        h.free(p)
    reused = sum(1 for p, n in freed if h.malloc(n) is not None)
    assert reused == len(freed), (
        f"only {reused} of {len(freed)} freed blocks were reused: freed space must come back "
        f"out of the free list, not be stranded")


# ---------------------------------------------------------------------------
# Step 4 (limit): free(None) is a no-op; a double free is detected
# ---------------------------------------------------------------------------

def check_null_and_double_free() -> None:
    from allocator import AllocError, HeapAllocator

    h = HeapAllocator(4096)
    before = [(b.offset, b.size, b.allocated) for b in h.blocks()]
    h.free(None)  # must be a silent no-op
    after = [(b.offset, b.size, b.allocated) for b in h.blocks()]
    assert before == after, "free(None) changed the heap; free(NULL) must do nothing at all"

    p = h.malloc(64)
    h.write(p, b"x" * 64)
    h.free(p)

    detected = False
    try:
        h.free(p)
    except AllocError:
        detected = True
    assert detected, (
        "freeing the same pointer twice was accepted: the second free must look at the "
        "allocated bit in the block's header and refuse (DoubleFree), not corrupt the list")

    # A detected double free must leave the list intact: the blocks still tile the arena and
    # the freed block can be handed out again.
    assert sum(b.size for b in h.blocks()) == h.arena_size - 2 * 16, (
        "the block chain no longer tiles the arena after the double free was rejected")
    q = h.malloc(64)
    assert q == p, f"the freed block at {p} was not reusable after the double free was rejected (got {q})"

    # An out-of-range pointer is rejected too, rather than silently trusted.
    try:
        h.free(h.arena_size + 64)
        raise AssertionError("free() of an out-of-range pointer was accepted")
    except AllocError:
        pass


# ---------------------------------------------------------------------------
# Step 5 (limit): fragmentation leaves no falsely-large free block
# ---------------------------------------------------------------------------

def check_fragmentation() -> None:
    from allocator import HeapAllocator

    h = HeapAllocator(4096)
    P = 64
    blocksize = 32 + P          # one request of P bytes -> a 96-byte block
    count = 42                  # 42 * 96 = 4032 bytes, arena usable is 4064: tail is 32
    ptrs = [h.malloc(P) for _ in range(count)]
    assert all(p is not None for p in ptrs), (
        f"could not place {count} blocks of {P} bytes in a {h.arena_size}-byte arena")

    for i in range(0, count, 2):
        h.free(ptrs[i])

    free_blocks = [b for b in h.blocks() if not b.allocated]
    largest = max(b.size for b in free_blocks)
    assert largest <= blocksize, (
        f"a free block of {largest} bytes exists although no two freed blocks are adjacent "
        f"(every free block should be {blocksize} bytes): coalescing merged non-neighbours")

    # No free block is adjacent to another free block; verify directly from the addresses.
    occupied = [(b.offset, b.offset + b.size) for b in free_blocks]
    occupied.sort()
    for (a0, a1), (b0, b1) in zip(occupied, occupied[1:]):
        assert a1 != b0, f"free blocks at [{a0},{a1}) and [{b0},{b1}) are adjacent but did not merge"

    # Two 96-byte blocks are needed for this request; they are not adjacent, so it must fail.
    need = 2 * P
    q = h.malloc(need)
    assert q is None, (
        f"malloc({need}) succeeded even though every free block is {blocksize} bytes and no two "
        f"are adjacent: a non-adjacent pair was falsely coalesced into a large block")

    # Free the rest: now everything is free and adjacent, so it becomes one huge block.
    for i in range(1, count, 2):
        h.free(ptrs[i])
    free_blocks = [b for b in h.blocks() if not b.allocated]
    assert len(free_blocks) == 1, (
        f"after freeing every block, {len(free_blocks)} free blocks remain: they must coalesce "
        f"into one")
    assert free_blocks[0].size >= count * blocksize, (
        f"the coalesced block is only {free_blocks[0].size} bytes, expected at least "
        f"{count * blocksize}")
    q = h.malloc(need)
    assert q is not None, "the fully coalesced heap must serve the request that fragmentation blocked"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("allocator.py", "16-byte alignment, no overlapping payloads", check_alignment_no_overlap),
    ("allocator.py", "freed blocks reused, adjacent blocks coalesce", check_reuse_and_coalesce),
    ("allocator.py", "stress run stays above the utilisation floor", check_stress_utilisation),
    ("allocator.py", "free(None) no-op, double free detected", check_null_and_double_free),
    ("allocator.py", "fragmentation: no falsely-large free block", check_fragmentation),
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
    print(f"\n{BOLD}Allocator From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built a malloc.{RESET}")
        print(f"  {GREY}Run the demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstring in that file walks through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
