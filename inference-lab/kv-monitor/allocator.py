"""
allocator.py — block accounting for the KV cache (solution).

The KV cache is a pool of fixed-size blocks; a sequence of `L` tokens holds
`ceil(L / block_size)` of them (PagedAttention, Kwon et al., SOSP 2023). Every
allocation and release goes through `BlockAllocator`, which is the one place
that must never let the pool go negative or over-release.

DESIGN DECISION — allocation is whole blocks, so the last block is partly wasted.
  Exact byte accounting would admit ~`block_size-1` more tokens per sequence,
  but no serving stack does it: attention kernels address whole blocks. The
  waste is real and the monitor's job is to make it visible, so it stays.

DESIGN DECISION — over-allocation and over-release raise instead of clamping.
  A serving loop that quietly clamps is a serving loop that serves wrong
  answers about its own memory. Raising turns a booking bug into a crash at the
  first bad step, which is where you want to find it.
"""

from __future__ import annotations


def blocks_needed(length: int, block_size: int) -> int:
    """Number of whole blocks a sequence of `length` tokens holds.

    ceil(length / block_size); 0 tokens hold 0 blocks. Raises ValueError on a
    negative length or a non-positive block size.
    """
    # TODO: Reject block_size <= 0 and length < 0 with ValueError; otherwise return (length + block_size - 1) // block_size (0 for length 0).
    raise NotImplementedError("blocks_needed")


class BlockAllocator:
    """A pool of `total_blocks` KV blocks."""

    def __init__(self, total_blocks: int) -> None:
        if total_blocks < 0:
            raise ValueError("total_blocks must not be negative")
        self.total_blocks = total_blocks
        self._used = 0

    @property
    def used_blocks(self) -> int:
        return self._used

    @property
    def free_blocks(self) -> int:
        return self.total_blocks - self._used

    @property
    def utilisation(self) -> float:
        return self._used / self.total_blocks if self.total_blocks else 0.0

    def fits(self, blocks: int) -> bool:
        """Would `blocks` more blocks fit?"""
        return 0 <= blocks <= self.free_blocks

    def allocate(self, blocks: int) -> None:
        """Take `blocks` from the pool. Raises ValueError if they do not fit."""
        # TODO: Raise ValueError on a negative count or one that does not fit (use self.fits); then self._used += blocks.
        raise NotImplementedError("BlockAllocator.allocate")

    def release(self, blocks: int) -> None:
        """Return `blocks` to the pool. Raises ValueError if over-releasing."""
        # TODO: Raise ValueError on a negative count or one greater than self._used; then self._used -= blocks.
        raise NotImplementedError("BlockAllocator.release")


if __name__ == "__main__":
    a = BlockAllocator(8)
    print("block allocator — total 8 blocks, block_size 4")
    print(f"  {blocks_needed(0, 4)=} {blocks_needed(4, 4)=} {blocks_needed(5, 4)=} "
          f"{blocks_needed(16, 4)=}")
    a.allocate(5)
    print(f"  allocate(5): used={a.used_blocks} free={a.free_blocks} "
          f"utilisation={a.utilisation:.0%}")
    print(f"  fits(3)={a.fits(3)} fits(4)={a.fits(4)}")
    a.release(5)
    print(f"  release(5): used={a.used_blocks} free={a.free_blocks}")
