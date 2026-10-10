# Allocator From Scratch

A `malloc`/`free` over a fixed byte arena, in pure Python 3 (standard library only),
built one mechanism at a time: boundary tags, an implicit free list, first fit, splitting,
and neighbour coalescing.

The source is Bryant & O'Hallaron, *Computer Systems: A Programmer's Perspective* (CS:APP),
chapter 9, *Virtual Memory*, section 9.9, *Dynamic Memory Allocation*. The [solution
docstring](solutions/allocator.py) maps each subsection to the code: 9.9.5 boundary tags,
9.9.6/9.9.7 implicit free lists and first fit, 9.9.8 splitting, 9.9.11 coalescing, 9.9.12
"putting it together".

The point is not to call Python's allocator — it is to be one. You hand out integer
offsets into a `bytearray`, write bytes at them, and keep the block tags consistent enough
that a freed block is reused and two free neighbours become one.

## What you build

The top-level `allocator.py` is a **template**: each function you write keeps its signature
and docstring, has a `TODO` with a hint, and raises `NotImplementedError`. The arena setup,
the boundary-tag read/write primitives, `write`/`read` and `allocated_payload` are provided
(scaffolding, not the lesson). `solutions/` holds a working version.

| Step | Mechanism | Check |
|---|---|---|
| 1 | first fit over the implicit free list; 16-byte-aligned, non-overlapping payloads | 1 |
| 2 | a freed block is reused; adjacent free blocks coalesce | 2 |
| 3 | splitting and reuse keep utilisation above the floor | 3 |
| 4 | `free(None)` is a no-op; a double free is refused | 4 |
| 5 | alternating alloc/free leaves no falsely-large free block | 5 |

## How to use this directory

```bash
cd lowlevel/03-allocator
python3 check.py        # what to build next; stops at the first gap
python3 check.py 4      # one step
python3 check.py --all  # everything
```

`check.py` runs 5 checks against **your** code and never imports `solutions/`. When a check
fails it names the likely cause (e.g. *"first fit must reuse the earliest free block that
fits, not carve a new one from the tail"*).

## Design decisions, named

Each one is spelled out with alternatives and cost in the [solution
docstring](solutions/allocator.py). In short:

- **Implicit free list, not explicit.** The size tag in every block *is* the list; a search
  walks every block. An explicit list threads pointers through free payloads, so it visits
  fewer blocks but adds a second structure to keep consistent. Cost: O(number of blocks) per
  search.
- **16-byte payload alignment via a 16-byte header.** Every block size is a multiple of 16,
  so `block_start + 16` is aligned. Cost: up to 15 bytes of internal fragmentation per
  allocation.
- **First fit, not best fit or next fit.** First fit reuses the earliest hole, which is what
  step 2 asserts. Cost: the front of the heap is split into slivers over time.
- **Utilisation counts payload capacity, not requested bytes** (CS:APP's definition). That
  includes alignment padding and unsplit tails. Cost: a 1-byte request occupies a 48-byte
  block, so utilisation looks low for tiny allocations.
- **A double free is caught by the allocated bit in the header**, not by a separate live
  set. Cost: a wild pointer that lands on a plausible tag is not caught; only a genuine
  second free is.

## Questions to answer before reading the solutions

1. Why is a footer needed at all, when the header already stores the size?
2. Step 5 allocates 42 blocks of 64 bytes in a 4096-byte arena. Why 42, and why does a
   request for 128 bytes fail there but succeed after everything is freed?
3. `malloc(0)` returns `None` here. Real `malloc(0)` may return a unique pointer that must
   be freed. What does the choice buy, and what does it cost a caller?
4. In step 2, why is `d == b` guaranteed and not merely *usually* true?
5. If `free` marked the block free but never coalesced, which of the five checks would
   still pass, and which would fail?

## Limits

- One arena, allocated up front; there is no `sbrk`/`mmap` path to grow the heap, so a
  request that does not fit returns `None` (real `malloc` returns `NULL`).
- Python integers stand in for addresses. That makes the pointer arithmetic honest but
  means no actual process memory is protected: a bogus offset can still be read.
- No explicit free list, no segregated free lists, no `realloc`, no thread safety, and no
  rebalancing heuristics. The README of CS:APP §9.9.14 (segregated lists) is the next rung.
- The stress check uses a seeded `random.Random`, so the workload is deterministic; it is
  not a benchmark of speed, only of space.

## The checker was itself tested

Eight classic bugs were planted in copies of the solution, and each had to be caught by its
check (`_build/mutations.py`, run with `mutate.py`):

| Planted bug | Caught by |
|---|---|
| payload not 16-byte aligned (return `off + 8`) | step 1 |
| first fit does not skip allocated blocks | step 1 |
| no splitting: a request consumes the whole free block | step 1 |
| `free()` does not coalesce with the next block | step 2 |
| `free()` does not coalesce with the previous block | step 2 |
| `free(None)` is not a no-op | step 4 |
| double free is not detected (no allocated-bit check) | step 4 |
| coalesce with the next block even when it is allocated | step 5 |
