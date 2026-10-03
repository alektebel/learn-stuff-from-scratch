"""
Step 6 — Paged KV cache
=======================
Virtual memory for tokens. A sequence owns a *block table* (list of
physical block ids). The tokens live in a pool of fixed-size blocks.

Invariants the checker will break you on:
  - allocating N tokens uses ceil(N / block_size) blocks
  - freeing a sequence returns its blocks to the free list
  - two sequences that share a prefix can share those blocks
  - forking a sequence (beam, n>1) costs ZERO extra blocks until a write
    (copy-on-write). This is the vLLM claim you already met in
    context-caching/paged_kv_cache.py — hold it here at server scale.
  - fragmentation: a pool can have free tokens and still fail an
    allocation when they are split across partial blocks you refuse to
    steal. `can_allocate` is about free BLOCKS, not free tokens.

DESIGN DECISION — why blocks, not a big tensor per sequence?
  A 2048-reserved tensor for a 12-token request wastes 99% of the
  allocation. Blocks make the waste at most one block, and they make
  prefix sharing a pointer copy.
"""

from typing import Dict, List, Optional, Set


class PagedKV:
    def __init__(self, num_blocks: int, block_size: int = 16):
        self.num_blocks = num_blocks
        self.block_size = block_size
        self.free: List[int] = list(range(num_blocks))
        self.tables: Dict[str, List[int]] = {}   # seq_id -> block ids
        self.refcnt: Dict[int, int] = {}         # block id -> sharers
        self.filled: Dict[str, int] = {}         # seq_id -> tokens stored

    def can_allocate(self, tokens: int) -> bool:
        """TODO: True iff free blocks >= ceil(tokens / block_size)."""
        raise NotImplementedError

    def allocate(self, seq_id: str, tokens: int) -> List[int]:
        """TODO: pop blocks, refcnt=1, store the table, filled=tokens.
        Raise MemoryError if can_allocate is False.
        """
        raise NotImplementedError

    def free_seq(self, seq_id: str) -> None:
        """TODO: decrement refcnt on each block; a block at 0 returns
        to free. Delete the table. Unknown seq_id is a no-op.
        """
        raise NotImplementedError

    def share_prefix(self, parent_id: str, child_id: str,
                     prefix_tokens: int) -> None:
        """TODO: child gets a COPY of the parent's first
        ceil(prefix_tokens / block_size) block ids, each refcnt += 1.
        child's filled = prefix_tokens. Parent is unchanged.
        """
        raise NotImplementedError

    def fork(self, parent_id: str, child_id: str) -> None:
        """Copy-on-write fork of the entire sequence.

        TODO: share_prefix(parent, child, filled[parent]).
        After this, parent and child have the SAME block ids.
        The next write to either must copy the touched block first —
        implement `write_token` that way.
        """
        raise NotImplementedError

    def write_token(self, seq_id: str) -> None:
        """Append one token, copy-on-write if the tail block is shared.

        TODO:
        If filled % block_size == 0, allocate a fresh block (or
        MemoryError).
        If the current tail block has refcnt > 1, allocate a new block,
        copy the logical ownership (refcnt old -= 1, new = 1), replace
        the tail in THIS sequence's table only.
        Then filled += 1.
        """
        raise NotImplementedError

    def fragmentation(self) -> float:
        """1 - (free_blocks * block_size) / (num_blocks * block_size)
        i.e. the used-block fraction. Not the token-fill fraction —
        a half-full block still counts as used. That gap IS fragmentation.
        """
        raise NotImplementedError
