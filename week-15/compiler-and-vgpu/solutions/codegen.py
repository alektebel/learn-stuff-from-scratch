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
        self.variables: Dict[str, int] = {}     # name -> virtual register
        self.spills = 0

    # -- v1: expressions ----------------------------------------------------

    def fresh(self) -> int:
        """A new virtual register. Unlimited, on purpose."""
        self.next_virtual += 1
        return self.next_virtual - 1

    def label(self, stem: str) -> str:
        self.next_label += 1
        return f"{stem}{self.next_label}"

    def emit(self, text: str) -> None:
        self.lines.append(f"    {text}")

    def emit_label(self, name: str) -> None:
        self.lines.append(f"{name}:")

    def variable(self, name: str) -> int:
        if name not in self.variables:
            self.variables[name] = self.fresh()
            self.emit(f"LI v{self.variables[name]}, 0")
        return self.variables[name]

    BINARY_OPS = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD",
                  "<": "CMPLT", ">": "CMPGT", "==": "CMPEQ"}

    def expr(self, node) -> int:
        """Emit code for an expression; return the virtual register holding it."""
        if isinstance(node, Num):
            target = self.fresh()
            self.emit(f"LI v{target}, {node.value}")
            return target

        if isinstance(node, Var):
            return self.variable(node.name)

        if isinstance(node, Tid):
            target = self.fresh()
            if self.gpu:
                self.emit(f"TID v{target}")
            else:
                self.emit(f"LI v{target}, 0")   # a scalar CPU is thread 0
            return target

        if isinstance(node, Load):
            address = self.expr(node.address)
            target = self.fresh()
            self.emit(f"LD v{target}, v{address}, 0")
            return target

        if isinstance(node, Binary):
            # Derived comparisons, rather than more opcodes. <= is just !(>).
            if node.op in ("<=", ">=", "!="):
                base = {"<=": ">", ">=": "<", "!=": "=="}[node.op]
                inner = self.expr(Binary(base, node.left, node.right))
                target, zero = self.fresh(), self.fresh()
                self.emit(f"LI v{zero}, 0")
                self.emit(f"CMPEQ v{target}, v{inner}, v{zero}")
                return target

            left = self.expr(node.left)
            right = self.expr(node.right)
            target = self.fresh()
            self.emit(f"{self.BINARY_OPS[node.op]} v{target}, v{left}, v{right}")
            return target

        raise CodegenError(f"cannot generate code for {node!r}")

    # -- v2 and v4: statements and control flow -----------------------------

    def stmt(self, node) -> None:
        if isinstance(node, Assign):
            value = self.expr(node.value)
            self.emit(f"MOV v{self.variable(node.name)}, v{value}")
            return

        if isinstance(node, Store):
            address = self.expr(node.address)
            value = self.expr(node.value)
            self.emit(f"ST v{address}, v{value}, 0")
            return

        if isinstance(node, If):
            condition = self.expr(node.condition)
            if self.gpu:
                # v4: lanes may disagree. Both arms execute, each with the mask
                # that selects the lanes it applies to.
                else_label, join_label = self.label("else"), self.label("join")
                self.emit(f"DIVERGE v{condition}, {else_label}")
                for inner in node.then_body:
                    self.stmt(inner)
                self.emit_label(else_label)
                self.emit(f"ELSE {join_label}")
                for inner in node.else_body:
                    self.stmt(inner)
                self.emit_label(join_label)
                self.emit("CONVERGE")
            else:
                # v2: one thread of control, so a plain branch is enough.
                else_label, join_label = self.label("else"), self.label("join")
                self.emit(f"JZ v{condition}, {else_label}")
                for inner in node.then_body:
                    self.stmt(inner)
                self.emit(f"JMP {join_label}")
                self.emit_label(else_label)
                for inner in node.else_body:
                    self.stmt(inner)
                self.emit_label(join_label)
            return

        if isinstance(node, While):
            top, exit_label = self.label("loop"), self.label("endloop")
            self.emit_label(top)
            condition = self.expr(node.condition)
            if self.gpu:
                # Lanes drop out as their condition fails; the warp keeps
                # looping until none are left.
                self.emit(f"LOOPTEST v{condition}, {exit_label}")
            else:
                self.emit(f"JZ v{condition}, {exit_label}")
            for inner in node.body:
                self.stmt(inner)
            self.emit(f"JMP {top}")
            self.emit_label(exit_label)
            if self.gpu:
                self.emit("CONVERGE")
            return

        raise CodegenError(f"cannot generate code for {node!r}")

    def generate(self, program: List[Stmt]) -> str:
        for node in program:
            self.stmt(node)
        self.emit("HALT")
        return "\n".join(self.lines)


