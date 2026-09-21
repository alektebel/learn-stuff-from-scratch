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
    return line.split("#")[0].split(";")[0].strip()


def parse_line(text: str) -> Optional[Tuple[str, List[str]]]:
    """Return (mnemonic, raw operand strings), or None for a blank line."""
    text = _strip(text)
    if not text:
        return None
    parts = text.replace(",", " ").split()
    return parts[0].upper(), parts[1:]


def first_pass(source: str) -> Tuple[Dict[str, int], List[Tuple[int, str, List[str]]]]:
    """Find every label's address, and collect the instruction lines.

    Addresses are instruction indices, not byte offsets — every instruction is
    one word, so they are the same thing up to a factor of 4. Keeping them as
    indices removes a whole class of off-by-four bugs.
    """
    labels: Dict[str, int] = {}
    program: List[Tuple[int, str, List[str]]] = []
    address = 0

    for number, raw in enumerate(source.splitlines(), start=1):
        text = _strip(raw)
        if not text:
            continue
        match = _LABEL_DEF.match(text)
        if match:
            name = match.group(1)
            if name in labels:
                raise AssemblyError(f"line {number}: label {name!r} defined twice")
            labels[name] = address
            continue
        parsed = parse_line(text)
        if parsed is None:
            continue
        program.append((number, parsed[0], parsed[1]))
        address += 1

    return labels, program


def _resolve_operand(token: str, labels: Dict[str, int], line: int) -> int:
    """A register index, an integer, or a label address."""
    match = _REGISTER.match(token)
    if match:
        index = int(match.group(1))
        if not 0 <= index < NUM_REGISTERS:
            raise AssemblyError(f"line {line}: r{index} outside "
                                f"0..{NUM_REGISTERS - 1}")
        return index
    if token in labels:
        return labels[token]
    try:
        return int(token, 0)
    except ValueError:
        raise AssemblyError(f"line {line}: {token!r} is not a register, a "
                            f"number, or a known label") from None


def second_pass(labels: Dict[str, int],
                program: List[Tuple[int, str, List[str]]]) -> List[Instruction]:
    """Turn each line into an Instruction, resolving labels."""
    result: List[Instruction] = []
    for line, mnemonic, operands in program:
        op = BY_NAME.get(mnemonic)
        if op is None:
            raise AssemblyError(f"line {line}: unknown instruction {mnemonic!r}")
        if len(operands) != len(op.operands):
            raise AssemblyError(f"line {line}: {mnemonic} takes "
                                f"{len(op.operands)} operand(s), got "
                                f"{len(operands)}")

        fields = {"rd": 0, "rs1": 0, "rs2": 0, "imm": 0}
        slot = {"d": "rd", "a": "rs1", "b": "rs2", "i": "imm"}
        for kind, token in zip(op.operands, operands):
            fields[slot[kind]] = _resolve_operand(token, labels, line)
        result.append(Instruction(op=mnemonic, **fields))
    return result


def assemble(source: str) -> List[Instruction]:
    labels, program = first_pass(source)
    return second_pass(labels, program)


def assemble_to_words(source: str) -> List[int]:
    return [encode(instruction) for instruction in assemble(source)]


def disassemble(instructions: List[Instruction],
                labels: Optional[Dict[str, int]] = None) -> str:
    """Render a program back to text, with labels where they are known."""
    reverse = {address: name for name, address in (labels or {}).items()}
    lines = []
    for address, instruction in enumerate(instructions):
        if address in reverse:
            lines.append(f"{reverse[address]}:")
        lines.append(f"  {address:>3}  {instruction}")
    return "\n".join(lines)


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
    print("=== Source ===")
    print(SUM_TO_N.strip())

    labels, program = first_pass(SUM_TO_N)
    print(f"\n=== First pass: label addresses ===")
    for name, address in sorted(labels.items(), key=lambda kv: kv[1]):
        print(f"  {name:<8} -> instruction {address}")
    print(f"  ({len(program)} instructions)")
    print("\nThe forward reference to 'done' is why a single pass would not")
    print("work: at the JNZ we have not seen the label yet.")

    instructions = second_pass(labels, program)
    print("\n=== Second pass: resolved ===")
    print(disassemble(instructions, labels))

    print("\n=== Encoded ===")
    for address, word in enumerate(assemble_to_words(SUM_TO_N)):
        print(f"  {address:>3}  0x{word:08x}")

    print("\n=== Errors point at a line ===")
    for bad, why in [
        ("  ADD r1, r2\n", "wrong operand count"),
        ("  FROB r1, r2, r3\n", "unknown instruction"),
        ("  ADD r1, r2, r99\n", "register out of range"),
        ("  JMP nowhere\n", "undefined label"),
        ("a:\n a:\n  HALT\n", "duplicate label"),
    ]:
        try:
            assemble(bad)
            print(f"  {why:<24} NO ERROR — that is a bug")
        except AssemblyError as exc:
            print(f"  {why:<24} {exc}")


if __name__ == "__main__":
    _demo()
