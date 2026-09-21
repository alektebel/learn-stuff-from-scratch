"""
Step 1 — The instruction set. Complete Solution.

DESIGN DECISION — register machine or stack machine?
  A stack machine needs no register allocation at all: every operation pops its
  operands and pushes its result. Code generation is almost trivial.
  A register machine is what real hardware is, and it forces you to confront
  allocation and spilling.
  CHOSEN: register machine, precisely BECAUSE it creates the harder problem.
  Spilling is the interesting part of step 5, and a stack machine would have
  hidden it.

DESIGN DECISION — fixed-width or variable-width encoding?
  Variable-width (x86) packs common instructions into fewer bytes. Fixed-width
  (ARM, RISC-V, every GPU) makes decode trivial and lets you fetch instruction
  N without having decoded N-1.
  CHOSEN: fixed 32-bit. Decoding is a few shifts, and — the reason that matters
  here — a SIMT machine must fetch ONE instruction for a whole warp. Variable
  width would make that a mess.

DESIGN DECISION — how many registers?
  32 would make the toy programs fit without ever spilling. 4 would make
  spilling so constant it stops being instructive.
  CHOSEN: 16. Enough for straight-line code to be comfortable, few enough that
  a nested expression runs out — which is exactly the limit case that motivates
  the register allocator.
"""

from typing import Dict, List, NamedTuple, Optional, Tuple

NUM_REGISTERS = 16
WORD_BITS = 32

# Encoding layout: [opcode:6][rd:4][rs1:4][rs2:4][imm:14]
OPCODE_SHIFT, OPCODE_BITS = 26, 6
RD_SHIFT, RS1_SHIFT, RS2_SHIFT = 22, 18, 14
REG_BITS = 4
IMM_BITS = 14
IMM_MIN, IMM_MAX = -(1 << (IMM_BITS - 1)), (1 << (IMM_BITS - 1)) - 1


class Op(NamedTuple):
    code: int
    name: str
    operands: str          # combination of 'd' (rd), 'a' (rs1), 'b' (rs2), 'i'
    gpu_only: bool = False


_OP_LIST = [
    # core
    Op(0, "NOP", ""),
    Op(1, "HALT", ""),
    Op(2, "LI", "di"),           # rd = imm
    Op(3, "MOV", "da"),          # rd = rs1
    # arithmetic
    Op(4, "ADD", "dab"),
    Op(5, "SUB", "dab"),
    Op(6, "MUL", "dab"),
    Op(7, "DIV", "dab"),
    Op(8, "MOD", "dab"),
    Op(9, "ADDI", "dai"),        # rd = rs1 + imm
    # comparison — result is 1 or 0 in a general register
    Op(10, "CMPLT", "dab"),
    Op(11, "CMPGT", "dab"),
    Op(12, "CMPEQ", "dab"),
    # memory
    Op(13, "LD", "dai"),         # rd = mem[rs1 + imm]
    Op(14, "ST", "abi"),         # mem[rs1 + imm] = rs2   (note: no rd)
    # control flow
    Op(15, "JMP", "i"),
    Op(16, "JZ", "ai"),          # if rs1 == 0 -> pc = imm
    Op(17, "JNZ", "ai"),
    # ---- GPU-only ----
    Op(18, "TID", "d", gpu_only=True),        # rd = this lane's id
    Op(19, "DIVERGE", "ai", gpu_only=True),   # push mask; disable lanes where rs1==0;
                                              # imm = pc of the ELSE arm
    Op(20, "ELSE", "i", gpu_only=True),       # invert the mask within the pushed set;
                                              # imm = pc of the join
    Op(21, "CONVERGE", "", gpu_only=True),    # pop the mask
    Op(22, "LOOPTEST", "ai", gpu_only=True),  # disable lanes where rs1==0; if none
                                              # remain active, jump to imm
    Op(23, "BAR", "", gpu_only=True),         # barrier across the warp
    Op(24, "LDS", "dai", gpu_only=True),      # shared-memory load
    Op(25, "STS", "abi", gpu_only=True),      # shared-memory store
]

BY_NAME: Dict[str, Op] = {op.name: op for op in _OP_LIST}
BY_CODE: Dict[int, Op] = {op.code: op for op in _OP_LIST}


class Instruction(NamedTuple):
    """A decoded instruction. Registers default to 0, immediate to 0."""
    op: str
    rd: int = 0
    rs1: int = 0
    rs2: int = 0
    imm: int = 0

    def __repr__(self) -> str:
        spec = BY_NAME[self.op].operands
        parts = []
        for kind in spec:
            parts.append({"d": f"r{self.rd}", "a": f"r{self.rs1}",
                          "b": f"r{self.rs2}", "i": str(self.imm)}[kind])
        return f"{self.op}" + (" " + ", ".join(parts) if parts else "")


def encode(instruction: Instruction) -> int:
    """Pack an instruction into one 32-bit word.

    TODO:
    1. Look up the opcode by name; raise ValueError if unknown.
    2. Validate rd, rs1, rs2 are within 0..NUM_REGISTERS-1, and that imm fits
       in IMM_BITS as a SIGNED value. Raise ValueError with a useful message.
    3. Shift each field into place and OR them together. Mask the immediate
       with ((1 << IMM_BITS) - 1) so a negative value does not corrupt the
       fields above it.

    Step 3's mask is the one people forget. Without it, encode(LI r5, -1)
    sets every bit in the word and silently changes the opcode.
    """
    raise NotImplementedError


def decode(word: int) -> Instruction:
    """Unpack a 32-bit word.

    TODO:
    1. Extract the opcode; raise ValueError if it is not a known instruction.
    2. Extract rd, rs1, rs2 with shifts and masks.
    3. Extract the immediate, then SIGN-EXTEND it: if it is >= 1 << (IMM_BITS-1),
       subtract 1 << IMM_BITS.

    Without step 3, every negative offset reads back as a large positive one
    and your jumps land in the wrong place. Test it: encode/decode LI r5, -1234
    must round-trip.
    """
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, verify:

    1. Print the opcode table and the encoding layout.
    2. Round-trip every sample instruction: encode then decode must give back
       exactly what you started with, INCLUDING negative immediates.
    3. Out-of-range immediates and registers are rejected with a clear message
       rather than silently truncated.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
