"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
 "coalescing.py": {
  "sector_of": "The sector a byte address belongs to is address // 32. A sector spans [32k, 32k+31].",
  "sectors_touched": "A set over the 32 addresses removes duplicates: distinct sectors, not addresses.",
  "transferred_bytes": "Sectors touched times the sector size: the memory system moves whole sectors.",
  "efficiency": "Useful bytes (threads x bytes_per_thread) divided by transferred bytes; guard the empty access against a division by zero.",
  "is_fully_coalesced": "Fully coalesced means efficiency is exactly 1.0 — no byte was fetched and thrown away.",
 },
 "banks.py": {
  "bank_of": "Shared memory has 32 banks, each 4 bytes: bank = word_index % 32.",
  "serialisation_degree": "Group threads by bank, keep the set of DISTINCT word indices per bank, return the largest set. Same word twice is a broadcast, not a conflict.",
  "is_conflict_free": "Conflict-free means the degree is 1: every bank serves at most one word.",
  "tile_word_index": "Row-major with padding: row * (width + pad) + col.",
  "row_words": "Walk c from 0 to cols-1 at a fixed row; width is cols so padding shifts the row start.",
  "column_words": "Walk r from 0 to rows-1 at a fixed column, with the tile's real width and pad.",
  "tile_words": "A padded rows x cols tile holds rows * (cols + pad) words.",
 },
 "occupancy.py": {
  "registers_per_block": "Round regs_per_thread up to the allocation granularity (8), multiply by 32 threads per warp, then by the warps in the block.",
  "block_caps": "One cap per resource: max threads // threads_per_block, register file // registers_per_block, shared memory // round_up(smem, 256), and the max blocks per SM. A block with no shared memory is capped only by the block slots.",
  "max_active_blocks": "A block is resident only if every resource has room: the minimum of the caps, never below zero.",
  "active_warps": "Resident blocks times the warps per block, capped at the SM's maximum warps.",
  "occupancy": "Active warps divided by the SM's maximum warps.",
  "limiting_resource": "Which cap equals the minimum: registers, shared memory, threads or block slots.",
 },
 "roofline.py": {
  "arithmetic_intensity": "Flops divided by bytes moved.",
  "ridge_point": "The AI where the two roofs cross: peak flops per second divided by bandwidth.",
  "attainable_flops": "The lower of the two ceilings: min(peak_compute, bandwidth * arithmetic_intensity).",
  "is_memory_bound": "Memory-bound when the memory roof is strictly below the compute roof: ai * bandwidth < peak.",
  "bottleneck": "\"memory\" when is_memory_bound, otherwise \"compute\".",
  "attainable_fraction": "Attainable flops divided by peak flops, in (0, 1].",
 },
}
