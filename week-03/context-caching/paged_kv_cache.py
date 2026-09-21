"""
Paged KV Cache (PagedAttention) — From Scratch
===============================================
The idea behind vLLM: stop storing each sequence's KV cache in one contiguous
buffer. Store it in fixed-size blocks with a per-sequence block table, exactly
like OS virtual memory.

Build it to understand:
- Internal and external fragmentation, measured rather than described
- Why forking a sequence becomes a pointer copy
- Copy-on-write, and precisely which block gets copied
- Why preemption is only possible once blocks are relocatable

Learning Path:
1. Implement BlockManager allocate / free with a free list
2. Implement append_token — allocate a block only when the last one fills
3. Implement fork with reference counting
4. Implement copy-on-write for a shared partial block
5. Measure paged versus contiguous admission on the same request mix

Background:
  A contiguous KV cache must be sized for the longest sequence you allow. A
  request that stops after 100 of 2048 reserved tokens wastes 95% of its slot
  (internal fragmentation), and free space that is not in one run cannot be
  used at all (external fragmentation).

  Paged allocation: logical position i lives at physical block
  `block_table[i // block_size]`, offset `i % block_size`. Blocks need not be
  adjacent, so waste is at most one partial block per sequence and external
  fragmentation disappears entirely.

  The second win is sharing. Two sequences with a common prefix can point at
  the same physical blocks. Beam search, n>1 sampling and speculative decoding
  all become cheap, because a fork costs one list copy regardless of prefix
  length.
"""

from typing import Dict, List, Optional, Tuple


class OutOfMemory(Exception):
    """No free physical blocks left."""


class PhysicalBlock:
    __slots__ = ("index", "ref_count", "num_tokens", "content_hash")

    def __init__(self, index: int):
        self.index = index
        self.ref_count = 0
        self.num_tokens = 0
        self.content_hash: Optional[str] = None


class Sequence:
    """A request's logical view: a token list plus a table of physical blocks."""

    def __init__(self, seq_id: int, block_size: int):
        self.seq_id = seq_id
        self.block_size = block_size
        self.tokens: List[int] = []
        self.block_table: List[int] = []

    def num_blocks_needed(self, extra_tokens: int = 0) -> int:
        """TODO: ceil((len(tokens) + extra_tokens) / block_size)."""
        raise NotImplementedError

    def slot(self, position: int) -> Tuple[int, int]:
        """TODO: logical position -> (physical block index, offset within it).

        This two-line function is the entire virtual-memory analogy. Write it
        first; everything else is bookkeeping around it.
        """
        raise NotImplementedError


class BlockManager:
    """Allocator for a fixed pool of physical KV blocks."""

    def __init__(self, num_blocks: int = 64, block_size: int = 16):
        self.block_size = block_size
        self.blocks = [PhysicalBlock(i) for i in range(num_blocks)]
        self.free_blocks: List[int] = list(range(num_blocks))
        self.sequences: Dict[int, Sequence] = {}
        self.stats = {"allocated": 0, "freed": 0, "cow_copies": 0,
                      "shared_blocks": 0, "oom": 0}

    @property
    def num_free(self) -> int:
        return len(self.free_blocks)

    @property
    def num_blocks(self) -> int:
        return len(self.blocks)

    # -- Step 1 -------------------------------------------------------------

    def _allocate_block(self) -> PhysicalBlock:
        """TODO: pop from the free list, set ref_count = 1, reset num_tokens.
        Raise OutOfMemory when the list is empty."""
        raise NotImplementedError

    def _release_block(self, index: int) -> None:
        """TODO: decrement ref_count; return the block to the free list ONLY
        when it reaches zero. A block shared by three sequences must survive
        two of them finishing."""
        raise NotImplementedError

    def allocate(self, seq_id: int, tokens: List[int]) -> Sequence:
        """Admit a new sequence with enough blocks for its prompt.

        TODO: check num_blocks_needed() against num_free FIRST and raise before
        allocating anything — a half-allocated sequence leaks blocks. Then
        allocate, set each block's num_tokens, and build the block table.
        """
        raise NotImplementedError

    def free(self, seq_id: int) -> None:
        """TODO: release every block in the sequence's table and drop it."""
        raise NotImplementedError

    # -- Step 2 and 4 -------------------------------------------------------

    def append_token(self, seq_id: int, token: int) -> None:
        """Add one decoded token, allocating a block only when one fills up.

        TODO:
        1. Look at the last block in the table.
        2. If there is none, or it is full, allocate a new block and append it.
        3. Otherwise, if its ref_count > 1 it is SHARED and we are about to
           write into it — copy-on-write first (step 4).
        4. Increment that block's num_tokens and append the token.

        Step 3 is the subtle one. Miss it and a fork silently writes into its
        sibling's KV cache, and the bug shows up as one branch of a beam search
        producing text influenced by another.
        """
        raise NotImplementedError

    def _copy_on_write(self, sequence: Sequence, table_index: int) -> PhysicalBlock:
        """TODO: allocate a fresh block, copy num_tokens across, point the
        sequence's table entry at it, and release the old one."""
        raise NotImplementedError

    # -- Step 3 -------------------------------------------------------------

    def fork(self, parent_id: int, child_id: int) -> Sequence:
        """Share the parent's blocks instead of copying them.

        TODO: copy the token list and the block TABLE (a list of ints), then
        increment ref_count on every shared block. No KV data is copied.
        """
        raise NotImplementedError

    # -- Step 5 -------------------------------------------------------------

    def utilization(self) -> Dict[str, float]:
        """TODO: blocks used/free, token capacity of the used blocks, live
        tokens stored, and internal waste = 1 - stored/capacity."""
        raise NotImplementedError

    def shared_block_count(self) -> int:
        raise NotImplementedError


class ContiguousAllocator:
    """The pre-vLLM approach: reserve max_seq_len contiguous tokens per slot."""

    def __init__(self, total_tokens: int, max_seq_len: int):
        self.total_tokens = total_tokens
        self.max_seq_len = max_seq_len
        self.slots = total_tokens // max_seq_len
        self.used = 0

    def admit(self) -> bool:
        """TODO: admit if a slot is free — regardless of how short the actual
        request is. That indifference is the entire problem."""
        raise NotImplementedError


def _demo() -> None:
    """Once implemented, produce and explain:

    1. A 4096-token budget, max_seq_len 2048, and ten requests of 45-900 tokens.
       Contiguous admits 2 (88% wasted). Paged admits all 10 (under 3% wasted).

    2. Block-size sweep (1, 8, 16, 32, 128) on the same requests: waste rises
       with block size, block-table entries fall. 16 is the usual compromise
       and you should be able to say why from your own numbers.

    3. Fork a 200-token sequence (13 blocks) three times. Blocks consumed by the
       forks: ZERO. A copying implementation would have needed 39 more.

    4. Append one token to a fork. Exactly ONE block is copied — the partial
       tail. The 12 shared prefix blocks stay shared.

    5. Fill a small pool by generating until OutOfMemory. This is where a real
       scheduler preempts a sequence: swap its blocks to CPU memory, or drop
       them and recompute the prefill later. Both are only possible because
       blocks are relocatable — a contiguous allocator cannot do either.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
