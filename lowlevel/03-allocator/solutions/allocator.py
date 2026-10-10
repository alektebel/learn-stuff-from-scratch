"""
A dynamic memory allocator over a fixed arena
=============================================

Source: Bryant & O'Hallaron, *Computer Systems: A Programmer's Perspective* (CS:APP),
chapter 9, "Virtual Memory", section 9.9, "Dynamic Memory Allocation" — specifically
9.9.5 (the header/footer boundary tags that let a block find its neighbours), 9.9.6/9.9.7
(an implicit free list searched with first fit), 9.9.8 (splitting a free block), 9.9.11
(coalescing free neighbours using the boundary tags) and 9.9.12 ("putting it together").
Restated in our own words: the heap is one contiguous byte array. Every block carries a
tag — its size and an allocated bit — in a header at its start and an identical copy in a
footer at its end. To serve a request we walk the blocks from the beginning and take the
first free one large enough. If the leftover is big enough to be a block itself, it is
split off. Freeing a block marks it free and merges it with any free block physically
before or after it.

The allocator hands out integers, not Python objects: an integer is an offset into
``self.mem``, the same way a C pointer is an address.  ``read``/``write`` move bytes at
those offsets so the caller can actually store something.

DESIGN DECISION - implicit free list or explicit free list?
CS:APP shows both. An *explicit* free list threads ``next``/``prev`` pointers through the
payloads of free blocks, so the allocator only visits free blocks; that needs the pointers
stored inside free payloads and kept consistent on every split and coalesce. An *implicit*
free list is just the size field of every block: the allocator walks every block, free and
allocated. Chosen: implicit. It is the layout that makes boundary tags unavoidable, which
is the lesson here, and it survives a corrupted list more gracefully because there is no
second structure to keep in sync. The cost is that every search is O(number of blocks).

DESIGN DECISION - why is every payload 16-byte aligned?
A tag is 8 bytes (a 64-bit size and flag word). Payloads start ``HEADER`` bytes into a
16-byte-aligned block. Choosing ``HEADER = 16`` (and rounding every block size up to 16)
puts the payload at a multiple of 16. Real ``malloc`` promises ``max_align_t``, commonly
16, because SSE and long double loads require it. The cost is up to 15 bytes of internal
fragmentation per allocation; a smaller header would be tighter but would break alignment.

DESIGN DECISION - first fit, not best fit or next fit
First fit returns the first free block large enough. Best fit must scan the whole heap to
minimise the leftover and tends to litter it with tiny unusable fragments; next fit keeps a
roving cursor and has better throughput but worse space. Chosen: first fit — it is the
simplest to reason about and it reuses an early freed block immediately, which is exactly
what the reuse check asserts. Its cost is that the front of the heap stays hot and can be
split into slivers.

DESIGN DECISION - what "utilisation" counts
CS:APP defines utilisation as *allocated payload* over *heap size*, where a block's payload
is its size minus the header and footer. That includes the padding a request was rounded up
to and any tail space a block was not split because the remainder was too small. Chosen:
that definition, ``allocated capacity / arena_size``; tracking *requested* bytes instead
would flatter the allocator and hide both kinds of fragmentation. Cost: a 1-byte request
occupies a 48-byte block, so utilisation looks low for tiny allocations.

DESIGN DECISION - how a double free is detected
The allocated bit in the header is the allocator's own record of what is live. A second
free of the same pointer reaches a block whose header already says "free", so ``free``
raises ``DoubleFree`` before touching the tags. No separate live-pointer set is kept: that
set would be a second source of truth that could disagree with the heap, and a real
allocator does not have one. Cost: a wild pointer that happens to land on a 16-byte
boundary whose first word looks like an allocated tag is not caught. That is why the
checker only demands that a *double free* is detected, and why ``free(None)`` is a no-op.
"""

from __future__ import annotations

from collections import namedtuple

_WORD = 8          # bytes per size/flag word
ALIGN = 16         # every payload starts at a multiple of this
_HEADER = 16       # bytes of boundary tag at the start of a block
_FOOTER = 16       # identical tag at the end
_MIN_BLOCK = _HEADER + _FOOTER   # a block with no payload at all
_ALLOC = 1         # low bit of a tag word

Block = namedtuple("Block", "offset size payload capacity allocated")


class AllocError(Exception):
    """Base class for invalid heap operations."""


class DoubleFree(AllocError):
    """free() was called on a block that is already free."""


class InvalidFree(AllocError):
    """free() was called on something that is not a live block start."""


def align_up(n: int) -> int:
    """Round ``n`` up to the next multiple of ALIGN."""
    return (n + ALIGN - 1) & ~(ALIGN - 1)