# ---------------------------------------------------------------------------
# v3: register allocation
# ---------------------------------------------------------------------------

def live_intervals(lines: List[str]) -> Dict[int, Tuple[int, int]]:
    """First and last line on which each virtual register appears.

    DESIGN DECISION — linear scan or graph colouring?
      Graph colouring builds an interference graph and colours it; it produces
      better allocations and is much more work.
      CHOSEN: linear scan over live intervals. It is a few dozen lines, it is
      what JITs use when compile time matters, and it makes the SHAPE of the
      problem visible: intervals that overlap need different registers.
      Approximating liveness by first-to-last mention is coarse — a value dead
      in the middle still holds its register — but it is never WRONG, only
      wasteful.
    """
    intervals: Dict[int, Tuple[int, int]] = {}
    for index, line in enumerate(lines):
        for token in line.replace(",", " ").split():
            if token.startswith("v") and token[1:].isdigit():
                virtual = int(token[1:])
                if virtual in intervals:
                    intervals[virtual] = (intervals[virtual][0], index)
                else:
                    intervals[virtual] = (index, index)
    return intervals


def allocate_registers(assembly: str) -> Tuple[str, int]:
    """Map virtual registers onto r0..r13, spilling when they run out.

    Returns (assembly, number of spills).

    The limit case this exists for: a program with more simultaneously-live
    values than the machine has registers. With 14 allocatable registers you
    have to nest expressions a fair way to hit it — which is exactly why the
    MVP works and feels fine right up until it does not.
    """
    lines = assembly.splitlines()
    intervals = live_intervals(lines)

    # Sort by start point — the "linear scan" of linear scan.
    order = sorted(intervals.items(), key=lambda item: item[1][0])

    assignment: Dict[int, int] = {}
    spilled: Set[int] = set()
    active: List[Tuple[int, int]] = []          # (end, virtual)
    free = list(ALLOCATABLE)

    for virtual, (start, end) in order:
        # Retire intervals that ended before this one began.
        for entry in [a for a in active if a[0] < start]:
            active.remove(entry)
            free.append(assignment[entry[1]])
        if free:
            assignment[virtual] = free.pop(0)
            active.append((end, virtual))
        else:
            # Spill the value that lives longest — it is the one least likely
            # to be needed again soon.
            active.sort(reverse=True)
            longest_end, victim = active[0]
            if longest_end > end:
                assignment[virtual] = assignment[victim]
                spilled.add(victim)
                del assignment[victim]
                active.pop(0)
                active.append((end, virtual))
            else:
                spilled.add(virtual)

    # Rewrite, materialising spilled values through the scratch registers.
    output: List[str] = []
    slots = {virtual: SPILL_BASE + index
             for index, virtual in enumerate(sorted(spilled))}

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.endswith(":"):
            output.append(line)
            continue

        parts = stripped.replace(",", " ").split()
        mnemonic, operands = parts[0], parts[1:]
        prologue: List[str] = []
        epilogue: List[str] = []
        rewritten: List[str] = []
        scratch_pool = [SCRATCH, SCRATCH2]

        for position, token in enumerate(operands):
            if not (token.startswith("v") and token[1:].isdigit()):
                rewritten.append(token)
                continue
            virtual = int(token[1:])
            if virtual in assignment:
                rewritten.append(f"r{assignment[virtual]}")
                continue
            # Spilled: load it before, store it after if it is the destination.
            physical = scratch_pool.pop(0)
            slot = slots[virtual]
            is_destination = position == 0 and mnemonic not in ("ST", "STS",
                                                                "JZ", "JNZ",
                                                                "DIVERGE",
                                                                "LOOPTEST")
            if not is_destination:
                prologue.append(f"    LI r{physical}, {slot}")
                prologue.append(f"    LD r{physical}, r{physical}, 0")
            else:
                epilogue.append(f"    LI r{SCRATCH2}, {slot}")
                epilogue.append(f"    ST r{SCRATCH2}, r{physical}, 0")
            rewritten.append(f"r{physical}")

        output.extend(prologue)
        output.append("    " + mnemonic + (" " + ", ".join(rewritten)
                                           if rewritten else ""))
        output.extend(epilogue)

    return "\n".join(output), len(spilled)


