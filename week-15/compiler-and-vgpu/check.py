"""
Progress checker for the compiler + virtual GPU templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

Nothing here imports solutions/. It tests YOUR code.
"""

import math
import pathlib
import shutil
import sys
import traceback

# Always read the learner's source fresh. Python validates cached bytecode on
# (mtime, size), so an edit that keeps a file the same size within the same
# second can be masked by a stale __pycache__ — and a checker you cannot trust
# is worse than no checker.
sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"

GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# Step 1: isa.py
# ---------------------------------------------------------------------------

def check_encoding() -> None:
    from isa import (IMM_MAX, IMM_MIN, NUM_REGISTERS, Instruction, decode,
                     encode)

    samples = [
        Instruction("ADD", rd=3, rs1=1, rs2=2),
        Instruction("LI", rd=5, imm=1234),
        Instruction("LD", rd=7, rs1=2, imm=0),
        Instruction("JZ", rs1=4, imm=100),
        Instruction("HALT"),
        Instruction("NOP"),
    ]
    for instruction in samples:
        word = encode(instruction)
        assert 0 <= word < (1 << 32), f"{instruction} encoded outside 32 bits"
        assert decode(word) == instruction, (
            f"{instruction} did not round-trip: got {decode(word)}")

    negative = Instruction("LI", rd=5, imm=-1234)
    word = encode(negative)
    assert decode(word) == negative, (
        f"a NEGATIVE immediate did not round-trip: {decode(word)} != {negative}. "
        "Two likely causes: you did not mask the immediate with "
        "((1 << IMM_BITS) - 1) when packing, so its sign bits corrupted the "
        "fields above it; or you did not SIGN-EXTEND when unpacking, so it read "
        "back as a large positive number. Both make every backward jump wrong.")

    assert encode(Instruction("LI", rd=1, imm=IMM_MAX)) is not None
    assert decode(encode(Instruction("LI", rd=1, imm=IMM_MIN))).imm == IMM_MIN

    # Distinct instructions must not collide.
    words = {encode(i) for i in samples}
    assert len(words) == len(samples), "two different instructions encoded alike"

    for bad, why in [(Instruction("LI", rd=1, imm=IMM_MAX + 1), "immediate too large"),
                     (Instruction("LI", rd=1, imm=IMM_MIN - 1), "immediate too small"),
                     (Instruction("ADD", rd=NUM_REGISTERS, rs1=1, rs2=2),
                      "register out of range")]:
        try:
            encode(bad)
            raise AssertionError(
                f"{why} was accepted. Silently truncating is far worse than "
                "refusing — it corrupts the opcode and the program runs, wrongly.")
        except ValueError:
            pass

    try:
        decode(0b111111 << 26)
        raise AssertionError("an unknown opcode must raise ValueError")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Step 2: assembler.py
# ---------------------------------------------------------------------------

def check_assembler() -> None:
    from assembler import (SUM_TO_N, AssemblyError, assemble,
                           assemble_to_words, first_pass)

    labels, program = first_pass(SUM_TO_N)
    assert labels == {"loop": 2, "done": 7}, (
        f"expected loop=2 and done=7, got {labels}. A label marks a POSITION "
        "and must not advance the address itself.")
    assert len(program) == 8, f"expected 8 instructions, got {len(program)}"

    instructions = assemble(SUM_TO_N)
    jnz = instructions[3]
    assert jnz.op == "JNZ" and jnz.imm == 7, (
        f"the forward reference to 'done' resolved to {jnz.imm}, expected 7. "
        "This is exactly why a single pass cannot work — at the JNZ the label "
        "has not been seen yet.")

    words = assemble_to_words(SUM_TO_N)
    assert len(words) == 8 and all(isinstance(w, int) for w in words)

    # Comments, blank lines and comma-free operands.
    compact = assemble("  ADD r1 r2 r3   # no commas\n\n  HALT ; trailing\n")
    assert len(compact) == 2 and compact[0].op == "ADD", \
        "comments (# and ;) and comma-free operands must both work"

    for bad, why in [
        ("  ADD r1, r2\n", "wrong operand count"),
        ("  FROB r1, r2, r3\n", "unknown instruction"),
        ("  ADD r1, r2, r99\n", "register out of range"),
        ("  JMP nowhere\n", "undefined label"),
        ("a:\na:\n  HALT\n", "duplicate label"),
    ]:
        try:
            assemble(bad)
            raise AssertionError(f"{why} was accepted")
        except AssemblyError as exc:
            assert "line" in str(exc), (
                f"the error for {why!r} does not name a line: {exc}. An "
                "assembler that says only 'syntax error' is a tool you will "
                "grow to hate.")


