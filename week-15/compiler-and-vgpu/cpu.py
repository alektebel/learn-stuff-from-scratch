"""
Step 3 — The scalar CPU. Complete Solution.

Fetch, decode, execute. One instruction at a time, one thread.

DESIGN DECISION — interpret decoded instructions, or decode every cycle?
  A real CPU decodes the 32-bit word each fetch. We could keep the decoded
  Instruction objects and skip that entirely.
  CHOSEN: decode every cycle, from the encoded words. It is slower and it is
  the point: the machine's input is MEMORY, not a Python list of objects. Doing
  it this way means self-modifying code, jumping into data, and a corrupted
  encoding all behave the way they really would.
"""

from typing import Dict, List, Optional

from isa import BY_NAME, NUM_REGISTERS, Instruction, decode, encode


class CPUError(Exception):
    pass


class CPU:
    """A scalar machine: 16 registers, a flat word-addressed memory, one PC."""

    def __init__(self, memory_words: int = 4096, trace: bool = False):
        self.registers: List[int] = [0] * NUM_REGISTERS
        self.memory: List[int] = [0] * memory_words
        self.pc: int = 0
        self.halted: bool = False
        self.cycles: int = 0
        self.trace = trace
        self.program: List[int] = []

    def load(self, words: List[int], data: Optional[Dict[int, int]] = None) -> None:
        """Load a program and optionally seed data memory.

        TODO: store the words, reset pc/halted/cycles/registers, then write any
        `data` entries into memory.

        DESIGN DECISION — one address space or two?
          Real machines mostly share one (von Neumann); GPUs and
          microcontrollers often separate them (Harvard).
          CHOSEN: separate. Instructions live in self.program, data in
          self.memory. It removes a class of confusing bugs where a store
          silently overwrites code — not the lesson here — and it matches the
          vGPU in step 6, where they really are separate.
        """
        raise NotImplementedError

    def step(self) -> Optional[Instruction]:
        """Execute one instruction. Return it, or None if already halted.

        TODO:
        1. Return None if halted. Raise CPUError if pc is outside the program —
           "pc 41 outside 0..12" is a real error message; an IndexError is not.
        2. decode(self.program[self.pc]).  Decode from the WORD, not from a
           stored Instruction: the machine's input is memory.
        3. next_pc = pc + 1, then a branch per opcode:
             LI/MOV/ADD/SUB/MUL/DIV/MOD/ADDI  arithmetic
             CMPLT/CMPGT/CMPEQ                write 1 or 0 into rd
             LD/ST                            address = reg[rs1] + imm
             JMP/JZ/JNZ                       assign next_pc
             HALT                             set self.halted
        4. Guard division and modulo by zero, and bounds-check every memory
           access through self._address.
        5. If the opcode is GPU-only, say so explicitly — a scalar CPU has no
           lanes to diverge. A generic "unknown instruction" would send you
           looking in the wrong place.
        6. Set self.pc = next_pc and increment self.cycles.
        """
        raise NotImplementedError

    def _address(self, address: int) -> int:
        """TODO: bounds-check and return the address, or raise CPUError."""
        raise NotImplementedError

    def run(self, max_cycles: int = 100_000) -> int:
        """TODO: step until halted; return the cycle count.

        Raise CPUError if max_cycles is exceeded. This is not decoration: the
        first bug most people hit is an inverted loop condition, and without the
        cap the machine hangs instead of telling you where it is stuck.
        """
        raise NotImplementedError

    def dump(self, registers: int = 8, memory: int = 0) -> str:
        """TODO: a one-line register (and optional memory) dump for debugging."""
        raise NotImplementedError


def _demo() -> None:
    """Once implemented, verify:

    1. SUM_TO_N with n=5 leaves 15 in r2. Trace it and watch the loop.
    2. Cycles grow linearly with n — 5 instructions per iteration, which you
       can read straight off the source.
    3. A load/store program doubles [3, 7, 11, 13] into memory at 100.
    4. Every error is reported, not guessed at: out-of-range address, division
       by zero, an infinite loop hitting the cycle cap, and a GPU instruction
       on the CPU.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
