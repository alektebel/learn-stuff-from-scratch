"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
    ("count 128-byte lines instead of 32-byte sectors", "coalescing.py",
     "    return len({sector_of(a, sector_bytes) for a in addresses})\n",
     "    return len({a // LINE_BYTES for a in addresses})\n",
     "3"),
    ("count distinct banks, so a column read looks conflict-free", "banks.py",
     "    return max(len(words) for words in per_bank.values())\n",
     "    return len(per_bank)\n",
     "6"),
    ("ignore the register limit in occupancy", "occupancy.py",
     "    return max(0, min(caps.values()))\n",
     "    return max(0, min(caps[\"threads\"], caps[\"shared_memory\"], caps[\"blocks\"]))\n",
     "11"),
    ("use peak compute instead of the memory-bound roofline", "roofline.py",
     "    return min(peak_flops, ai * bandwidth)\n",
     "    return peak_flops\n",
     "14"),
]