# ---------------------------------------------------------------------------
# Step 3: cpu.py
# ---------------------------------------------------------------------------

def check_cpu_basics() -> None:
    from assembler import assemble_to_words
    from cpu import CPU, CPUError

    cpu = CPU()
    cpu.load(assemble_to_words("""
        LI  r1, 10
        LI  r2, 3
        ADD r3, r1, r2
        SUB r4, r1, r2
        MUL r5, r1, r2
        DIV r6, r1, r2
        MOD r7, r1, r2
        HALT
    """))
    cpu.run()
    got = [cpu.registers[i] for i in range(3, 8)]
    assert got == [13, 7, 30, 3, 1], f"arithmetic wrong: {got}, expected [13, 7, 30, 3, 1]"

    cpu = CPU()
    cpu.load(assemble_to_words("""
        LI r1, 5
        LI r2, 7
        CMPLT r3, r1, r2
        CMPGT r4, r1, r2
        CMPEQ r5, r1, r2
        HALT
    """))
    cpu.run()
    assert [cpu.registers[3], cpu.registers[4], cpu.registers[5]] == [1, 0, 0], \
        "comparisons must write exactly 1 or 0"

    cpu = CPU()
    cpu.load(assemble_to_words("""
        LI r1, 2
        LD r2, r1, 0
        ADDI r2, r2, 100
        ST r1, r2, 10
        HALT
    """), data={2: 42})
    cpu.run()
    assert cpu.registers[2] == 142, f"LD/ADDI gave {cpu.registers[2]}, expected 142"
    assert cpu.memory[12] == 142, (
        f"ST should write to reg[rs1] + imm = 2 + 10 = 12, found "
        f"{cpu.memory[12]} there")


def check_cpu_control_and_errors() -> None:
    from assembler import SUM_TO_N, assemble_to_words
    from cpu import CPU, CPUError

    for n, want in ((1, 1), (5, 15), (10, 55), (100, 5050)):
        cpu = CPU()
        cpu.load(assemble_to_words(SUM_TO_N))
        cpu.registers[1] = n
        cpu.run()
        assert cpu.registers[2] == want, \
            f"sum(1..{n}) gave {cpu.registers[2]}, expected {want}"
    assert cpu.cycles > 0 and cpu.halted

    checks = [
        ("  LI r1, 5000\n  LD r2, r1, 0\n  HALT\n", "out-of-range address"),
        ("  LI r1, 0\n  LI r2, 1\n  DIV r3, r2, r1\n  HALT\n", "division by zero"),
        ("loop:\n  JMP loop\n", "infinite loop"),
        ("  TID r1\n  HALT\n", "GPU instruction on a scalar CPU"),
    ]
    for source, why in checks:
        cpu = CPU()
        cpu.load(assemble_to_words(source))
        try:
            cpu.run(max_cycles=300)
            raise AssertionError(f"{why} did not raise CPUError")
        except CPUError:
            pass


# ---------------------------------------------------------------------------
# Step 4: frontend.py
# ---------------------------------------------------------------------------

def check_lexer() -> None:
    from frontend import ParseError, tokenize

    kinds = [t.kind for t in tokenize("x = 1 + 2;")]
    assert kinds == ["NAME", "OP", "NUMBER", "OP", "NUMBER", "PUNCT"], \
        f"unexpected token kinds: {kinds}"

    assert [t.kind for t in tokenize("if while tid mem")] == \
        ["IF", "WHILE", "TID", "MEM"], (
        "keywords must get their own token kind in the LEXER — doing it there "
        "keeps the parser from special-casing identifiers everywhere")

    assert [t.text for t in tokenize("x // comment\ny")] == ["x", "y"], (
        "// comments must be dropped. If you got ['x', '/', '/', 'comment', "
        "'y'], your COMMENT pattern is listed AFTER OP in TOKEN_SPEC — "
        "alternation takes the first branch that matches, so '/' wins and the "
        "comment body lexes as identifiers.")
    assert [t.text for t in tokenize("a<=b")] == ["a", "<=", "b"], \
        "'<=' must lex as ONE token, not '<' followed by '='"

    try:
        tokenize("x = 1 $ 2;")
        raise AssertionError("an illegal character must raise ParseError")
    except ParseError:
        pass


