# GPU Memory System From Scratch

The part of GPU performance that can be simulated and graded on a CPU, in pure Python
(standard library only): coalescing, shared-memory bank conflicts, occupancy and the
roofline model.

This is **Step B** of the [CUDA roadmap](../ROADMAP.md). That roadmap orders everything by
one constraint: this environment has no GPU and no `nvcc`. The `.cu` exercises cannot run
here, but the memory behaviour that makes a kernel fast or slow is arithmetic, and
arithmetic runs anywhere. It extends [`compiler-and-vgpu/`](../../compiler-and-vgpu/),
which simulates the SIMT warp and divergence; this module takes the memory side.

The idea the module turns on: **a GPU instruction is priced by the bytes it moves, not by
how many instructions you wrote.** A warp of 32 threads issuing one load can cost 4 sectors
or 32; the same matrix multiply can be memory-bound or compute-bound; and a per-SM resource
you never looked at decides how many warps hide the latency.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Coalescing | count the 32-byte sectors one warp instruction touches; efficiency | `coalescing.py` | 1-4 |
| Bank conflicts | serialisation degree of an access; padding a tile to 33 | `banks.py` | 5-8 |
| Occupancy | resident blocks from registers / shared memory / threads per block | `occupancy.py` | 9-12 |
| Roofline | arithmetic intensity against bandwidth and peak compute | `roofline.py` | 13-16 |

## How to use this directory

Each `.py` file is a **template**: the function you write keeps its signature and docstring,
has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds a working
version for when you are stuck, or to compare afterwards.

```bash
cd cuda-from-scratch/memory-system
python3 check.py        # what to build next; stops at the first gap
python3 check.py 6      # one step
python3 check.py 5 8    # a range
python3 check.py --all  # everything
python3 solutions/coalescing.py   # once it passes, run the demo and read the numbers
```

`check.py` runs 16 checks against **your** code and never imports `solutions/`. Every
expected count is computed in `check.py` from the constructed pattern, so the checker never
asks your code what the right answer is. The limit cases are constructed, not random: a
stride of exactly 32 bytes, a 32x32 column, a kernel of exactly 33 registers.

**The checker was itself tested.** Four classic bugs were planted in copies of the
solutions, and each one has to be caught by its check:

| Planted bug | Caught by |
|---|---|
| count 128-byte cache lines instead of 32-byte sectors | step 3 |
| count distinct banks, so a 32x32 column read looks conflict-free | step 6 |
| ignore the register limit when computing occupancy | step 11 |
| return peak compute instead of the memory-bound roofline | step 14 |

Run them yourself from the repository root:

```bash
python3 .claude/skills/graded-module/scripts/mutate.py \
    cuda-from-scratch/memory-system cuda-from-scratch/memory-system/_build/mutations.py
```

It reports `CAUGHT` for all four.

## Design decisions, named

Each solution file's docstring names the alternatives and the cost of the choice. In short:

- **Count 32-byte sectors, not 128-byte cache lines.** The sector is what consumes DRAM
  bandwidth. Counting lines makes a stride-32-byte access (32 sectors, 8 lines) look 4x
  cheaper than it is. The cost of this choice: the model ignores L1/L2 hit rates entirely.
- **Bytes per thread is a parameter, default 4.** A float64 load with the same addresses
  moves twice the useful bytes; hardcoding 4 would score it 100% efficient when it is 50%.
- **Bank-conflict degree is a maximum over banks, and a repeated word is a broadcast.**
  One warp instruction costs its slowest bank, not the total; and hardware really does
  broadcast a repeated address in a bank, so reductions are not conflicts.
- **Registers are allocated per warp and rounded up to a granularity of 8.** 33 registers
  cost the same as 40, and a 100-thread block occupies four warps. Skipping the rounding is
  the classic reason a hand computed occupancy disagrees with the profiler.
- **Occupancy takes an `SMLimits` argument.** The hardware limits differ by architecture;
  making them a parameter turns a table to memorise into arithmetic you can re-run for
  another GPU. The default resembles a mid-range SM.
- **The roofline uses one DRAM bandwidth, not a cache hierarchy.** This is the MVP: below
  the ridge a kernel does not care about its flops, and that is the lesson. Cache blocking,
  which moves the ridge, is deliberately left to a later module.
- **Memory-bound is strict `<`.** At exactly the ridge point both roofs are equal, so
  neither is the bottleneck, and the two classifications are never both true.

## Questions to answer before reading the solutions

1. A warp reads `a[threadIdx.x * 2]` in float32. How many 32-byte sectors does it touch,
   and how many for `a[threadIdx.x]`? What is the efficiency ratio? (The same question the
   roadmap asks, now with a number you can check.)
2. Why does padding a 32x32 tile to 32x33 remove the column read's bank conflicts? Write
   the bank index of thread `r` in the padded tile before you look. What does the padding
   cost, in words and as a fraction of the tile?
3. A kernel uses 33 registers per thread with 256-thread blocks. Which resource limits
   occupancy, and what is the occupancy? Then answer for 128 registers. Which change buys
   more resident warps?
4. Vector add has an arithmetic intensity of 1/12 flop/byte; matmul at N=1024 has ~171.
   With a 10 TFLOP/s peak and 1 TB/s bandwidth, which is compute-bound, and what fraction
   of peak can each reach? Why does adding flops to vector add not help it?
5. Occupancy is not a goal. Give a kernel that is memory-bound at 25% occupancy and one
   that is compute-bound at 100%. Which would you rather schedule, and what does that say
   about "maximise occupancy"?

## Limits

- **Simulation, not silicon.** Sector sizes, bank counts and SM limits are model constants;
  real values vary by architecture. The arithmetic is exact given the model.
- **No caches, no latency, no instruction issue.** Coalescing counts sectors touched, not
  misses; occupancy counts resident warps, not achieved latency hiding; the roofline has
  one bandwidth, not L1/L2/DRAM. These are the parts a CPU checker can pin down exactly;
  the rest needs a profiler.
- **No actual CUDA.** Nothing here compiles or runs a kernel; `.cu` exercises live at the
  top of `cuda-from-scratch/`. Step C (reductions, scans, tiled matmul, attention) is a
  separate module.
- **One warp / one SM / one instruction at a time.** No multi-warp scheduling, no
  inter-SM effects, no measured timings.
