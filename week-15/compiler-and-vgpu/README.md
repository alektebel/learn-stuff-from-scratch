# Compiler + Virtual GPU

Build a compiler for a small language, a CPU to run it on, and a **virtual GPU** that
executes the *same instruction set* under a completely different execution model.

Then watch what that difference costs.

## The idea

Most compiler courses stop at "it produces correct code". Most GPU material starts at
"here is how to write a kernel". The interesting territory is between them: **the same
program, compiled once, executed two ways** — and the fact that one of those ways
punishes you for branching.

So the vGPU here deliberately runs the **identical ISA** as the CPU, plus a handful of
control instructions. Nothing about the arithmetic, the registers or the memory model
changes. The only difference is that a warp has **one program counter for eight lanes** —
and every consequence in this directory follows from that one decision.

## What you build

| Step | File | Effort | What it is |
|---|---|---|---|
| 1 | `isa.py` | small | 32-bit fixed-width instruction set, encode/decode |
| 2 | `assembler.py` | small | Two-pass assembler with labels |
| 3 | `cpu.py` | medium | Fetch–decode–execute, one thread |
| 4 | `frontend.py` | medium | Lexer + recursive-descent parser → AST |
| 5 | `codegen.py` | **large** | AST → assembly, then register allocation |
| 6 | `vgpu.py` | **large** | SIMT warp, divergence, barriers |
| 7 | `capstone.py` | small | One program, two machines, measured |

---

## How to use this directory

Templates at the top level, complete versions in `solutions/`.

```bash
cd compiler-and-vgpu
python3 check.py            # what to build next
python3 check.py            # re-run after each function
```

12 graded checks against **your** code. Red `✗` names the likely cause:

```
  ✗  6. frontend.py          parser: precedence and blocks
      10 - 3 - 2 must nest to the LEFT — (10-3)-2 = 5, not 10-(3-2) = 9.
      If it nested right, you recursed with `power` instead of `power + 1`.
```

---

## The two things this directory is built around

### 1. Design decisions are named, with their alternatives

Every file opens with the choices it embodies and why the rejected option was rejected:

> **DESIGN DECISION — register machine or stack machine?**
> A stack machine needs no register allocation at all. A register machine is what real
> hardware is, and forces you to confront allocation and spilling.
> **Chosen:** register machine, precisely *because* it creates the harder problem.
> A stack machine would have hidden step 5 entirely.

Others you will meet: fixed vs variable-width encoding (and why SIMT settles it), two-pass
vs backpatching, recursive descent vs a parser generator, linear scan vs graph colouring,
and the three real ways hardware handles divergence.

### 2. MVP first, then complicate — driven by limit cases

`codegen.py` is built in four visible stages, each forced by a concrete failure of the one
before:

```
v1  expressions, unlimited virtual registers      works, unrunnable
v2  ...now add control flow                       labels and jumps
v3  ...now only 16 registers exist                allocation, then spilling
v4  ...now lanes disagree about the branch        GPU divergence
```

**You watch v1 hit its limit.** Right-nested expressions keep every left operand live, so
spills appear at depth ~14 and grow — while every answer stays correct:

```
  depth  virtual regs   spills   result   ok
     10            21        0       55   OK
     14            29        1      105   OK
     18            37        5      171   OK
     24            49       11      300   OK
```

Told up front that a compiler needs a register allocator, you memorise it. Having written
code that runs out of registers, you could have invented one.

---

## The payoff

The capstone compiles one source twice and measures both:

```
uniform    (mem[tid] = mem[tid] + mem[tid])   8.00x speedup, 100% efficiency
divergent  (if (tid < 4) ...)                 6.86x,          75%
ragged     (while (i < tid) ...)              1.37x,          57%
```

The third is the one worth sitting with. Lane 0 loops zero times and lane 7 loops seven,
so the warp keeps issuing until the **slowest lane** finishes while the finished lanes sit
masked off. That is the SIMT straggler problem, and the reason graph traversal, sparse
data and ragged batches are hard on GPUs.

Trace a divergent kernel and you can see it happen:

```
    4  [1111....]  LI r3, 100
    7  [1111....]  ELSE 10
    8  [....1111]  LI r5, 200
   10  [....1111]  CONVERGE
   11  [11111111]  TID r6
```