def check_parser() -> None:
    from frontend import (Assign, Binary, If, Load, Num, ParseError, Store,
                          Tid, Var, While, parse)

    tree = parse("x = 1 + 2 * 3;")[0]
    assert isinstance(tree, Assign) and tree.name == "x"
    assert isinstance(tree.value, Binary) and tree.value.op == "+", (
        f"the ROOT of 1 + 2 * 3 must be '+', got "
        f"{getattr(tree.value, 'op', tree.value)}. '*' binds tighter, so it "
        "belongs deeper in the tree.")
    assert isinstance(tree.value.right, Binary) and tree.value.right.op == "*"

    tree = parse("x = 10 - 3 - 2;")[0]
    assert isinstance(tree.value.left, Binary), (
        "10 - 3 - 2 must nest to the LEFT — (10-3)-2 = 5, not 10-(3-2) = 9. "
        "If it nested right, you recursed with `power` instead of `power + 1`.")

    program = parse("""
    i = 0;
    while (i < 4) {
      if (mem[i] > 10) { total = total + mem[i]; } else { total = total + 1; }
      i = i + 1;
    }
    mem[100] = total;
    """)
    assert len(program) == 3
    loop = program[1]
    assert isinstance(loop, While) and isinstance(loop.body[0], If)
    assert loop.body[0].else_body, "the else arm was dropped"
    assert isinstance(program[2], Store)

    assert isinstance(parse("x = tid;")[0].value, Tid)
    assert isinstance(parse("x = mem[3];")[0].value, Load)
    assert isinstance(parse("x = (1 + 2) * 3;")[0].value, Binary) and \
        parse("x = (1 + 2) * 3;")[0].value.op == "*", \
        "parentheses must override precedence"

    for bad, why in [("x = ;", "missing expression"),
                     ("x = 1", "missing semicolon"),
                     ("if x { }", "missing parenthesis"),
                     ("= 5;", "statement starting with '='")]:
        try:
            parse(bad)
            raise AssertionError(f"{why} was accepted")
        except ParseError:
            pass


# ---------------------------------------------------------------------------
# Step 5: codegen.py
# ---------------------------------------------------------------------------

def check_codegen_cpu() -> None:
    from assembler import assemble_to_words
    from codegen import compile_source
    from cpu import CPU

    def run(source, data=None):
        assembly, spills = compile_source(source, gpu=False)
        cpu = CPU()
        cpu.load(assemble_to_words(assembly), data=data or {})
        cpu.run()
        return cpu, spills

    cpu, _ = run("mem[0] = 1 + 2 * 3;")
    assert cpu.memory[0] == 7, f"1 + 2 * 3 gave {cpu.memory[0]}, expected 7"

    cpu, _ = run("mem[0] = 10 - 3 - 2;")
    assert cpu.memory[0] == 5, f"10 - 3 - 2 gave {cpu.memory[0]}, expected 5"

    cpu, _ = run("mem[0] = (2 + 3) * 4;")
    assert cpu.memory[0] == 20, f"(2+3)*4 gave {cpu.memory[0]}, expected 20"

    # Derived comparisons — <=, >= and != have no opcode of their own.
    for expression, want in [("3 <= 3", 1), ("4 <= 3", 0), ("3 >= 4", 0),
                             ("3 != 4", 1), ("3 != 3", 0)]:
        cpu, _ = run(f"mem[0] = {expression};")
        assert cpu.memory[0] == want, \
            f"{expression} gave {cpu.memory[0]}, expected {want}"

    cpu, _ = run("if (1 < 2) { mem[0] = 111; } else { mem[0] = 222; }")
    assert cpu.memory[0] == 111, "the then arm did not run"
    cpu, _ = run("if (2 < 1) { mem[0] = 111; } else { mem[0] = 222; }")
    assert cpu.memory[0] == 222, "the else arm did not run"

    cpu, _ = run("i = 0;\ns = 0;\nwhile (i < 5) { s = s + i; i = i + 1; }\nmem[0] = s;")
    assert cpu.memory[0] == 10, f"0+1+2+3+4 gave {cpu.memory[0]}, expected 10"

    cpu, _ = run("""
    i = 0; total = 0;
    while (i < 4) {
      if (mem[i] > 10) { total = total + mem[i]; } else { total = total + 1; }
      i = i + 1;
    }
    mem[100] = total;
    """, data={0: 3, 1: 20, 2: 11, 3: 7})
    assert cpu.memory[100] == 33, \
        f"nested control flow gave {cpu.memory[100]}, expected 33"

    # Nested loops need unique labels.
    cpu, _ = run("""
    i = 0; n = 0;
    while (i < 3) { j = 0; while (j < 3) { n = n + 1; j = j + 1; } i = i + 1; }
    mem[0] = n;
    """)
    assert cpu.memory[0] == 9, (
        f"nested loops gave {cpu.memory[0]}, expected 9. If this jumped to the "
        "wrong place, your label generator is reusing names.")


