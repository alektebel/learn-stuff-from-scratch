"""
Roofline — arithmetic intensity against two ceilings
====================================================

Source: Williams, Waterman and Patterson, "Roofline: An Insightful Visual Performance Model
for Multicore Architectures" (2009). Restated, not copied.

A kernel's arithmetic intensity (AI) is flops per byte moved. Two ceilings bound it:

    attainable flops/s = min(peak_compute, bandwidth x AI)

Below the ridge point (AI = peak_compute / bandwidth) the kernel is memory-bound: adding
compute is free, moving bytes is not. Above it, it is compute-bound. The ridge point is the
only number needed to classify a kernel.

DESIGN DECISION — model the memory roof as one bandwidth, not a cache hierarchy?
The full roofline has several roofs (L1, L2, DRAM). One bandwidth is the MVP and already
exposes the lesson: a kernel below the ridge does not care about its flops. Chosen: one
DRAM bandwidth and one peak-compute ceiling. The limit case left out is cache blocking,
which moves the ridge; that is a later module.

DESIGN DECISION — memory-bound is strict `<`?
At exactly the ridge point both ceilings are equal, so neither is the bottleneck. Chosen:
memory-bound iff AI * bandwidth < peak, so the ridge point classifies as compute-bound and
the two cases are never both true.
"""


def arithmetic_intensity(flops, bytes_moved):
    """Flops performed per byte moved."""
    return flops / bytes_moved


def ridge_point(peak_flops, bandwidth):
    """The AI at which the memory and compute roofs meet (flops per byte)."""
    return peak_flops / bandwidth


def attainable_flops(ai, peak_flops, bandwidth):
    """The lower of the two roofs: min(peak, bandwidth * AI)."""
    return min(peak_flops, ai * bandwidth)


def is_memory_bound(ai, peak_flops, bandwidth):
    """True when the memory roof is strictly below the compute roof."""
    return ai * bandwidth < peak_flops


def bottleneck(ai, peak_flops, bandwidth):
    """"memory" or "compute"."""
    return "memory" if is_memory_bound(ai, peak_flops, bandwidth) else "compute"


def attainable_fraction(ai, peak_flops, bandwidth):
    """Fraction of peak compute the kernel can reach (the memory roof, when bound)."""
    return attainable_flops(ai, peak_flops, bandwidth) / peak_flops


def _demo():
    peak, bandwidth = 1.0e13, 1.0e12
    print(f"peak {peak:.1e} flop/s, bandwidth {bandwidth:.1e} B/s -> "
          f"ridge {ridge_point(peak, bandwidth):.1f} flop/byte")
    print(f"{'kernel':<16}{'AI':>12}{'bound':>10}{'fraction of peak':>18}")
    for name, ai in (("vector add", 1 / 6), ("matmul N=1024", 1024 / 6), ("AI=2", 2.0)):
        print(f"{name:<16}{ai:>12.2f}{bottleneck(ai, peak, bandwidth):>10}"
              f"{attainable_fraction(ai, peak, bandwidth):>18.3f}")


if __name__ == "__main__":
    _demo()
