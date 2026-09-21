"""
Step 2 — The assembler. Complete Solution.

Text with labels -> encoded words.

DESIGN DECISION — two passes, or one pass with backpatching?
  A forward reference ("jump to a label defined later") cannot be resolved when
  you first meet it. Two ways out:
    two-pass       — walk once to find every label's address, walk again to emit
    backpatching   — emit a placeholder, remember where, fill it in at the end
  CHOSEN: two-pass. It is simpler to get right and easy to read, and the cost
  (walking the source twice) is irrelevant at this scale. Backpatching wins when
  input is streamed and cannot be re-read — a real constraint for a linker,
  not for us.
"""

import re
from typing import Dict, List, Optional, Tuple

from isa import BY_NAME, NUM_REGISTERS, Instruction, encode


class AssemblyError(Exception):
    """Raised with a line number, because an assembler that says only 'syntax
    error' is a tool you will grow to hate."""


_REGISTER = re.compile(r"^r(\d+)$", re.IGNORECASE)
_LABEL_DEF = re.compile(r"^([A-Za-z_.][A-Za-z0-9_.]*):$")


def _strip(line: str) -> str:
    """TODO: drop anything after '#' or ';', then strip whitespace."""
    raise NotImplementedError


def parse_line(text: str) -> Optional[Tuple[str, List[str]]]:
    """TODO: strip comments; return None for a blank line; otherwise split into
    (UPPERCASE mnemonic, operand strings). Treat commas as whitespace so
    "ADD r1, r2, r3" and "ADD r1 r2 r3" both work."""
    raise NotImplementedError


def first_pass(source: str) -> Tuple[Dict[str, int], List[Tuple[int, str, List[str]]]]:
    """Find every label's address; collect the instruction lines.

    TODO:
    1. Walk the source with line numbers (1-based — error messages need them).
    2. A line matching _LABEL_DEF records labels[name] = current address and
       does NOT advance the address; a label is a position, not an instruction.
       Raise AssemblyError on a duplicate.
    3. Any other non-blank line is appended as (line_number, mnemonic, operands)
       and advances the address by one.

    Addresses are INSTRUCTION INDICES, not byte offsets. Every instruction is
    one word, so they differ only by a factor of 4 — and keeping them as indices
    removes a whole class of off-by-four bugs.
    """
    raise NotImplementedError


def _resolve_operand(token: str, labels: Dict[str, int], line: int) -> int:
    """TODO: a register (rN, validated against NUM_REGISTERS), a known label,
    or an integer (int(token, 0) so 0x20 works). Raise AssemblyError naming the
    line and the token otherwise."""
    raise NotImplementedError


def second_pass(labels: Dict[str, int],
                program: List[Tuple[int, str, List[str]]]) -> List[Instruction]:
    """TODO: for each line, look up the Op, check the operand COUNT against
    op.operands, then map each operand into the right Instruction field using
    the operand spec ('d'->rd, 'a'->rs1, 'b'->rs2, 'i'->imm).

    Checking the count matters: "ADD r1, r2" would otherwise silently assemble
    with rs2=0 and compute the wrong thing at runtime, which is far harder to
    find than an assembler error."""
    raise NotImplementedError


def assemble(source: str) -> List[Instruction]:
    """TODO: first_pass then second_pass."""
    raise NotImplementedError


def assemble_to_words(source: str) -> List[int]:
    """TODO: assemble, then encode each instruction."""
    raise NotImplementedError


def disassemble(instructions: List[Instruction],
                labels: Optional[Dict[str, int]] = None) -> str:
    """TODO: render each instruction with its address, printing a label line
    wherever one points. Worth writing — you will read this output constantly
    while debugging codegen."""
    raise NotImplementedError


SUM_TO_N = """
# sum = 0; i = 1; while (i <= n) { sum += i; i += 1 }
# n in r1, result left in r2
        LI   r2, 0          # sum
        LI   r3, 1          # i
loop:
        CMPGT r4, r3, r1    # r4 = (i > n)
        JNZ  r4, done
        ADD  r2, r2, r3
        ADDI r3, r3, 1
        JMP  loop
done:
        HALT
"""


def _demo() -> None:
    """Once implemented, verify:

    1. first_pass on SUM_TO_N finds loop=2 and done=7, with 8 instructions.
       The forward reference to 'done' is exactly why one pass cannot work.
    2. second_pass resolves JNZ r4, done -> JNZ r4, 7.
    3. Every error case names its line: wrong operand count, unknown
       instruction, register out of range, undefined label, duplicate label.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
