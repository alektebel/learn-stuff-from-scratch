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
        self.active = (1 << warp_size) - 1        # all lanes on
        self.stack: List[MaskEntry] = []
        self.halted = False
        self.trace = trace
        self.program: List[int] = []

        # Cost model: what we came here to measure.
        self.instructions_issued = 0      # warp-level fetches
        self.lane_instructions = 0        # useful per-lane work
        self.divergent_issues = 0         # issues with some lanes masked off

    # -- helpers ------------------------------------------------------------

    def lanes(self) -> List[int]:
        return [i for i in range(self.warp_size) if self.active >> i & 1]

    def mask_string(self, mask: Optional[int] = None) -> str:
        mask = self.active if mask is None else mask
        return "".join("1" if mask >> i & 1 else "." for i in range(self.warp_size))

    def load(self, words: List[int], data: Optional[Dict[int, int]] = None) -> None:
        self.program = list(words)
        self.pc = 0
        self.halted = False
        self.active = (1 << self.warp_size) - 1
        self.stack = []
        self.registers = [[0] * NUM_REGISTERS for _ in range(self.warp_size)]
        self.instructions_issued = 0
        self.lane_instructions = 0
        self.divergent_issues = 0
        for address, value in (data or {}).items():
            self.memory[address] = value

    # -- execution ----------------------------------------------------------

    def step(self) -> Optional[Instruction]:
        if self.halted:
            return None
        if not 0 <= self.pc < len(self.program):
            raise GPUError(f"pc {self.pc} outside the program")

        instruction = decode(self.program[self.pc])
        op, rd, a, b, imm = (instruction.op, instruction.rd, instruction.rs1,
                             instruction.rs2, instruction.imm)

        self.instructions_issued += 1
        live = self.lanes()
        self.lane_instructions += len(live)
        if len(live) < self.warp_size:
            self.divergent_issues += 1

        if self.trace:
            print(f"  {self.pc:>3}  [{self.mask_string()}]  {instruction}")

        next_pc = self.pc + 1

        # ---- control flow that manipulates the mask ----
        if op == "DIVERGE":
            taken = 0
            for lane in live:
                if self.registers[lane][a] != 0:
                    taken |= 1 << lane
            self.stack.append(MaskEntry("if", self.active,
                                        self.active & ~taken, imm))
            self.active = taken
            # Every lane took the else arm: skip the then arm entirely. This is
            # the one case where divergence costs nothing.
            if self.active == 0:
                next_pc = imm
            self.pc = next_pc
            return instruction

        if op == "ELSE":
            if not self.stack:
                raise GPUError(f"pc {self.pc}: ELSE with no matching DIVERGE")
            entry = self.stack[-1]
            self.active = entry.pending_mask
            self.stack[-1] = entry._replace(pending_mask=0, join_pc=imm)
            if self.active == 0:
                next_pc = imm
            self.pc = next_pc
            return instruction

        if op == "CONVERGE":
            if not self.stack:
                raise GPUError(f"pc {self.pc}: CONVERGE with no matching DIVERGE")
            self.active = self.stack.pop().outer_mask
            self.pc = next_pc
            return instruction

        if op == "LOOPTEST":
            # Lanes whose condition is false drop out and stay out until the
            # loop finishes. The warp keeps iterating for whoever is left.
            if not self.stack or self.stack[-1].kind != "loop":
                self.stack.append(MaskEntry("loop", self.active, 0, imm))
            still_going = 0
            for lane in self.lanes():
                if self.registers[lane][a] != 0:
                    still_going |= 1 << lane
            self.active = still_going
            if self.active == 0:
                next_pc = imm
            self.pc = next_pc
            return instruction

        if op == "BAR":
            # A barrier inside divergent control flow is a deadlock on real
            # hardware: the masked-off lanes will never arrive. We detect it
            # rather than hang, because "it hung" is a terrible error message.
            if self.stack:
                raise GPUError(
                    f"pc {self.pc}: BAR reached with {len(self.lanes())} of "
                    f"{self.warp_size} lanes active, inside divergent control "
                    "flow. The inactive lanes can never reach this barrier. On "
                    "real hardware this deadlocks or is undefined behaviour — "
                    "which is why CUDA requires __syncthreads() to be reached "
                    "by every thread in the block.")
            self.pc = next_pc
            return instruction

        if op == "HALT":
            self.halted = True
            self.pc = next_pc
            return instruction

        # ---- uniform control flow: the whole warp branches together ----
        if op in ("JMP", "JZ", "JNZ"):
            if op == "JMP":
                next_pc = imm
            else:
                if not live:
                    self.pc = next_pc
                    return instruction
                values = {self.registers[lane][a] for lane in live}
                truth = {(value != 0) for value in values}
                if len(truth) > 1:
                    raise GPUError(
                        f"pc {self.pc}: {op} with lanes disagreeing about the "
                        "condition. A plain branch cannot express that — the "
                        "compiler must emit DIVERGE/ELSE/CONVERGE instead. "
                        "(Did you compile with gpu=False?)")
                condition = truth.pop()
                if (op == "JZ" and not condition) or (op == "JNZ" and condition):
                    next_pc = imm
            self.pc = next_pc
            return instruction

        # ---- per-lane data operations ----
        for lane in live:
            reg = self.registers[lane]
            if op == "NOP":
                pass
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
                    raise GPUError(f"pc {self.pc}: lane {lane} divided by zero")
                reg[rd] = reg[a] // reg[b]
            elif op == "MOD":
                reg[rd] = reg[a] - reg[b] * (reg[a] // reg[b])
            elif op == "ADDI":
                reg[rd] = reg[a] + imm
            elif op == "CMPLT":
                reg[rd] = 1 if reg[a] < reg[b] else 0
            elif op == "CMPGT":
                reg[rd] = 1 if reg[a] > reg[b] else 0
            elif op == "CMPEQ":
                reg[rd] = 1 if reg[a] == reg[b] else 0
            elif op == "TID":
                reg[rd] = lane
            elif op == "LD":
                reg[rd] = self.memory[self._address(reg[a] + imm, self.memory)]
            elif op == "ST":
                self.memory[self._address(reg[a] + imm, self.memory)] = reg[b]
            elif op == "LDS":
                reg[rd] = self.shared[self._address(reg[a] + imm, self.shared)]
            elif op == "STS":
                self.shared[self._address(reg[a] + imm, self.shared)] = reg[b]
            else:
                raise GPUError(f"pc {self.pc}: unimplemented instruction {op}")

        self.pc = next_pc
        return instruction

    def _address(self, address: int, space: List[int]) -> int:
        if not 0 <= address < len(space):
            raise GPUError(f"pc {self.pc}: address {address} outside "
                           f"0..{len(space) - 1}")
        return address

    def run(self, max_issues: int = 100_000) -> int:
        while not self.halted:
            if self.instructions_issued >= max_issues:
                raise GPUError(f"still running after {max_issues} issues at "
                               f"pc {self.pc}")
            self.step()
        return self.instructions_issued

    # -- the number this whole file exists to produce ----------------------

    def efficiency(self) -> float:
        """Fraction of lane-slots that did useful work.

        1.0 means every lane was active on every issued instruction. 0.5 means
        you paid for a warp and used half of it. This is the metric that makes
        divergence concrete — and the one a real profiler calls warp execution
        efficiency or SM occupancy-weighted throughput.
        """
        total = self.instructions_issued * self.warp_size
        return self.lane_instructions / total if total else 0.0


def _demo() -> None:
    from assembler import assemble_to_words
    from codegen import compile_source

    print("=== Uniform: every lane does the same thing ===")
    source = "x = tid * 2;\nmem[tid] = x;"
    assembly, _ = compile_source(source, gpu=True)
    gpu = VirtualGPU()
    gpu.load(assemble_to_words(assembly))
    gpu.run()
    print(f"  mem[0:8] = {gpu.memory[0:8]}")
    print(f"  issues {gpu.instructions_issued}, lane-instructions "
          f"{gpu.lane_instructions}, efficiency {gpu.efficiency():.0%}")
    print("  Nothing diverges, so every issue does 8 lanes of work.")

    print("\n=== Divergent: lanes take different branches ===")
    source = """
    if (tid < 4) { x = 100; } else { x = 200; }
    mem[tid] = x;
    """
    assembly, _ = compile_source(source, gpu=True)
    gpu = VirtualGPU(trace=True)
    gpu.load(assemble_to_words(assembly))
    gpu.run()
    print(f"\n  mem[0:8] = {gpu.memory[0:8]}")
    print(f"  issues {gpu.instructions_issued}, efficiency {gpu.efficiency():.0%}, "
          f"{gpu.divergent_issues} issues with lanes masked off")
    print("  Both arms executed, one after the other. That is the cost.")

    print("\n=== Efficiency falls as divergence gets finer ===")
    print(f"{'condition':<22}{'issues':>8}{'efficiency':>12}")
    for label, condition in [("all lanes same", "tid < 8"),
                             ("half and half", "tid < 4"),
                             ("one lane differs", "tid < 7"),
                             ("alternating", "tid % 2 == 0")]:
        program = f"if ({condition}) {{ x = 1; }} else {{ x = 2; }}\nmem[tid] = x;"
        assembly, _ = compile_source(program, gpu=True)
        gpu = VirtualGPU()
        gpu.load(assemble_to_words(assembly))
        gpu.run()
        print(f"{label:<22}{gpu.instructions_issued:>8}{gpu.efficiency():>11.0%}")
    print("'all lanes same' still issues the DIVERGE and the empty ELSE — one")
    print("wasted slot, hence 92% rather than 100%. It does NOT execute the dead")
    print("arm's body, which is the part that would actually cost you.")
    print("Everything else pays for both arms at partial occupancy. This is why")
    print("GPU code is written to keep a warp's lanes agreeing where possible,")
    print("and why 'branch on tid/32' beats 'branch on tid%2' for the same work.")

    print("\n=== The limit case: a barrier inside divergence ===")
    gpu = VirtualGPU()
    gpu.load(assemble_to_words("""
        TID r1
        LI  r2, 4
        CMPLT r3, r1, r2
        DIVERGE r3, elsearm
        BAR
    elsearm:
        ELSE join
    join:
        CONVERGE
        HALT
    """))
    try:
        gpu.run()
        print("  no error — that is a bug")
    except GPUError as exc:
        print(f"  {exc}")


if __name__ == "__main__":
    _demo()
