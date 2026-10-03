"""
Step 7 — Capstone: one program, two machines. Complete Solution.

The payoff. The same source compiles for a scalar CPU and for a SIMT GPU, and
the two produce IDENTICAL results by construction — which is the property that
makes the comparison meaningful at all.

What the numbers show:
  - where SIMT wins (uniform work over many elements)
  - where it does not (divergent control flow, serial dependencies)
  - that the win is instruction ISSUES, not instructions executed
"""

from typing import Dict, List, Tuple

from assembler import assemble_to_words
from codegen import compile_source
from vgpu import WARP_SIZE, VirtualGPU


def run_on_gpu(source: str, data: Dict[int, int],
               threads: int = WARP_SIZE) -> Tuple[List[int], VirtualGPU]:
    """TODO: compile with gpu=True, run on a VirtualGPU, return
    (memory[:threads], the gpu) so the caller can read its counters."""
    raise NotImplementedError


def compare(name: str, source: str, data: Dict[int, int],
            threads: int = WARP_SIZE) -> None:
    """Run a kernel both ways and report the cost of each.

    TODO:
    1. Run it on a full warp; record instructions_issued and efficiency.
    2. Build the SERIAL baseline by running the same compiled words on a
       one-lane VirtualGPU, once per thread, summing the issues.

       Using a one-lane warp rather than the scalar CPU is deliberate: it runs
       the SAME instructions, so any difference in the numbers is the execution
       model and not the compiler. Comparing against the CPU build would confound
       the two.
    3. Print output, warp issues, serial issues, speedup and efficiency.
    """
    raise NotImplementedError


def _demo() -> None:
    """The payoff. Once implemented, produce:

    1. The same source compiled both ways, printed side by side. Same front
       end, same registers, same arithmetic — the ONLY difference is how
       control flow is expressed: JZ/JMP for one thread, DIVERGE/ELSE/CONVERGE
       for a warp whose lanes may disagree.

    2. Three kernels, and their numbers:

         uniform    (mem[tid] = mem[tid] + mem[tid])   ~8.00x, 100% efficiency
         divergent  (if (tid < 4) ...)                 ~6.86x,  75%
         ragged     (while (i < tid) ...)              ~1.37x,  57%

       Predict each before you run it.

    3. Explain the third to yourself. Lane 0 loops zero times and lane 7 loops
       seven, so the warp keeps issuing until the slowest lane finishes while
       the finished lanes sit masked off. A warp runs at the speed of its
       SLOWEST lane — the SIMT straggler problem, and the reason irregular
       workloads (graph traversal, sparse data, ragged batches) are hard on
       GPUs.

    The general lesson, which outlives this toy: a GPU's advantage is amortising
    INSTRUCTION ISSUE across lanes. Anything that makes lanes disagree spends
    that advantage. Divergence is not a bug to be fixed in hardware — it is the
    price of the design decision at the top of vgpu.py.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