class HeapAllocator:
    """A first-fit allocator with boundary tags over a fixed-size bytearray."""

    def __init__(self, arena_size: int = 4096):
        if arena_size % ALIGN or arena_size < 4 * ALIGN:
            raise ValueError(f"arena_size must be a multiple of {ALIGN} and at least {4 * ALIGN}")
        self.arena_size = arena_size
        self.mem = bytearray(arena_size)
        # Prologue: the footer of a virtual block before the first real one. Marked
        # allocated so backward coalescing never walks off the front.
        self._write_tag(0, 0, True)
        # Epilogue: a virtual block at the end, marked allocated so forward coalescing
        # never walks off the back.
        self._write_tag(arena_size - _HEADER, 0, True)
        # One free block spanning everything between them.
        self._set_block(_HEADER, arena_size - _HEADER - _FOOTER, False)

    # -- boundary tags ------------------------------------------------------------------
    def _read_tag(self, offset: int):
        """Return ``(size, allocated)`` from the tag word at ``offset``."""
        raw = int.from_bytes(self.mem[offset:offset + _WORD], "little")
        return raw & ~(ALIGN - 1), bool(raw & _ALLOC)

    def _write_tag(self, offset: int, size: int, allocated: bool) -> None:
        raw = (size & ~(ALIGN - 1)) | (_ALLOC if allocated else 0)
        self.mem[offset:offset + _WORD] = raw.to_bytes(_WORD, "little")

    def _set_block(self, start: int, size: int, allocated: bool) -> None:
        """Write the header and the matching footer of the block at ``start``."""
        self._write_tag(start, size, allocated)
        self._write_tag(start + size - _FOOTER, size, allocated)

    # -- allocation ---------------------------------------------------------------------
    def _find_first_fit(self, need: int):
        """Walk the implicit free list and return the first free block >= ``need``."""
        off = _HEADER
        limit = self.arena_size - _HEADER
        while off < limit:
            size, allocated = self._read_tag(off)
            if size == 0:
                break
            if not allocated and size >= need:
                return off
            off += size
        return None

    def malloc(self, n: int):
        """Allocate at least ``n`` bytes. Return a 16-byte-aligned offset, or None.

        ``n <= 0`` returns None: the arena has no address to hand back for a zero-length
        object, and free(None) is then naturally a no-op.
        """
        if n <= 0:
            return None
        need = _HEADER + align_up(n) + _FOOTER
        off = self._find_first_fit(need)
        if off is None:
            return None
        size, _ = self._read_tag(off)
        if size - need >= _MIN_BLOCK:
            self._set_block(off, need, True)
            self._set_block(off + need, size - need, False)
        else:
            self._set_block(off, size, True)
        return off + _HEADER

    def free(self, ptr) -> None:
        """Release a block. ``None`` is a no-op; every other bad pointer raises."""
        if ptr is None:
            return
        if not isinstance(ptr, int) or ptr % ALIGN != 0:
            raise InvalidFree(f"pointer {ptr!r} is not a {ALIGN}-byte aligned integer")
        head = ptr - _HEADER
        if head < _HEADER or head + _MIN_BLOCK > self.arena_size - _HEADER:
            raise InvalidFree(f"pointer {ptr} is outside the heap")
        size, allocated = self._read_tag(head)
        if not allocated:
            raise DoubleFree(f"free of {ptr}: the block is already free (double free?)")
        self._set_block(head, size, False)
        # Coalesce with the next block if it is free.
        nxt = head + size
        n_size, n_alloc = self._read_tag(nxt)
        if nxt < self.arena_size - _HEADER and not n_alloc:
            size += n_size
            self._set_block(head, size, False)
        # Coalesce with the previous block, found through this block's leading footer.
        p_size, p_alloc = self._read_tag(head - _FOOTER)
        if not p_alloc:
            head -= p_size
            size += p_size
            self._set_block(head, size, False)

    # -- inspection ---------------------------------------------------------------------
    def blocks(self):
        """Return every block, in arena order, as ``Block`` namedtuples."""
        out = []
        off = _HEADER
        limit = self.arena_size - _HEADER
        while off < limit:
            size, allocated = self._read_tag(off)
            if size < _MIN_BLOCK:
                raise AllocError(f"corrupt heap at offset {off}: block size {size}")
            out.append(Block(off, size, off + _HEADER, size - _HEADER - _FOOTER, allocated))
            off += size
        if off != limit:
            raise AllocError(f"block chain ends at {off}, epilogue is at {limit}")
        return out

    def allocated_payload(self) -> int:
        """Bytes of payload held by allocated blocks (capacity, not requested)."""
        return sum(b.capacity for b in self.blocks() if b.allocated)

    def utilization(self) -> float:
        """Allocated payload over arena size, CS:APP's definition."""
        return self.allocated_payload() / self.arena_size

    # -- reading and writing memory -----------------------------------------------------
    def write(self, ptr: int, data: bytes) -> None:
        head = ptr - _HEADER
        size, allocated = self._read_tag(head)
        if not allocated:
            raise InvalidFree(f"write to {ptr}: not a live allocation")
        capacity = size - _HEADER - _FOOTER
        if len(data) > capacity:
            raise ValueError(f"write of {len(data)} bytes exceeds the {capacity} bytes at {ptr}")
        self.mem[ptr:ptr + len(data)] = data

    def read(self, ptr: int, n: int) -> bytes:
        if ptr < 0 or ptr + n > self.arena_size:
            raise ValueError(f"read of {n} bytes at {ptr} is outside the arena")
        return bytes(self.mem[ptr:ptr + n])


if __name__ == "__main__":
    # Demo: fill a heap, free every other block, then coalesce it all back and measure.
    arena = 4096
    h = HeapAllocator(arena)
    ptrs = []
    while True:
        p = h.malloc(64)
        if p is None:
            break
        ptrs.append(p)
    for p in ptrs[::2]:
        h.free(p)
    free_now = [b for b in h.blocks() if not b.allocated]
    print(f"{arena}-byte arena: {len(ptrs)} live allocations of 64 bytes")
    print(f"after freeing every other one: {len(free_now)} free blocks, "
          f"largest {max(b.size for b in free_now)} bytes, utilisation {h.utilization():.3f}")
    for p in ptrs[1::2]:
        h.free(p)
    merged = [b for b in h.blocks() if not b.allocated]
    print(f"after freeing the rest: {len(merged)} free block of {merged[0].size} bytes")
    big = h.malloc(2000)
    print(f"a 2000-byte request now fits at offset {big} (multiple of {ALIGN}: {big % ALIGN == 0})")
