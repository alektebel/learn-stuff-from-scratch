# GPU from scratch: roadmap with the GPU MODE lectures

Source: **GPU MODE lectures**, <https://github.com/gpu-mode/lectures> (supplementary code,
notebooks and slides; Apache-2.0), read at commit `77a8df4` (2026-09-08). The lectures
themselves are videos on the GPU MODE YouTube channel (verify the channel URL). 60 lectures
are listed; about 35 have material in the repository. Nothing from it is copied here: the
lectures are reading/viewing, and the exercises are this repo's own.

## The constraint that orders everything

This development environment has **no GPU and no `nvcc`**. So the `.cu` exercises in this
directory cannot be compiled or run here, and none of them has a graded checker yet.
What *can* be built and graded on a CPU is the part that makes GPU code fast or slow:
memory traffic, coalescing, bank conflicts, occupancy, and the algorithms (reductions,
scans, tiling, online softmax), simulated exactly. The plan uses that split.

## Where each lecture lands

| Lectures | Topic | Where in this repo | Bucket |
|---|---|---|---|
| 2, 3, 5 | PMPP ch. 1-3, first kernels, CUDA from Python | `01_vector_addition.cu` … `03_matrix_multiplication.cu` | covered (GPU required, ungraded) |
| 4 | compute and memory architecture | `compiler-and-vgpu/` (SIMT warp, divergence); memory side: **step B** | extends |
| 8 | performance checklist: coalescing, occupancy, divergence, tiling, privatization, coarsening | **step B** (simulated, graded) | new |
| 9 | reductions, including float non-determinism from summation order | `04_reduction.cu`; numerics: **step C** | extends |
| 20, 21, 24 | scan (prefix sum) | **step C** | new |
| 12 | Flash Attention | **step C** (online softmax, tile by tile, exactness + traffic) | new |
| 18 | fused kernels | **step C** (traffic saved by fusion, counted) | new |
| 1, 16 | profiling kernels in PyTorch, hands-on profiling | GPU required: `inference-lab/` #2 | planned |
| 14, 29, 34, 104 | Triton: practitioner's guide, internals, low-bit kernels, Gluon | `inference-lab/` #7 (Triton kernel; correctness on CPU with `TRITON_INTERPRET=1`) | planned |
| 23, 15, 36, 57, 86, 103, 114 | tensor cores, CUTLASS, CuTe and its layout algebra | GPU required; layout algebra (103) is pure math and could be a CPU module | gap |
| 7, 30, 33, 34, 69 | quantization, quantized and 4-bit training | `inference-lab/` #5, `ml-systems/framework` part 3 | planned |
| 22, 35, 40 | speculative decoding in vLLM, SGLang, FlashInfer | `inference-lab/` #6, `sgl-lang/`, `vllm-engine/` | planned / guides |
| 13 | ring attention | `distributed-training/` | guide |
| 17, 67, 70, 78 | NCCL, NVSHMEM, fault-tolerant collectives, multi-GPU Triton | `distributed-training/`; all-reduce from scratch is a candidate (also CS249r Vol II ch. 6) | gap |
| 37 | SASS and GPU microarchitecture | `compiler-and-vgpu/` (its own ISA) | related |
| 84 | numerics and AI | **step C** (summation order, bf16) | new |
| 11, 6, 28, 32, 39, 79 | sparsity, optimizers, Liger, Unsloth, TorchTitan, mega-kernels | reading | link |
| 25, 26, 31, 38 | AMD Composable Kernel, SYCL, Metal, ARM low-bit | vendor-specific | link |
| 71, 72, 74 | ScaleML: FlexOlmo, long context, PaTH attention | `llm-from-scratch/` reading | link |

## The plan: three steps, one at a time

**Step A — make the existing `.cu` exercises gradable (GPU required).** A `check.py` that
compiles with `nvcc`, runs each exercise against a CPU reference, and reports TODO/FAIL
like every other module. It can be written here; it can only be *run* on a machine with
a GPU.

**Step B — the memory system, simulated and graded on CPU** (extends `compiler-and-vgpu/`):
- given each thread's addresses in a warp, count the 32-byte sectors touched (coalescing);
- shared-memory bank conflicts: the serialisation degree of an access pattern, and how
  padding a tile removes it;
- an occupancy calculator from registers per thread, shared memory per block and threads
  per block against per-SM limits;
- a roofline: arithmetic intensity against bandwidth and peak compute.
Checks are exact counts on constructed patterns (a strided access touching 32 sectors, a
column read of a 32x32 tile with a 32-way conflict, padding to 33 fixing it).

**Step B built:** [`memory-system/`](memory-system/) — 16 graded checks over four templates, mutation-tested.

**Step C — GPU algorithms, simulated exactly on CPU** (new module, numpy):
- tree reductions, and why the result depends on the summation order in float32;
- scans: Hillis-Steele and Blelloch, with work and depth counted;
- tiled matmul: global-memory traffic as a function of tile size;
- online softmax and a tile-by-tile attention that matches naive attention to 1e-6 while
  never materialising the N x N matrix; traffic counted for both;
- kernel fusion: bytes moved by unfused versus fused elementwise chains.

Pick one; nothing is built until then. Step B is the recommended start: it runs here, and it
is the content of lecture 8, the one most others assume.

## Reading for each step: [AI Performance Engineering resources](https://github.com/wafer-ai/gpu-perf-engineering-resources)

A curated list by Wafer (MIT, read at `1c52412`, 2026-09-12), with a strict source policy:
only originating papers, official documentation, implementations, or implementer reports
with code and measurements; performance numbers without hardware, workload, precision and
baseline are left out. That policy is the same discipline these modules ask for. Its 121
links are not copied here (8 were already in this repo); read the sections instead:

| Before | Read in that list | The sources the step implements |
|---|---|---|
| step B | "Start here" (in order), then "1. GPU fundamentals" | the roofline paper (Williams, Waterman, Patterson); NVIDIA's matrix-transpose post (coalescing, tiling, bank conflicts) |
| step C | "2. Kernel optimization": foundational exercises, matrix multiplication, attention | Harris, *Optimizing Parallel Reduction*; Merrill and Garland, single-pass scan with decoupled look-back; Milakov and Gimelshein, online softmax (arXiv 1805.02867) |
| step A, Triton | "3. Programming models and profiling" | its profiling/correctness subsection is the checklist for a GPU `check.py` |
| tensor cores, CuTe | "2. Tensor cores and low precision", "3. CUTLASS, CuTe, and CUDA Tile" | gap in this repo |

Authors above are from memory; verify before citing.

## Questions to answer before building (no answers here)

1. A warp reads `a[threadIdx.x * 2]` in float32. How many 32-byte sectors, and how many for
   `a[threadIdx.x]`? What is the efficiency ratio?
2. Why does padding a 32x32 shared-memory tile to 32x33 remove the bank conflicts of a
   column read, and what does it cost?
3. Summing 10^7 float32 values sequentially and as a tree gives different results. Which
   one is closer to the exact sum, and why?
4. Flash Attention computes exactly the same result as naive attention. What does it save,
   and what does it pay instead?
