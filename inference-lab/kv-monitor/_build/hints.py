"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
    "allocator.py": {
        "blocks_needed": "Reject block_size <= 0 and length < 0 with ValueError; otherwise return (length + block_size - 1) // block_size (0 for length 0).",
        "BlockAllocator.allocate": "Raise ValueError on a negative count or one that does not fit (use self.fits); then self._used += blocks.",
        "BlockAllocator.release": "Raise ValueError on a negative count or one greater than self._used; then self._used -= blocks.",
    },
    "simulator.py": {
        "simulate": "Per step: move arrivals (arrive <= step) into a FIFO deque; for each running sequence generate one token, growing its block count via blocks_needed and, when the pool is full, preempting the running sequence with the most blocks (free it, requeue at the front, count it) then retrying; completing a sequence releases its blocks and bumps `completed`; then admit from the queue while len(running) < cap and the blocks fit, rejecting any request whose final length exceeds total_blocks. Record alloc.used_blocks each step. Return a Timeline(total, used, running_counts, waiting_counts, preemptions, completed, rejected, oom).",
    },
    "monitor.py": {
        "peak_utilisation": "timeline.peak_blocks / timeline.total_blocks, or 0.0 when total_blocks is 0.",
        "steps_above": "Count entries u in timeline.used_blocks with u / timeline.total_blocks > threshold.",
        "recommend_max_num_seqs": "Try max_num_seqs from len(requests) down to 1; return the first cap whose simulate(...) has preemptions == 0, no oom and no rejected. Return 1 if none.",
    },
}