def compile_source(source: str, gpu: bool = False,
                   allocate: bool = True) -> Tuple[str, int]:
    """Front to back: source -> allocated assembly. Returns (asm, spills)."""
    assembly = Codegen(gpu=gpu).generate(parse(source))
    if not allocate:
        return assembly, 0
    return allocate_registers(assembly)


def _demo() -> None:
    from assembler import assemble_to_words
    from cpu import CPU

    print("=== v1: expressions, unlimited virtual registers ===")
    virtual, _ = compile_source("x = 1 + 2 * 3;", allocate=False)
    print(virtual)
    print("Every value gets its own register. Simple, and impossible to run —")
    print("the machine has 16, not however many the expression needed.")

    print("\n=== v3: the same code, allocated onto r0..r13 ===")
    allocated, spills = compile_source("x = 1 + 2 * 3;")
    print(allocated)
    print(f"spills: {spills}")

    print("\n=== It actually runs ===")
    source = """
    i = 0;
    total = 0;
    while (i < 4) {
      if (mem[i] > 10) { total = total + mem[i]; } else { total = total + 1; }
      i = i + 1;
    }
    mem[100] = total;
    """
    assembly, spills = compile_source(source)
    cpu = CPU()
    cpu.load(assemble_to_words(assembly), data={0: 3, 1: 20, 2: 11, 3: 7})
    cpu.run()
    expected = 20 + 11 + 1 + 1
    print(f"  input:    [3, 20, 11, 7]  (threshold 10)")
    print(f"  mem[100]: {cpu.memory[100]}   expected {expected}   "
          f"{'OK' if cpu.memory[100] == expected else 'WRONG'}")
    print(f"  {len(assembly.splitlines())} lines of assembly, {cpu.cycles} cycles, "
          f"{spills} spills")

    print("\n=== The limit case that forces the allocator ===")

    def right_nested(depth: int) -> str:
        """1 + (2 + (3 + ...)) — each left operand stays live across the whole
        rest of the expression, so N levels means N simultaneously-live values.

        Left-nested expressions do NOT do this: their temporaries die
        immediately and linear scan reuses one register forever. Which values
        are live at once is a property of the SHAPE of the expression, not its
        size — worth knowing before you go looking for a spill and cannot make
        one happen.
        """
        expression = str(depth)
        for i in range(depth - 1, 0, -1):
            expression = f"({i} + {expression})"
        return expression

    print(f"{'depth':>7}{'virtual regs':>14}{'spills':>9}{'result':>9}{'ok':>5}")
    for depth in (2, 5, 10, 14, 18, 24):
        program = f"x = {right_nested(depth)};\nmem[50] = x;"
        raw, _ = compile_source(program, allocate=False)
        used = len(live_intervals(raw.splitlines()))
        assembly, spills = compile_source(program)
        cpu = CPU()
        cpu.load(assemble_to_words(assembly))
        cpu.run()
        want = sum(range(1, depth + 1))
        print(f"{depth:>7}{used:>14}{spills:>9}{cpu.memory[50]:>9}"
              f"{('OK' if cpu.memory[50] == want else 'WRONG'):>5}")

    print("\nUp to ~13 live values everything fits in r0..r13 and the allocator")
    print("is invisible. Past that it spills to memory: slower, still correct.")
    print("That is the whole reason register allocation exists, and you just")
    print("watched the MVP hit its limit and the next stage absorb it.")


if __name__ == "__main__":
    _demo()