def check_register_allocation() -> None:
    from assembler import assemble_to_words
    from codegen import ALLOCATABLE, compile_source, live_intervals
    from cpu import CPU

    def right_nested(depth: int) -> str:
        expression = str(depth)
        for i in range(depth - 1, 0, -1):
            expression = f"({i} + {expression})"
        return expression

    intervals = live_intervals(["    LI v0, 1", "    LI v1, 2",
                                "    ADD v2, v0, v1", "    HALT"])
    assert intervals[0] == (0, 2), f"v0 lives from line 0 to 2, got {intervals[0]}"
    assert intervals[1] == (1, 2) and intervals[2] == (2, 2)

    # Every allocated register must be inside the allocatable range.
    assembly, _ = compile_source("mem[0] = 1 + 2 * 3;")
    for line in assembly.splitlines():
        for token in line.replace(",", " ").split():
            assert not token.startswith("v"), \
                f"a virtual register survived allocation: {line.strip()!r}"

    # Correctness must hold whether or not spilling happened.
    spill_counts = []
    for depth in (5, 10, 14, 18, 24):
        program = f"x = {right_nested(depth)};\nmem[50] = x;"
        assembly, spills = compile_source(program)
        spill_counts.append(spills)
        cpu = CPU()
        cpu.load(assemble_to_words(assembly))
        cpu.run()
        want = sum(range(1, depth + 1))
        assert cpu.memory[50] == want, (
            f"at nesting depth {depth} ({spills} spills) the result was "
            f"{cpu.memory[50]}, expected {want}. Spilling may make code slower; "
            "it must never make it wrong. Check which operands are destinations "
            "(ST, JZ, JNZ, DIVERGE and LOOPTEST read their first operand).")

    assert spill_counts[0] == 0, (
        "a 5-deep expression should fit in the register file with no spills")
    assert spill_counts[-1] > 0, (
        f"a 24-deep RIGHT-nested expression needs ~25 simultaneously-live "
        f"values but there are only {len(ALLOCATABLE)} registers, so it must "
        "spill. Got 0 spills — is your allocator actually running, and are you "
        "sure the expression nests right rather than left? Left-nested "
        "temporaries die immediately and never exhaust the pool.")
    assert spill_counts == sorted(spill_counts), \
        f"spills should grow with depth, got {spill_counts}"


# ---------------------------------------------------------------------------
# Step 6: vgpu.py
# ---------------------------------------------------------------------------

def check_gpu_uniform() -> None:
    from assembler import assemble_to_words
    from codegen import compile_source
    from vgpu import WARP_SIZE, VirtualGPU

    assembly, _ = compile_source("mem[tid] = tid * 2;", gpu=True)
    gpu = VirtualGPU()
    gpu.load(assemble_to_words(assembly))
    gpu.run()

    assert gpu.memory[:WARP_SIZE] == [i * 2 for i in range(WARP_SIZE)], (
        f"expected each lane to write its own doubled id, got "
        f"{gpu.memory[:WARP_SIZE]}. Does TID give each lane its index?")
    assert gpu.efficiency() == 1.0, (
        f"a fully uniform kernel must run at 100% efficiency, got "
        f"{gpu.efficiency():.0%} — no lane should ever be masked off here")
    assert gpu.divergent_issues == 0
    assert gpu.instructions_issued > 0 and \
        gpu.lane_instructions == gpu.instructions_issued * WARP_SIZE


