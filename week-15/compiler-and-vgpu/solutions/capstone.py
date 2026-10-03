"""
Step 7 — Capstone: one program, two machines. Complete Solution.

The payoff. The same source compiles for a scalar CPU and for a SIMT GPU, and
the two produce IDENTICAL results by construction — which is the property that
makes the comparison meaningful at all.

What the numbers show:
  - where SIMT wins (uniform work over many elements)
  - where it does not (divergent control flow, serial dependencies)
  - that the win is instruction ISSUES, not instructions executed
"""

from typing import Dict, List, Tuple

from assembler import assemble_to_words
from codegen import compile_source
from vgpu import WARP_SIZE, VirtualGPU


def run_on_gpu(source: str, data: Dict[int, int],
               threads: int = WARP_SIZE) -> Tuple[List[int], VirtualGPU]:
    assembly, _ = compile_source(source, gpu=True)
    gpu = VirtualGPU(warp_size=threads)
    gpu.load(assemble_to_words(assembly), data=data)
    gpu.run()
    return gpu.memory[:threads], gpu


def compare(name: str, source: str, data: Dict[int, int],
            threads: int = WARP_SIZE) -> None:
    """Run a kernel both ways and report the cost of each."""
    gpu_out, gpu = run_on_gpu(source, data, threads)

    # Scalar reference: run the GPU-compiled code with a one-lane warp per
    # thread. Same instructions, no SIMT, so any difference is the execution
    # model rather than the compiler.
    assembly, _ = compile_source(source, gpu=True)
    words = assemble_to_words(assembly)
    serial_issues = 0
    for _ in range(threads):
        one = VirtualGPU(warp_size=1)
        one.load(words, data=data)
        one.run()
        serial_issues += one.instructions_issued

    print(f"\n--- {name} ---")
    print(f"  GPU output      {gpu_out}")
    print(f"  warp issues     {gpu.instructions_issued}")
    print(f"  serial issues   {serial_issues}   (one lane at a time)")
    print(f"  speedup         {serial_issues / gpu.instructions_issued:.2f}x")
    print(f"  efficiency      {gpu.efficiency():.0%}")


def _demo() -> None:
    print("=" * 68)
    print("One source language, two execution models")
    print("=" * 68)

    print("\n=== The same program, compiled both ways ===")
    source = "if (tid < 4) { x = 1; } else { x = 2; }\nmem[tid] = x;"
    cpu_asm, _ = compile_source(source, gpu=False)
    gpu_asm, _ = compile_source(source, gpu=True)
    print(f"{'CPU build':<38}{'GPU build'}")
    cpu_lines = cpu_asm.splitlines()
    gpu_lines = gpu_asm.splitlines()
    for i in range(max(len(cpu_lines), len(gpu_lines))):
        left = cpu_lines[i] if i < len(cpu_lines) else ""
        right = gpu_lines[i] if i < len(gpu_lines) else ""
        print(f"{left:<38}{right}")
    print("\nSame front end, same registers, same arithmetic. The only")
    print("difference is how control flow is expressed: JZ/JMP for one thread,")
    print("DIVERGE/ELSE/CONVERGE for a warp whose lanes may disagree.")

    print("\n" + "=" * 68)
    print("Where SIMT wins and where it does not")
    print("=" * 68)

    compare("uniform: every lane doubles its element",
            "mem[tid] = mem[tid] + mem[tid];",
            {i: i + 1 for i in range(WARP_SIZE)})

    compare("divergent: lanes split two ways",
            "if (tid < 4) { x = 10; } else { x = 20; }\nmem[tid] = x;",
            {})

    compare("worst case: every lane a different branch depth",
            """
            x = 0;
            i = 0;
            while (i < tid) { x = x + i; i = i + 1; }
            mem[tid] = x;
            """,
            {})

    print("\n" + "=" * 68)
    print("Reading these numbers")
    print("=" * 68)
    print("""
The uniform kernel is the case SIMT is built for: one instruction fetch does
eight lanes of work, and the speedup approaches the warp size.

The divergent kernel still wins, but by less. Both arms are issued, so the
warp does the work of both and only the mask decides which lanes keep it.

The last kernel is the pathological one: lane 0 loops zero times and lane 7
loops seven, so the warp keeps issuing until the slowest lane finishes while
the finished lanes sit masked off. The warp runs at the speed of its slowest
lane — the SIMT equivalent of a straggler, and the reason irregular workloads
(graph traversal, sparse data, ragged batches) are hard on GPUs.

The general lesson, which outlives this toy: the GPU's advantage is amortising
INSTRUCTION ISSUE across lanes. Anything that makes lanes disagree spends that
advantage. Divergence is not a bug you can fix in the hardware — it is the
price of the design decision made at the top of vgpu.py.
""")


if __name__ == "__main__":
    _demo()
