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
    """Pack an instruction into one 32-bit word."""
    op = BY_NAME.get(instruction.op)
    if op is None:
        raise ValueError(f"unknown opcode {instruction.op!r}")
    for name, value in (("rd", instruction.rd), ("rs1", instruction.rs1),
                        ("rs2", instruction.rs2)):
        if not 0 <= value < NUM_REGISTERS:
            raise ValueError(f"{instruction.op}: {name}={value} outside "
                             f"0..{NUM_REGISTERS - 1}")
    if not IMM_MIN <= instruction.imm <= IMM_MAX:
        raise ValueError(f"{instruction.op}: immediate {instruction.imm} does not "
                         f"fit in {IMM_BITS} bits ({IMM_MIN}..{IMM_MAX})")

    return ((op.code << OPCODE_SHIFT)
            | (instruction.rd << RD_SHIFT)
            | (instruction.rs1 << RS1_SHIFT)
            | (instruction.rs2 << RS2_SHIFT)
            | (instruction.imm & ((1 << IMM_BITS) - 1)))


def decode(word: int) -> Instruction:
    """Unpack a 32-bit word. The immediate is sign-extended."""
    code = (word >> OPCODE_SHIFT) & ((1 << OPCODE_BITS) - 1)
    op = BY_CODE.get(code)
    if op is None:
        raise ValueError(f"unknown opcode {code} in word 0x{word:08x}")

    imm = word & ((1 << IMM_BITS) - 1)
    if imm >= (1 << (IMM_BITS - 1)):        # sign-extend
        imm -= (1 << IMM_BITS)

    return Instruction(
        op=op.name,
        rd=(word >> RD_SHIFT) & ((1 << REG_BITS) - 1),
        rs1=(word >> RS1_SHIFT) & ((1 << REG_BITS) - 1),
        rs2=(word >> RS2_SHIFT) & ((1 << REG_BITS) - 1),
        imm=imm,
    )


def _demo() -> None:
    print("=== The instruction set ===")
    print(f"{'code':>5}  {'name':<9}{'operands':<10}where")
    for op in _OP_LIST:
        where = "GPU only" if op.gpu_only else "CPU + GPU"
        print(f"{op.code:>5}  {op.name:<9}{op.operands or '-':<10}{where}")

    print(f"\n{NUM_REGISTERS} registers, {WORD_BITS}-bit fixed-width words.")
    print("Layout: [opcode:6][rd:4][rs1:4][rs2:4][imm:14]")

    print("\n=== Encoding round-trip ===")
    samples = [
        Instruction("ADD", rd=3, rs1=1, rs2=2),
        Instruction("LI", rd=5, imm=1234),
        Instruction("LI", rd=5, imm=-1234),
        Instruction("LD", rd=7, rs1=2, imm=-8),
        Instruction("JZ", rs1=4, imm=100),
        Instruction("HALT"),
    ]
    for instruction in samples:
        word = encode(instruction)
        back = decode(word)
        ok = back == instruction
        print(f"  {str(instruction):<24} 0x{word:08x}  round-trip: "
              f"{'OK' if ok else 'FAILED ' + str(back)}")

    print("\n=== The limits the encoding imposes ===")
    print(f"immediate range: {IMM_MIN} .. {IMM_MAX}")
    for bad, why in [(Instruction("LI", rd=5, imm=99999), "immediate too large"),
                     (Instruction("ADD", rd=99, rs1=1, rs2=2), "register out of range")]:
        try:
            encode(bad)
            print(f"  {why}: NO ERROR — that is a bug")
        except ValueError as exc:
            print(f"  {why}: rejected — {exc}")
    print("\nA real assembler would materialise an out-of-range constant with a")
    print("two-instruction sequence (load high, or into a scratch register).")
    print("Ours refuses, loudly. Refusing is fine; corrupting the encoding")
    print("silently is not — and silent truncation is what you get if you")
    print("forget to mask the immediate before packing it.")


if __name__ == "__main__":
    _demo()
