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
        """Load a program, and optionally seed data memory.

        DESIGN DECISION — one address space or two?
          Real machines mostly share one (von Neumann); GPUs and microcontrollers
          often separate them (Harvard).
          CHOSEN: separate. Instructions live in self.program, data in
          self.memory. It removes a whole class of confusing bugs where a store
          silently overwrites the code, which is not the lesson here — and it
          matches the vGPU in step 6, where they really are separate.
        """
        self.program = list(words)
        self.pc = 0
        self.halted = False
        self.cycles = 0
        self.registers = [0] * NUM_REGISTERS
        for address, value in (data or {}).items():
            self.memory[address] = value

    # -- execution ----------------------------------------------------------

    def step(self) -> Optional[Instruction]:
        """Execute one instruction. Returns it, or None if halted."""
        if self.halted:
            return None
        if not 0 <= self.pc < len(self.program):
            raise CPUError(f"pc {self.pc} outside the program "
                           f"(0..{len(self.program) - 1})")

        instruction = decode(self.program[self.pc])
        if self.trace:
            print(f"  {self.pc:>3}  {instruction}")

        next_pc = self.pc + 1
        op, rd, a, b, imm = (instruction.op, instruction.rd, instruction.rs1,
                             instruction.rs2, instruction.imm)
        reg = self.registers

        if op == "NOP":
            pass
        elif op == "HALT":
            self.halted = True
        elif op == "LI":
            reg[rd] = imm
        elif op == "MOV":
            reg[rd] = reg[a]
        elif op == "ADD":
            reg[rd] = reg[a] + reg[b]
        elif op == "SUB":
            reg[rd] = reg[a] - reg[b]
        elif op == "MUL":
            reg[rd] = reg[a] * reg[b]
        elif op == "DIV":
            if reg[b] == 0:
                raise CPUError(f"pc {self.pc}: division by zero")
            reg[rd] = int(reg[a] / reg[b]) if reg[a] * reg[b] < 0 else reg[a] // reg[b]
        elif op == "MOD":
            if reg[b] == 0:
                raise CPUError(f"pc {self.pc}: modulo by zero")
            reg[rd] = reg[a] - reg[b] * (reg[a] // reg[b])
        elif op == "ADDI":
            reg[rd] = reg[a] + imm
        elif op == "CMPLT":
            reg[rd] = 1 if reg[a] < reg[b] else 0
        elif op == "CMPGT":
            reg[rd] = 1 if reg[a] > reg[b] else 0
        elif op == "CMPEQ":
            reg[rd] = 1 if reg[a] == reg[b] else 0
        elif op == "LD":
            reg[rd] = self.memory[self._address(reg[a] + imm)]
        elif op == "ST":
            self.memory[self._address(reg[a] + imm)] = reg[b]
        elif op == "JMP":
            next_pc = imm
        elif op == "JZ":
            if reg[a] == 0:
                next_pc = imm
        elif op == "JNZ":
            if reg[a] != 0:
                next_pc = imm
        elif BY_NAME[op].gpu_only:
            raise CPUError(f"pc {self.pc}: {op} is a GPU instruction — a scalar "
                           f"CPU has no lanes to diverge or synchronise")
        else:
            raise CPUError(f"pc {self.pc}: unimplemented instruction {op}")

        self.pc = next_pc
        self.cycles += 1
        return instruction

    def _address(self, address: int) -> int:
        if not 0 <= address < len(self.memory):
            raise CPUError(f"pc {self.pc}: memory address {address} outside "
                           f"0..{len(self.memory) - 1}")
        return address

    def run(self, max_cycles: int = 100_000) -> int:
        """Run to HALT. Returns the cycle count.

        The cycle cap is not decoration: the very first bug most people hit is
        a loop whose exit condition is inverted, and without a cap the machine
        hangs instead of telling you.
        """
        while not self.halted:
            if self.cycles >= max_cycles:
                raise CPUError(f"still running after {max_cycles} cycles — "
                               "infinite loop? (pc is currently "
                               f"{self.pc})")
            self.step()
        return self.cycles

    def dump(self, registers: int = 8, memory: int = 0) -> str:
        parts = ["  " + " ".join(f"r{i}={self.registers[i]}"
                                 for i in range(registers))]
        if memory:
            parts.append("  mem " + " ".join(str(v) for v in self.memory[:memory]))
        return "\n".join(parts)


def _demo() -> None:
    from assembler import SUM_TO_N, assemble_to_words

    print("=== sum 1..n, traced ===")
    cpu = CPU(trace=True)
    cpu.load(assemble_to_words(SUM_TO_N))
    cpu.registers[1] = 5                      # n = 5
    cpu.run()
    print(f"\nsum(1..5) = {cpu.registers[2]}  (expected 15)")
    print(f"cycles: {cpu.cycles}")

    print("\n=== Cycle count grows with n ===")
    print(f"{'n':>5}{'result':>9}{'cycles':>9}")
    for n in (1, 5, 10, 50, 100):
        cpu = CPU()
        cpu.load(assemble_to_words(SUM_TO_N))
        cpu.registers[1] = n
        cpu.run()
        print(f"{n:>5}{cpu.registers[2]:>9}{cpu.cycles:>9}")
    print("Five instructions per iteration, as you would expect from the source.")

    print("\n=== Memory ===")
    from assembler import assemble_to_words as build
    doubler = build("""
            LI   r1, 0          # index
            LI   r5, 4          # count
    loop:
            CMPLT r6, r1, r5
            JZ   r6, done
            LD   r2, r1, 0      # x = in[i]
            ADD  r2, r2, r2     # x = x + x
            ST   r1, r2, 100    # out[i] = x
            ADDI r1, r1, 1
            JMP  loop
    done:
            HALT
    """)
    cpu = CPU()
    cpu.load(doubler, data={0: 3, 1: 7, 2: 11, 3: 13})
    cpu.run()
    print(f"  in  {cpu.memory[0:4]}")
    print(f"  out {cpu.memory[100:104]}   (each doubled)")

    print("\n=== Errors are reported, not guessed at ===")
    for source, why in [
        ("  LI r1, 5000\n  LD r2, r1, 0\n  HALT\n", "out-of-range address"),
        ("  LI r1, 0\n  LI r2, 1\n  DIV r3, r2, r1\n  HALT\n", "division by zero"),
        ("loop:\n  JMP loop\n", "infinite loop"),
        ("  TID r1\n  HALT\n", "GPU instruction on the CPU"),
    ]:
        cpu = CPU()
        cpu.load(build(source))
        try:
            cpu.run(max_cycles=200)
            print(f"  {why:<28} NO ERROR — that is a bug")
        except CPUError as exc:
            print(f"  {why:<28} {exc}")


if __name__ == "__main__":
    _demo()
