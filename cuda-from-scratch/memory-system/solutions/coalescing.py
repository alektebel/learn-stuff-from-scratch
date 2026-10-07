"""
Coalescing — what one warp memory instruction really moves
==========================================================

Source: NVIDIA's matrix-transpose post (coalescing, tiling, bank conflicts) and the
performance checklist in GPU MODE lecture 8. Restated, not copied.

A warp is 32 threads. When they execute one load, the hardware looks at the 32 addresses
at once and fetches memory in fixed-size *sectors*: the smallest unit the memory system
transfers is 32 bytes. Every distinct sector that any of the 32 addresses falls in is
transferred in full, whether or not the warp uses all of its bytes.

So the question is never "did the warp issue one instruction" — it did. It is "how many
sectors did that one instruction cost, and how many did we actually need".

DESIGN DECISION — count sectors, not cache lines?
The L1 cache line is 128 bytes, four sectors. One might count the 128-byte lines the warp
touches and call that the transaction count. That hides the limit case: a stride-32-byte
access touches 8 lines but 32 sectors, and the sectors are what consume memory bandwidth.
Counting lines makes a 4x-worse kernel look the same. Chosen: count 32-byte sectors, the
DRAM transfer granularity.

DESIGN DECISION — bytes per thread as an argument?
A load from a float32 array and a load from a float64 array have the same addresses but
move different useful bytes. Hardcoding 4 would score a double-precision kernel as 100%
efficient when it is 50%. Chosen: `bytes_per_thread` is explicit, default 4 (the common
float32 / int32 case).
"""

SECTOR_BYTES = 32
LINE_BYTES = 128
WARP = 32


def sector_of(address, sector_bytes=SECTOR_BYTES):
    """The sector a single byte address belongs to: address // 32."""
    return address // sector_bytes


def sectors_touched(addresses, sector_bytes=SECTOR_BYTES):
    """Distinct 32-byte sectors spanned by one warp instruction's addresses.

    `addresses` are byte offsets, one per active thread. Only the set of sectors matters,
    never their order.
    """
    return len({sector_of(a, sector_bytes) for a in addresses})


def transferred_bytes(addresses, sector_bytes=SECTOR_BYTES):
    """Bytes the memory system moves: sectors touched x sector size."""
    return sectors_touched(addresses, sector_bytes) * sector_bytes


def efficiency(addresses, bytes_per_thread=4, sector_bytes=SECTOR_BYTES):
    """Useful bytes / transferred bytes for one warp instruction, in [0, 1].

    A fully coalesced float32 access over 32 consecutive threads is 128 useful bytes
    across 4 sectors: 1.0. A stride-32-byte access is 128 useful across 1024: 0.125.
    """
    if not addresses:
        return 1.0
    useful = len(addresses) * bytes_per_thread
    return useful / transferred_bytes(addresses, sector_bytes)


def is_fully_coalesced(addresses, bytes_per_thread=4, sector_bytes=SECTOR_BYTES):
    """True when the warp moves no byte it does not use."""
    return efficiency(addresses, bytes_per_thread, sector_bytes) == 1.0


def _demo():
    stride4 = [t * 4 for t in range(WARP)]
    stride8 = [t * 8 for t in range(WARP)]
    stride32 = [t * 32 for t in range(WARP)]
    misaligned = [7 + t * 4 for t in range(WARP)]
    print(f"{'pattern':<28}{'sectors':>8}{'efficiency':>12}")
    for name, addrs in (
        ("contiguous f32 (stride 4)", stride4),
        ("stride 8 bytes", stride8),
        ("stride 32 bytes", stride32),
        ("contiguous, offset 7", misaligned),
    ):
        print(f"{name:<28}{sectors_touched(addrs):>8}{efficiency(addrs):>12.3f}")


if __name__ == "__main__":
    _demo()
