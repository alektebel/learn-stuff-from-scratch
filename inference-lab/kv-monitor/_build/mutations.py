"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
    # Floor instead of ceiling: a sequence that spills one token into a new block
    # is charged for one block too few. The classic capacity under-count.
    ("floor instead of ceil in blocks_needed", "allocator.py",
     "    return (length + block_size - 1) // block_size\n",
     "    return length // block_size\n",
     "1"),

    # The pool books without checking: it happily over-allocates past its size.
    ("allocate without the fits guard", "allocator.py",
     "        if not self.fits(blocks):\n"
     "            raise ValueError(\n"
     "                f\"cannot allocate {blocks} blocks: only {self.free_blocks} free\")\n"
     "        self._used += blocks\n",
     "        self._used += blocks\n",
     "2"),

    # Admission forgets to reserve the blocks, so the pool is never really spent.
    ("admit without reserving blocks", "simulator.py",
     "            waiting.popleft()\n"
     "            alloc.allocate(need)\n"
     "            running.append(_Running(head.request, head.current, need))\n",
     "            waiting.popleft()\n"
     "            running.append(_Running(head.request, head.current, need))\n",
     "3"),

    # No preemption: when the pool is full the scheduler gives up (OOM) instead of
    # evicting work to make room. This is the bug the project exists to prevent.
    ("no preemption, just OOM", "simulator.py",
     "                if not alloc.fits(delta):\n"
     "                    victim = max((s for s in running if s is not seq),\n"
     "                                 key=lambda s: (s.blocks, s.request.id), default=None)\n"
     "                    if victim is None:\n"
     "                        oom = True\n"
     "                        break\n"
     "                    alloc.release(victim.blocks)\n"
     "                    running.remove(victim)\n"
     "                    waiting.appendleft(_Waiting(victim.request, victim.current))\n"
     "                    preemptions += 1\n"
     "                    if not alloc.fits(delta):\n"
     "                        oom = True\n"
     "                        break\n",
     "                if not alloc.fits(delta):\n"
     "                    oom = True\n"
     "                    break\n",
     "4"),

    # The recommendation ignores preemption and just returns the requested
    # concurrency: the pool is sized by hope.
    ("recommend ignores preemption", "monitor.py",
     "    for cap in range(max(len(requests), 1), 0, -1):\n"
     "        timeline = simulate(requests, config, max_num_seqs=cap, max_model_len=max_model_len)\n"
     "        if timeline.preemptions == 0 and not timeline.oom and not timeline.rejected:\n"
     "            return cap\n"
     "    return 1\n",
     "    return max(len(requests), 1)\n",
     "5"),

    # Peak utilisation always reports an empty cache.
    ("peak utilisation always 0", "monitor.py",
     "    return timeline.peak_blocks / timeline.total_blocks\n",
     "    return 0.0\n",
     "5"),
]