def check_gpu_divergence() -> None:
    from assembler import assemble_to_words
    from codegen import compile_source
    from vgpu import WARP_SIZE, VirtualGPU

    assembly, _ = compile_source(
        "if (tid < 4) { x = 100; } else { x = 200; }\nmem[tid] = x;", gpu=True)
    gpu = VirtualGPU()
    gpu.load(assemble_to_words(assembly))
    gpu.run()

    assert gpu.memory[:WARP_SIZE] == [100] * 4 + [200] * 4, (
        f"divergent if/else gave {gpu.memory[:WARP_SIZE]}, expected four 100s "
        "then four 200s. Each lane must get the arm ITS condition selected — "
        "that is the whole job of the mask stack.")
    assert 0.5 < gpu.efficiency() < 0.95, (
        f"efficiency {gpu.efficiency():.0%}. Both arms execute, each with only "
        "half the lanes active, so it must be well under 100% — and above 50%, "
        "since the surrounding uniform code runs at full width.")
    assert gpu.divergent_issues > 0, "no issue was recorded as divergent"
    assert gpu.stack == [], (
        "the mask stack is not empty at HALT — a DIVERGE was never matched by "
        "a CONVERGE, which would silently corrupt any later branch")

    # Nested divergence.
    assembly, _ = compile_source("""
    if (tid < 4) {
      if (tid < 2) { x = 1; } else { x = 2; }
    } else {
      if (tid < 6) { x = 3; } else { x = 4; }
    }
    mem[tid] = x;
    """, gpu=True)
    gpu = VirtualGPU()
    gpu.load(assemble_to_words(assembly))
    gpu.run()
    assert gpu.memory[:WARP_SIZE] == [1, 1, 2, 2, 3, 3, 4, 4], (
        f"nested divergence gave {gpu.memory[:WARP_SIZE]}, expected "
        "[1,1,2,2,3,3,4,4]. The mask stack must nest — that is why it is a "
        "stack and not a single register.")

    # CONVERGE must restore the ENCLOSING mask, not "all lanes". The statement
    # after the inner if is what exposes the difference: only lanes 0-3 are
    # still inside the outer then-arm and may run it.
    assembly, _ = compile_source("""
    if (tid < 4) {
      if (tid < 2) { x = 1; } else { x = 2; }
      mem[tid] = 99;
    } else {
      x = 3;
    }
    """, gpu=True)
    gpu = VirtualGPU()
    gpu.load(assemble_to_words(assembly))
    gpu.run()
    assert gpu.memory[:WARP_SIZE] == [99, 99, 99, 99, 0, 0, 0, 0], (
        f"after the inner if, memory is {gpu.memory[:WARP_SIZE]}, expected "
        "[99,99,99,99,0,0,0,0]. Lanes 4-7 wrote when they should not have, so "
        "CONVERGE restored the FULL mask instead of the mask that was active "
        "when the matching DIVERGE ran. Pop the saved outer mask.")

    # A divergent loop: lanes drop out at different times.
    assembly, _ = compile_source("""
    x = 0; i = 0;
    while (i < tid) { x = x + i; i = i + 1; }
    mem[tid] = x;
    """, gpu=True)
    gpu = VirtualGPU()
    gpu.load(assemble_to_words(assembly))
    gpu.run()
    want = [sum(range(t)) for t in range(WARP_SIZE)]
    assert gpu.memory[:WARP_SIZE] == want, (
        f"a ragged loop gave {gpu.memory[:WARP_SIZE]}, expected {want}. Lanes "
        "must drop out as their conditions fail while the warp keeps iterating "
        "for whoever is left.")


def check_gpu_limits() -> None:
    """The two failure modes worth building deliberately."""
    from assembler import assemble_to_words
    from codegen import compile_source
    from vgpu import GPUError, VirtualGPU

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
        gpu.run(max_issues=500)
        raise AssertionError(
            "a BAR inside divergent control flow must raise GPUError. The "
            "masked-off lanes can never reach it; on real hardware this "
            "deadlocks or is undefined, which is exactly why CUDA requires "
            "__syncthreads() to be reached by every thread in the block.")
    except GPUError:
        pass

    # A plain branch cannot express lanes disagreeing. Hand-written, because
    # the CPU build compiles `tid` to LI 0 — every lane would agree on 0, and
    # nothing would diverge.
    gpu = VirtualGPU()
    gpu.load(assemble_to_words("""
        TID r1
        LI  r2, 4
        CMPLT r3, r1, r2
        JZ  r3, skip
        LI  r4, 1
    skip:
        HALT
    """))
    try:
        gpu.run(max_issues=500)
        raise AssertionError(
            "a JZ whose lanes disagree must raise GPUError. Taking the "
            "majority would silently give wrong answers for the other lanes.")
    except GPUError:
        pass

    try:
        gpu = VirtualGPU()
        gpu.load(assemble_to_words("  CONVERGE\n  HALT\n"))
        gpu.run(max_issues=50)
        raise AssertionError("CONVERGE with an empty mask stack must raise")
    except GPUError:
        pass


