"""
Paged KV Cache (PagedAttention) — Complete Solution

The idea behind vLLM: stop storing each sequence's KV cache in one contiguous
buffer. Store it in fixed-size blocks with a per-sequence block table, exactly
like OS virtual memory. Fragmentation collapses, and forking a sequence becomes
a pointer copy.
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

    def __repr__(self) -> str:
        return f"<Block {self.index} refs={self.ref_count} tokens={self.num_tokens}>"


class Sequence:
    """A request's logical view: a token list plus a table of physical blocks.

    The block table is the whole abstraction. Logical position i lives at
    physical block `table[i // block_size]`, offset `i % block_size`. Blocks
    need not be adjacent, so a sequence can grow without ever being moved or
    needing a contiguous run to be reserved up front.
    """

    def __init__(self, seq_id: int, block_size: int):
        self.seq_id = seq_id
        self.block_size = block_size
        self.tokens: List[int] = []
        self.block_table: List[int] = []

    def num_blocks_needed(self, extra_tokens: int = 0) -> int:
        total = len(self.tokens) + extra_tokens
        return (total + self.block_size - 1) // self.block_size

    def slot(self, position: int) -> Tuple[int, int]:
        """Logical position -> (physical block index, offset)."""
        return self.block_table[position // self.block_size], position % self.block_size

    def __repr__(self) -> str:
        return f"<Seq {self.seq_id} tokens={len(self.tokens)} " \
               f"blocks={self.block_table}>"


class BlockManager:
    """Allocator for a fixed pool of physical KV blocks.

    Two costs a contiguous allocator pays that this one does not:

    Internal fragmentation — a contiguous cache must be sized for the maximum
    possible length, so a request that stops after 100 of 2048 reserved tokens
    wastes 95% of its allocation. Paged allocation wastes at most one partial
    block per sequence.

    External fragmentation — free space exists but not in one run, so an
    allocation fails while memory is available. With blocks, any free block
    works and this failure mode simply disappears.
    """

    def __init__(self, num_blocks: int = 64, block_size: int = 16):
        self.block_size = block_size
        self.blocks = [PhysicalBlock(i) for i in range(num_blocks)]
        self.free_blocks: List[int] = list(range(num_blocks))
        self.sequences: Dict[int, Sequence] = {}
        self.stats = {"allocated": 0, "freed": 0, "cow_copies": 0,
                      "shared_blocks": 0, "oom": 0}

    # -- raw block operations ----------------------------------------------

    @property
    def num_free(self) -> int:
        return len(self.free_blocks)

    @property
    def num_blocks(self) -> int:
        return len(self.blocks)

    def _allocate_block(self) -> PhysicalBlock:
        if not self.free_blocks:
            self.stats["oom"] += 1
            raise OutOfMemory("no free blocks")
        block = self.blocks[self.free_blocks.pop()]
        block.ref_count = 1
        block.num_tokens = 0
        self.stats["allocated"] += 1
        return block

    def _release_block(self, index: int) -> None:
        block = self.blocks[index]
        block.ref_count -= 1
        if block.ref_count <= 0:
            block.ref_count = 0
            block.num_tokens = 0
            block.content_hash = None
            self.free_blocks.append(index)
            self.stats["freed"] += 1

    # -- sequence lifecycle -------------------------------------------------

    def allocate(self, seq_id: int, tokens: List[int]) -> Sequence:
        """Admit a new sequence and give it enough blocks for its prompt."""
        sequence = Sequence(seq_id, self.block_size)
        sequence.tokens = list(tokens)
        needed = sequence.num_blocks_needed()

        if needed > self.num_free:
            self.stats["oom"] += 1
            raise OutOfMemory(f"seq {seq_id} needs {needed} blocks, "
                              f"{self.num_free} free")

        remaining = len(sequence.tokens)
        for _ in range(needed):
            block = self._allocate_block()
            block.num_tokens = min(self.block_size, remaining)
            remaining -= block.num_tokens
            sequence.block_table.append(block.index)

        self.sequences[seq_id] = sequence
        return sequence

    def append_token(self, seq_id: int, token: int) -> None:
        """Add one decoded token, allocating a block only when one fills up.

        This is the decode-time allocation path, and it is why paged attention
        keeps memory tight: a sequence grows by one block at a time, on demand,
        instead of reserving its maximum length in advance.
        """
        sequence = self.sequences[seq_id]
        last_block = (self.blocks[sequence.block_table[-1]]
                      if sequence.block_table else None)

        if last_block is None or last_block.num_tokens == self.block_size:
            block = self._allocate_block()
            sequence.block_table.append(block.index)
            last_block = block
        elif last_block.ref_count > 1:
            # Copy-on-write: this partial block is shared with a fork, and we
            # are about to write into it.
            last_block = self._copy_on_write(sequence, len(sequence.block_table) - 1)

        last_block.num_tokens += 1
        sequence.tokens.append(token)

    def free(self, seq_id: int) -> None:
        sequence = self.sequences.pop(seq_id, None)
        if sequence is None:
            return
        for index in sequence.block_table:
            self._release_block(index)

    # -- forking ------------------------------------------------------------

    def fork(self, parent_id: int, child_id: int) -> Sequence:
        """Share the parent's blocks instead of copying them.

        This is what makes beam search, parallel sampling (n>1) and speculative
        branches cheap: the fork costs one list copy and some reference counts,
        no matter how long the shared prefix is.
        """
        parent = self.sequences[parent_id]
        child = Sequence(child_id, self.block_size)
        child.tokens = list(parent.tokens)
        child.block_table = list(parent.block_table)
        for index in child.block_table:
            self.blocks[index].ref_count += 1
            self.stats["shared_blocks"] += 1
        self.sequences[child_id] = child
        return child

    def _copy_on_write(self, sequence: Sequence, table_index: int) -> PhysicalBlock:
        """Give this sequence a private copy of a shared block before writing."""
        old_index = sequence.block_table[table_index]
        old_block = self.blocks[old_index]
        new_block = self._allocate_block()
        new_block.num_tokens = old_block.num_tokens
        sequence.block_table[table_index] = new_block.index
        self._release_block(old_index)
        self.stats["cow_copies"] += 1
        return new_block

    # -- reporting ----------------------------------------------------------

    def utilization(self) -> Dict[str, float]:
        used_blocks = self.num_blocks - self.num_free
        capacity_tokens = used_blocks * self.block_size
        live_tokens = sum(self.blocks[i].num_tokens
                          for i in range(self.num_blocks)
                          if self.blocks[i].ref_count > 0)
        return {
            "blocks_used": used_blocks,
            "blocks_free": self.num_free,
            "token_capacity": capacity_tokens,
            "tokens_stored": live_tokens,
            "internal_waste": 1 - (live_tokens / capacity_tokens) if capacity_tokens else 0.0,
        }

    def shared_block_count(self) -> int:
        return sum(1 for b in self.blocks if b.ref_count > 1)


# ---------------------------------------------------------------------------
# The comparison: contiguous vs paged
# ---------------------------------------------------------------------------

class ContiguousAllocator:
    """The pre-vLLM approach: reserve max_seq_len contiguous tokens per slot."""

    def __init__(self, total_tokens: int, max_seq_len: int):
        self.total_tokens = total_tokens
        self.max_seq_len = max_seq_len
        self.slots = total_tokens // max_seq_len
        self.used = 0

    def can_admit(self) -> bool:
        return self.used < self.slots

    def admit(self) -> bool:
        if not self.can_admit():
            return False
        self.used += 1
        return True

    def release(self) -> None:
        self.used = max(0, self.used - 1)


def _demo() -> None:
    print("=== Contiguous vs paged: how many requests fit? ===")
    total_tokens = 4096
    max_seq_len = 2048
    actual_lengths = [120, 340, 90, 512, 75, 200, 60, 900, 45, 130]

    contiguous = ContiguousAllocator(total_tokens, max_seq_len)
    admitted_contiguous = 0
    for _ in actual_lengths:
        if contiguous.admit():
            admitted_contiguous += 1

    manager = BlockManager(num_blocks=total_tokens // 16, block_size=16)
    admitted_paged = 0
    for i, length in enumerate(actual_lengths):
        try:
            manager.allocate(i, list(range(length)))
            admitted_paged += 1
        except OutOfMemory:
            break

    print(f"KV budget: {total_tokens} tokens, max_seq_len {max_seq_len}, "
          f"block size 16")
    print(f"actual request lengths: {actual_lengths}")
    print(f"contiguous: {admitted_contiguous}/{len(actual_lengths)} admitted "
          f"({contiguous.slots} slots of {max_seq_len} tokens each)")
    print(f"paged:      {admitted_paged}/{len(actual_lengths)} admitted")
    util = manager.utilization()
    print(f"paged waste: {util['internal_waste']:.1%} "
          f"({util['tokens_stored']} live tokens in "
          f"{util['token_capacity']} tokens of blocks)")
    print(f"contiguous waste: "
          f"{1 - sum(actual_lengths[:admitted_contiguous]) / (admitted_contiguous * max_seq_len):.1%}")

    print("\n=== Block size trade-off ===")
    print(f"{'block size':>12}{'blocks used':>14}{'waste':>10}{'table entries':>16}")
    for block_size in (1, 8, 16, 32, 128):
        manager = BlockManager(num_blocks=8192 // block_size, block_size=block_size)
        for i, length in enumerate(actual_lengths):
            manager.allocate(i, list(range(length)))
        util = manager.utilization()
        entries = sum(len(s.block_table) for s in manager.sequences.values())
        print(f"{block_size:>12}{util['blocks_used']:>14}"
              f"{util['internal_waste']:>9.1%}{entries:>16}")
    print("Small blocks waste less memory but grow the block tables and the")
    print("per-step gather cost. 16 is the usual compromise.")

    print("\n=== Forking is a pointer copy ===")
    manager = BlockManager(num_blocks=64, block_size=16)
    prompt = list(range(200))                       # 200-token prompt
    manager.allocate(1, prompt)
    before = manager.num_free
    print(f"parent sequence: {len(prompt)} tokens in "
          f"{len(manager.sequences[1].block_table)} blocks")

    for child_id in (2, 3, 4):
        manager.fork(1, child_id)
    print(f"forked 3 children (parallel sampling, n=4)")
    print(f"blocks consumed by the forks: {before - manager.num_free}")
    print(f"blocks now shared by >1 sequence: {manager.shared_block_count()}")
    print(f"a copying implementation would have needed "
          f"{3 * len(manager.sequences[1].block_table)} more blocks")

    print("\n=== Copy-on-write on divergence ===")
    print(f"before: seq2 table tail {manager.sequences[2].block_table[-3:]}")
    manager.append_token(2, 999)
    print(f"after appending one token to seq 2:")
    print(f"        seq2 table tail {manager.sequences[2].block_table[-3:]}")
    print(f"        seq1 table tail {manager.sequences[1].block_table[-3:]}")
    print(f"copy-on-write copies: {manager.stats['cow_copies']} "
          f"(one block, not {len(manager.sequences[1].block_table)})")
    print("Only the block being written is copied. The 12 shared prefix blocks")
    print("stay shared, which is the whole point.")

    print("\n=== Growing under memory pressure ===")
    manager = BlockManager(num_blocks=16, block_size=16)
    manager.allocate(1, list(range(200)))
    print(f"admitted a 200-token prompt: {manager.num_free} blocks free")
    generated = 0
    try:
        for _ in range(200):
            manager.append_token(1, 0)
            generated += 1
    except OutOfMemory:
        pass
    print(f"generated {generated} tokens before running out of blocks")
    print(f"total sequence length reached: {len(manager.sequences[1].tokens)}")
    print("A real scheduler handles this by preempting a sequence: swap its")
    print("blocks to CPU memory, or drop them and recompute the prefill later.")
    print("Preemption is possible precisely BECAUSE blocks are relocatable.")


if __name__ == "__main__":
    _demo()
