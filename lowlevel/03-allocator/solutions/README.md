# Allocator From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, no dependencies.

```bash
cd solutions
python3 allocator.py       # the demo measurement below
python3 ../check.py --all  # 5/5 passing against this file
```

## Expected demo output

```text
4096-byte arena: 42 live allocations of 64 bytes
after freeing every other one: 22 free blocks, largest 96 bytes, utilisation 0.328
after freeing the rest: 1 free block of 4064 bytes
a 2000-byte request now fits at offset 32 (multiple of 16: True)
```

Reading the numbers:

- **42 live allocations, not 40 or 43.** Usable space is `4096 - 16 (prologue) - 16
  (epilogue) = 4064` bytes. A 64-byte request needs `16 + 64 + 16 = 96` bytes of block, so
  the first 42 requests consume `4032` bytes and the tail holds a 32-byte remnant, too
  small for another block. This is the fragmentation arithmetic step 5 depends on.
- **22 free blocks, largest 96.** The 21 freed blocks are every other one, so none is
  adjacent to another and none coalesces; the 22nd free block is the 32-byte tail. A broken
  coalescer that merges non-neighbours would report a largest free block of 192+.
- **Utilisation 0.328** = `21 allocated * 64 payload / 4096`. The other 0.672 is tags,
  alignment padding and the free half. This is why the stress check measures *peak*
  utilisation on a full heap, not this half-empty one.
- **One free block of 4064 bytes** after freeing the rest: all 42 blocks and the tail are
  now adjacent and coalesce back to a single block.
- **A 2000-byte request at offset 32** — the first payload address after the 16-byte
  prologue tag, and 32 is a multiple of 16.

## Implementation notes

- `_read_tag`/`_write_tag` store `size | allocated` in a 64-bit little-endian word. Size is
  a multiple of 16, so the low four bits are free and bit 0 is the allocated flag.
- `free` clears the tag, coalesces forward using the next block's header, then backward
  using the footer 16 bytes before this block. The prologue and epilogue are marked
  allocated so neither walk runs off the arena.
- `blocks()` walks the chain and refuses to return if the sizes do not tile the arena, so a
  corrupted tag raises `AllocError` instead of looping.

## Mutation coverage

`../_build/mutations.py` plants eight bugs (no alignment, no skipping, no split, no forward
coalesce, no backward coalesce, `free(None)` not a no-op, no double-free check, coalescing
with an allocated neighbour) and every one is caught by the check named in the module
README.
