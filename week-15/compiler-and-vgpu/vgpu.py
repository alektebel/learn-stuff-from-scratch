"""
Step 6 — The virtual GPU. Complete Solution.

The same instruction set as the CPU, executed by a WARP: a group of lanes that
share one program counter and step in lockstep.

DESIGN DECISION — one PC per lane, or one PC per warp?
  Per-lane PCs make divergence trivial (each lane just goes where it likes) and
  throw away the entire reason GPUs are fast: one instruction fetch and decode
  amortised across many lanes.
  CHOSEN: one PC per warp, with an active-lane MASK. This is what real hardware
  does, and it means divergence is not free — it is the central cost of the
  model, and the thing this file exists to make visible.

DESIGN DECISION — how is divergence handled?
  Three real options:
    predication      — execute both sides, discard results for inactive lanes.
                       Cheap for short bodies, wasteful for long ones.
    reconvergence PC — hardware detects the join point automatically.
                       No compiler support; complex hardware.
    mask stack       — the compiler marks where control flow splits and joins,
                       hardware pushes and pops masks.
  CHOSEN: mask stack with compiler-emitted DIVERGE / ELSE / CONVERGE. It makes
  the mechanism explicit in the instruction stream, which is what we want to
  study, and it is close to what early NVIDIA hardware actually did.

The consequence you must see for yourself: a warp with divergent lanes executes
BOTH arms of an if/else, one after the other, with different masks. Work goes
up; parallelism does not.
"""

from typing import Dict, List, NamedTuple, Optional, Tuple

from isa import NUM_REGISTERS, Instruction, decode

WARP_SIZE = 8            # small enough to print a mask as 8 characters


class GPUError(Exception):
    pass


class MaskEntry(NamedTuple):
    kind: str            # "if" or "loop"
    outer_mask: int      # the mask to restore on CONVERGE
    pending_mask: int    # lanes waiting to run the ELSE arm
    join_pc: int


class VirtualGPU:
    """One warp of WARP_SIZE lanes sharing a program counter.

    Per-lane state: registers.
    Shared state:   global memory, shared memory, the PC, the active mask.
    """

    def __init__(self, memory_words: int = 4096, shared_words: int = 256,
                 warp_size: int = WARP_SIZE, trace: bool = False):
        self.warp_size = warp_size
        self.registers: List[List[int]] = [[0] * NUM_REGISTERS
                                           for _ in range(warp_size)]
        self.memory: List[int] = [0] * memory_words
        self.shared: List[int] = [0] * shared_words
        self.pc = 0
        self.active = (1 << warp_size) - 1
        self.stack: List[MaskEntry] = []
        self.halted = False
        self.trace = trace
        self.program: List[int] = []

        # Cost model: what we came here to measure.
        self.instructions_issued = 0      # warp-level fetches
        self.lane_instructions = 0        # useful per-lane work
        self.divergent_issues = 0         # issues with some lanes masked off

    def lanes(self) -> List[int]:
        """TODO: the indices of currently-active lanes, from self.active."""
        raise NotImplementedError

    def mask_string(self, mask: Optional[int] = None) -> str:
        """TODO: render a mask as '1' and '.', e.g. '1111....'. Write this
        early — a traced run with masks is how you will debug divergence."""
        raise NotImplementedError

    def load(self, words: List[int], data: Optional[Dict[int, int]] = None) -> None:
        """TODO: store the program; reset pc, mask (all lanes on), stack,
        registers and all three counters; seed memory from `data`."""
        raise NotImplementedError

    def step(self) -> Optional[Instruction]:
        """Execute one instruction across the warp.

        TODO, in this order:

        1. Decode. Then, BEFORE anything else, update the cost model:
             instructions_issued += 1
             lane_instructions   += len(active lanes)
             divergent_issues    += 1 if fewer than warp_size lanes are active
           These three counters are the entire point of the file.

        2. Mask-manipulating control flow:
           DIVERGE rs1, else_pc
             taken = active lanes whose reg[rs1] != 0
             push MaskEntry("if", outer=active, pending=active & ~taken, else_pc)
             active = taken; if that is empty, jump straight to else_pc
           ELSE join_pc
             active = the pushed pending mask; clear pending; record join_pc;
             if empty, jump to join_pc
           CONVERGE
             active = the popped entry's outer mask
           LOOPTEST rs1, exit_pc
             push a "loop" entry on first arrival; deactivate lanes whose
             condition is false; if none remain, jump to exit_pc
           Raise GPUError on ELSE/CONVERGE with an empty stack — an unbalanced
           mask stack silently corrupts every later branch.

        3. BAR — the limit case worth building deliberately. If the mask stack
           is non-empty, the warp is inside divergent control flow and the
           masked-off lanes can NEVER arrive. Real hardware deadlocks or is
           undefined here. Raise GPUError explaining that, rather than hanging:
           "it hung" is a terrible error message, and this is exactly why CUDA
           requires __syncthreads() to be reached by every thread.

        4. JMP/JZ/JNZ — uniform branches. If lanes DISAGREE about a JZ or JNZ
           condition, raise GPUError: a plain branch cannot express that, and
           the compiler should have emitted DIVERGE. Silently taking the
           majority would give wrong answers for some lanes.

        5. Everything else is per-lane: loop over the ACTIVE lanes only and
           apply the operation to that lane's registers. TID gives the lane its
           index; LD/ST hit global memory, LDS/STS hit shared.
        """
        raise NotImplementedError

    def _address(self, address: int, space: List[int]) -> int:
        """TODO: bounds-check against the given space, or raise GPUError."""
        raise NotImplementedError

    def run(self, max_issues: int = 100_000) -> int:
        """TODO: step until halted, with an issue cap for the same reason the
        CPU has a cycle cap."""
        raise NotImplementedError

    def efficiency(self) -> float:
        """Fraction of lane-slots that did useful work.

        TODO: lane_instructions / (instructions_issued * warp_size).

        1.0 means every lane was active on every issue. 0.5 means you paid for a
        warp and used half of it. This is the number that makes divergence
        concrete — a real profiler calls it warp execution efficiency.
        """
        raise NotImplementedError


def _demo() -> None:
    """Once implemented, verify:

    1. Uniform kernel (`mem[tid] = tid * 2;`): efficiency 100%, nothing
       diverges, every issue does 8 lanes of work.
    2. Divergent kernel (`if (tid < 4)`): TRACE it. You should see the then-arm
       executed with mask 1111...., then the else-arm with ....1111. Both arms
       run. Efficiency ~75%.
    3. A table of conditions: all-lanes-same (~92% — it still issues the
       DIVERGE and an empty ELSE, but skips the dead arm's body), half-and-half
       (75%), one-lane-differs (78%), alternating (78%).
    4. The limit case: hand-write a kernel with BAR inside a DIVERGE and
       confirm your machine reports the deadlock instead of hanging.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
