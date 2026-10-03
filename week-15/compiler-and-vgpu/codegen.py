"""
Step 5 — Code generation. Complete Solution.

AST -> assembly. This is where the MVP-then-complicate ladder is steepest, so
it is built in four visible stages:

  v1  expressions, unlimited virtual registers      -> works, ignores hardware
  v2  control flow                                  -> labels and jumps
  v3  only 16 real registers exist                  -> allocation, then spilling
  v4  lanes disagree about which branch to take     -> GPU divergence

Each stage is forced by a concrete failure of the one before. That is the
point: told up front that a compiler needs a register allocator you memorise
it; having written code that runs out of registers, you could have invented one.

DESIGN DECISION — generate to virtual registers first, or straight to r0..r15?
  Emitting real registers directly means allocation decisions are tangled into
  every visit_ method, and running out means restructuring code generation.
  CHOSEN: emit to an unlimited supply of virtual registers, then allocate as a
  separate pass. Every real compiler does this, for exactly this reason — the
  two problems are independent and get much harder when mixed.
"""

from typing import Dict, List, Optional, Set, Tuple

from frontend import (Assign, Binary, If, Load, Num, Store, Stmt, Tid, Var,
                      While, parse)
from isa import NUM_REGISTERS

# Registers reserved by convention, never handed to the allocator.
SCRATCH = 14          # used to materialise spilled values
SCRATCH2 = 15
ALLOCATABLE = list(range(SCRATCH))     # r0..r13

SPILL_BASE = 3000     # spill slots live high in data memory


class CodegenError(Exception):
    pass


class Codegen:
    """Walks the AST emitting assembly lines.

    `gpu` selects the divergence strategy for `if` and `while`:
      False — plain jumps, correct for one thread of control
      True  — DIVERGE/ELSE/CONVERGE and LOOPTEST, so a warp whose lanes
              disagree still computes the right answer for each lane
    """

    def __init__(self, gpu: bool = False):
        self.gpu = gpu
        self.lines: List[str] = []
        self.next_virtual = 0
        self.next_label = 0
        self.variables: Dict[str, int] = {}
        self.spills = 0

    # -- v1: expressions ----------------------------------------------------

    def fresh(self) -> int:
        """TODO: hand out a new virtual register number. Unlimited, on purpose —
        allocation is a separate pass."""
        raise NotImplementedError

    def label(self, stem: str) -> str:
        """TODO: a unique label like 'loop3'. Uniqueness matters the moment you
        nest two loops."""
        raise NotImplementedError

    def emit(self, text: str) -> None:
        raise NotImplementedError

    def emit_label(self, name: str) -> None:
        raise NotImplementedError

    def variable(self, name: str) -> int:
        """TODO: the virtual register for a named variable, creating and
        zero-initialising it on first use."""
        raise NotImplementedError

    BINARY_OPS = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD",
                  "<": "CMPLT", ">": "CMPGT", "==": "CMPEQ"}

    def expr(self, node) -> int:
        """Emit code for an expression; return the virtual register holding it.

        TODO:
          Num    -> fresh register, LI it
          Var    -> self.variable(name)
          Tid    -> TID on the GPU; LI 0 on the CPU (a scalar CPU is thread 0)
          Load   -> evaluate the address, then LD
          Binary -> evaluate both sides, then the matching opcode

        For <=, >= and != there is no opcode. Rather than adding three, derive
        them: a <= b is NOT (a > b), so emit the base comparison and compare its
        result against 0 with CMPEQ. Fewer opcodes means less to decode, in the
        assembler and in the hardware.
        """
        raise NotImplementedError

    # -- v2 and v4: statements and control flow -----------------------------

    def stmt(self, node) -> None:
        """TODO:
          Assign -> evaluate, MOV into the variable's register
          Store  -> evaluate address and value, ST

          If, CPU (v2): one thread of control, so a plain branch is enough.
              JZ cond, else_label / then body / JMP join / else_label: / else
              body / join_label:

          If, GPU (v4): lanes may disagree, and a warp has ONE program counter.
              DIVERGE cond, else_label     push the mask, keep lanes with cond
              ...then body...
              else_label: ELSE join_label  flip to the other lanes
              ...else body...
              join_label: CONVERGE         pop the mask
              Both arms execute. That is the cost of the model, and step 6
              measures it.

          While, CPU: label, evaluate condition, JZ out, body, JMP back.
          While, GPU: same shape but LOOPTEST instead of JZ, and a CONVERGE at
              the exit. Lanes drop out as their conditions fail while the warp
              keeps iterating for whoever is left.
        """
        raise NotImplementedError

    def generate(self, program: List[Stmt]) -> str:
        """TODO: emit every statement, then HALT, and join the lines."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# v3: register allocation
# ---------------------------------------------------------------------------

def live_intervals(lines: List[str]) -> Dict[int, Tuple[int, int]]:
    """First and last line on which each virtual register appears.

    TODO: scan the lines for vN tokens; record (first index, last index).

    DESIGN DECISION — linear scan or graph colouring?
      Graph colouring builds an interference graph and colours it: better
      allocations, much more work.
      CHOSEN: linear scan over live intervals. A few dozen lines, what JITs use
      when compile time matters, and it makes the SHAPE of the problem visible —
      intervals that overlap need different registers.
      Approximating liveness by first-to-last mention is coarse (a value dead in
      the middle still holds its register) but never WRONG, only wasteful.
    """
    raise NotImplementedError


def allocate_registers(assembly: str) -> Tuple[str, int]:
    """Map virtual registers onto r0..r13, spilling when they run out.

    Returns (assembly, number of spills).

    TODO:
    1. live_intervals, then sort by START point — the "linear scan".
    2. Walk them keeping an `active` list and a `free` pool:
         - retire actives whose interval ended before this one began, returning
           their registers to the pool
         - if a register is free, take it
         - otherwise SPILL: pick the active interval that ends LATEST (least
           likely to be needed soon). If it outlives the new one, steal its
           register and spill it; otherwise spill the new one.
    3. Rewrite the assembly. A spilled value needs a LI of its slot address and
       an LD before a read, or an ST after a write, using SCRATCH/SCRATCH2.
       Careful: the first operand is a DESTINATION for most opcodes but a
       SOURCE for ST, STS, JZ, JNZ, DIVERGE and LOOPTEST.

    The limit case this exists for: more simultaneously-live values than the
    machine has registers. With 14 allocatable you have to nest a fair way to
    hit it — which is exactly why the MVP feels fine right up until it does not.
    """
    raise NotImplementedError


def compile_source(source: str, gpu: bool = False,
                   allocate: bool = True) -> Tuple[str, int]:
    """TODO: parse -> Codegen(gpu).generate -> optionally allocate_registers."""
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, verify in order:

    1. v1: `x = 1 + 2 * 3;` without allocation uses one virtual register per
       value. Simple, and unrunnable — the machine has 16.
    2. v3: the same code allocated onto r0..r13, and it RUNS.
    3. A real program (while + if + memory) computes the right answer on the
       CPU from step 3.
    4. The limit case. Generate RIGHT-nested expressions —
       1 + (2 + (3 + ...)) — so each left operand stays live across the whole
       rest. Left-nested ones do not work: their temporaries die immediately and
       linear scan reuses one register forever. What is live at once is a
       property of the expression's SHAPE, not its size.
       Expect spills to appear around depth 14 and grow (0, 1, 5, 11 at depths
       10, 14, 18, 24) while every result stays CORRECT. Slower, still right —
       that is what an allocator buys you.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