Both arms executed, one after the other. The mask decides who keeps the result.

### The limit case worth building deliberately

A `BAR` inside divergent control flow. The masked-off lanes can never reach it. Real
hardware deadlocks or is undefined — your machine should say so:

```
pc 4: BAR reached with 4 of 8 lanes active, inside divergent control flow.
The inactive lanes can never reach this barrier... which is why CUDA requires
__syncthreads() to be reached by every thread in the block.
```

"It hung" is a terrible error message. Detecting this is worth the twenty lines.

---

## What this is not

- **Not an optimising compiler.** No constant folding, no CSE, no instruction scheduling,
  no peephole pass. The output is correct and naive, and you can read every line of it.
- **No functions.** No `CALL`/`RET`, no stack frames, no calling convention. That is the
  natural next extension and the README says so rather than pretending.
- **No types.** Everything is a machine word. No floats, no arrays beyond raw `mem[]`.
- **The vGPU is one warp**, not a grid of blocks. No scheduler, no occupancy, no memory
  coalescing, no cache hierarchy, no `LDS` bank conflicts.
- **The cost model counts instruction issues**, not cycles. Real performance is dominated
  by memory bandwidth and latency hiding, which this deliberately ignores.

## Extensions worth trying

1. **Functions.** Add `CALL`/`RET`, pick a calling convention, decide which registers are
   caller- vs callee-saved. This is where the register allocator gets genuinely hard —
   values live across a call.
2. **A peephole optimiser.** `LI rX, 0` followed by `ADD rY, rX, rZ` is just `MOV`. Count
   how many instructions you remove from the capstone kernels.
3. **Memory coalescing.** Give `LD`/`ST` a cost that depends on whether the warp's lanes
   touch consecutive addresses, then compare `mem[tid]` with `mem[tid * 17]`. That single
   number explains most GPU performance advice.
4. **Predication instead of a mask stack.** Add a predicate register and short-circuit
   `if` bodies below a length threshold. Measure where it beats DIVERGE.
5. **Multiple warps.** Add a scheduler that switches warps on a stall, and watch latency
   hiding appear — the actual reason GPUs tolerate slow memory.
6. **Constant folding in the front end**, then check how much of the spilling in step 5
   simply disappears.

---

## Structure

```
compiler-and-vgpu/
├── README.md
├── check.py              # progress checker — run this first
├── isa.py                # templates with TODOs and DESIGN DECISION blocks
├── assembler.py
├── cpu.py
├── frontend.py
├── codegen.py
├── vgpu.py
├── capstone.py
└── solutions/
```

```bash
cd solutions
python3 isa.py            # encoding round-trips and the limits it imposes
python3 assembler.py      # two passes, and why one will not do
python3 cpu.py            # sum 1..n, traced
python3 frontend.py       # precedence and associativity, as trees
python3 codegen.py        # v1 -> v3, and spilling appearing
python3 vgpu.py           # divergence traced, efficiency measured
python3 capstone.py       # the comparison
```

Pure Python 3 standard library. Everything runs in about a second.

## Related directories

- [`c-compiler/`](../c-compiler/) — a C compiler in C; this one is smaller and pairs with a GPU
- [`cuda-from-scratch/`](../../week-16/cuda-from-scratch/) — real CUDA, once you know what a warp is
- [`context-caching/`](../../week-03/context-caching/) — where GPU memory actually goes in practice
- [`PHILOSOPHY.md`](../../PHILOSOPHY.md) — why this repo is built the way it is

## Sources

- Nickolls, Buck, Garland & Skadron, **"Scalable Parallel Programming with CUDA"**, ACM Queue 2008 — what SIMT is, and the one-PC-per-warp model `vgpu.py` implements.
- Fung, Sham, Yuan & Aamodt, **"Dynamic Warp Formation"**, MICRO 2007 — branch divergence, the mask stack, and what hardware does about it.
- Patterson & Hennessy, **Computer Organization and Design** — instruction encoding, for `isa.py` and `assembler.py`.
- Poletto & Sarkar, **"Linear Scan Register Allocation"**, TOPLAS 1999 — the spilling in `codegen.py`.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-15--compilers)
