# Memory Layout — struct size, alignment, padding

From-scratch implementation of the C struct-layout rule on x86-64: where each
member lands, why a struct is bigger than the sum of its fields, how to pack it
into its exact in-memory bytes, and how to reorder the fields to make it smaller.

Source: Bryant & O'Hallaron, *Computer Systems: A Programmer's Perspective*
(CS:APP), Chapter 3 "Machine-Level Representation of Programs", §3.9
"Heterogeneous Data Structures" — Structures (3.9.1) and Data Alignment (3.9.3).
This module restates the rule and rebuilds it; it does not copy the book.

Why it matters: padding is invisible to the program and real in memory. It is
what `sizeof` reports, what a `memcmp` of two structs compares, and what a raw
`write()` of a struct-length buffer sends to the wire — three bugs you only see
by knowing the layout.

## What you build

| Step | File | Mechanism |
|---|---|---|
| 1 | `layout.py` | natural `sizeof` and member offsets; checked against the real C ABI (`ctypes`) and `struct.calcsize` |
| 2 | `layout.py` | nested structs contribute their own size *and alignment* as one member |
| 3 | `layout.py` | `format_string` (padding spelled out) and the packed byte layout vs a hand-written format string |
| 4 | `layout.py` | `pack`/`unpack`: padding bytes are zero, round-trips are exact |
| 5 | `reorder.py` | reordering a padded struct strictly reduces its size |
| 6 | `reorder.py` | the reordered size equals the brute-force optimum over all permutations |
| 7 | `layout.py` | **limit:** a packed struct is smaller, but the unaligned accesses are flagged |
| 8 | `layout.py` | **limit:** an over-aligned member pads the whole struct, not just the member |

## How to use this directory

Top-level `layout.py` and `reorder.py` are **templates**: each function keeps its
signature and docstring, has a `TODO` with a one-line hint, and raises
`NotImplementedError`. `solutions/` holds working versions for when you are
stuck, or to compare afterwards.

```bash
cd lowlevel/02-memory-layout
python3 check.py        # what to build next; stops at the first gap
python3 check.py 8      # one step
python3 check.py 3 6    # a range
python3 check.py --all  # everything
```

`check.py` runs the checks against **your** code and never imports `solutions/`.
It uses `ctypes` as an independent implementation of the platform ABI and the
`struct` module for byte strings, so it can tell you *why* a size disagree, not
just that it did.

## The rules, in one place

- **Member offset.** Round the running offset up to the member's own alignment,
  place it, then advance by its size. The skipped bytes are internal padding.
- **Struct alignment.** The maximum of its members' alignments.
- **Struct size.** The end offset rounded **up to the struct's alignment**
  (trailing padding). This is the part a first implementation forgets, and it
  is why `{char; int; char}` is 12, not 9 or 6.
- **Nested struct.** Laid out by its own rules, then treated as a single member
  of that size and alignment.
- **Packing.** Removing padding makes the struct smaller but can leave a 4- or
  8-byte member on an odd offset: a fault or a hidden fix-up on the CPU. Space
  and safety are the trade.
- **Reordering.** Declaring the largest alignments first leaves nothing to pad
  between members; only the final round-up remains. It is optimal for these
  types (steps 6 and 8's brute force prove it), but it changes the byte layout,
  which an on-disk or ABI struct cannot afford.

## Design decisions, named

Each file opens with its own decisions; in short:

- **Model the ABI, don't query it** (`layout.py`). An explicit `NATIVE_TYPES`
  table teaches the rule; the checks cross-check it against `ctypes` so it cannot
  drift silently. Cost: the table is LP64/x86-64-specific.
- **Little-endian packed bytes.** Native on x86-64 and deterministic, so the
  byte strings reproduce anywhere the checks run.
- **`unaligned_fields` takes the layout mode.** A natural struct is aligned by
  construction and reports nothing; a packed one reports the members the CPU
  would penalise. Reporting unaligned members of an aligned struct would be a
  false alarm.
- **`format_string` writes padding as explicit `x` bytes**, so
  `struct.calcsize(format_string(f)) == sizeof(f)` holds instead of silently
  undercounting the trailing padding.
- **Reordering is optimal, not heuristic** (`reorder.py`). Sorting by decreasing
  alignment is proven by brute force in step 6; `padding_bytes` distinguishes
  internal from trailing holes so a shrinking is only claimed when real.

## The checker was itself tested

Seven classic bugs were planted in copies of the solutions; each must be caught
by its check:

| Planted bug | Caught by |
|---|---|
| forgetting the struct's trailing padding | step 1 |
| ignoring a nested struct's alignment | step 2 |
| the natural format string drops trailing padding | step 3 |
| treating a packed layout as if it were aligned | step 7 |
| `bytes_saved` always reports zero | step 5 |
| reordering is a no-op | step 6 |
| `padding_bytes` ignores the real padding | step 5 |

Two initially slipped through. The natural-format-string mutation was invisible
because the struct used in step 3 happened to end exactly on its alignment (no
trailing padding to drop); step 3 now adds `{int; char}`, where the trailing 3
bytes are the whole point. The "wrong sort direction" mutation turned out to be
a non-bug here — for sizes that are powers of two, ascending order is also
optimal — so it was replaced with mutations that are genuinely wrong.

## Questions to answer before reading the solutions

1. `{char; int; char}` is 12 bytes. Explain why neither 6 (sum) nor 9
   (`struct.calcsize`'s native answer) is `sizeof`.
2. Why does an over-aligned member enlarge the *whole* struct? Which member is
   responsible for the struct's alignment?
3. Packing removes padding. Name one workload where the packed struct is the
   right call and one where it is a latent crash.
4. Reordering is free in C but not in the byte stream. Name a case where you must
   **not** reorder even though it would shrink the struct.
5. A CPU often reports an unaligned access only as a performance loss, not a
   fault. Why does that make the packed bug worse, not better?

## Limits

- The data model is x86-64 / LP64 (as the checks' `ctypes` oracle reflects):
  `long` and pointers are 8 bytes, `longdouble` is 16 bytes aligned to 16. A
  different ABI (ILP32, LLP64) would need its own table.
- Only scalar members and nested structs; no arrays, unions, bitfields, or
  `_Alignas`. Arrays would add `element_size × count` with the element's
  alignment; the rule itself does not change.
- Byte order is fixed to little-endian on purpose. `format_string` cannot
  express a nested struct (no single `struct` code), so `pack`/`unpack` do the
  nested work by hand.
- Packing is modelled as "no padding"; real `#pragma pack` also propagates to
  nested types, which this module leaves to the nested struct's own setting.