# ---------------------------------------------------------------------------
# Step 7: capstone.py
# ---------------------------------------------------------------------------

def check_capstone() -> None:
    from capstone import run_on_gpu
    from vgpu import WARP_SIZE, VirtualGPU

    output, gpu = run_on_gpu("mem[tid] = mem[tid] + mem[tid];",
                             {i: i + 1 for i in range(WARP_SIZE)})
    assert output == [2 * (i + 1) for i in range(WARP_SIZE)], \
        f"uniform kernel gave {output}"
    assert gpu.efficiency() == 1.0

    # The comparison that makes the point: a warp beats one-lane-at-a-time by
    # the warp size on uniform work, and by much less when lanes diverge.
    from assembler import assemble_to_words
    from codegen import compile_source

    def serial_issues(source, data):
        words = assemble_to_words(compile_source(source, gpu=True)[0])
        total = 0
        for _ in range(WARP_SIZE):
            one = VirtualGPU(warp_size=1)
            one.load(words, data=data)
            one.run()
            total += one.instructions_issued
        return total

    uniform = "mem[tid] = mem[tid] + mem[tid];"
    data = {i: i + 1 for i in range(WARP_SIZE)}
    _, warp = run_on_gpu(uniform, data)
    speedup = serial_issues(uniform, data) / warp.instructions_issued
    assert speedup > WARP_SIZE * 0.9, (
        f"uniform speedup was only {speedup:.2f}x against a warp size of "
        f"{WARP_SIZE}. Uniform work is the case SIMT is built for — one fetch "
        "should do every lane's work.")

    ragged = "x = 0; i = 0;\nwhile (i < tid) { x = x + i; i = i + 1; }\nmem[tid] = x;"
    _, warp = run_on_gpu(ragged, {})
    ragged_speedup = serial_issues(ragged, {}) / warp.instructions_issued
    assert ragged_speedup < speedup / 2, (
        f"the ragged kernel sped up {ragged_speedup:.2f}x versus {speedup:.2f}x "
        "for the uniform one. It should be dramatically worse: lane 0 loops "
        "zero times and lane 7 loops seven, so the warp keeps issuing until the "
        "SLOWEST lane finishes while the rest sit masked off.")
    assert warp.efficiency() < 0.8


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("isa.py", "instruction encoding round-trip", check_encoding),
    ("assembler.py", "two-pass assembly with labels", check_assembler),
    ("cpu.py", "arithmetic, comparison, memory", check_cpu_basics),
    ("cpu.py", "control flow and error reporting", check_cpu_control_and_errors),
    ("frontend.py", "lexer and keywords", check_lexer),
    ("frontend.py", "parser: precedence and blocks", check_parser),
    ("codegen.py", "v1-v2: expressions and control flow", check_codegen_cpu),
    ("codegen.py", "v3: allocation and spilling", check_register_allocation),
    ("vgpu.py", "uniform SIMT execution", check_gpu_uniform),
    ("vgpu.py", "v4: divergence, nesting, ragged loops", check_gpu_divergence),
    ("vgpu.py", "barrier deadlock and disagreeing branches", check_gpu_limits),
    ("capstone.py", "one program, two machines", check_capstone),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:                       # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}Compiler + Virtual GPU — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None

    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue

        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<20} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<20} {title}")
            print(f"      {GREY}not implemented yet"
                  f"{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<20} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")

    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()

    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you built a compiler and a GPU.{RESET}")
        print(f"  {GREY}Now run each file's own demo to see the measurements,{RESET}")
        print(f"  {GREY}then compare your approach with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The TODO comments in that file walk through it. "
              f"Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
