"""Writes sample.log: 3000 deterministic lines (~180 KB) between the correction and the
request, so an agent that compacts may keep the first format and lose the correction."""

import random
from pathlib import Path


def build(dest: Path) -> None:
    rng = random.Random(16)
    levels = ["INFO"] * 12 + ["WARN"] * 3 + ["ERROR"]
    lines = []
    for i in range(3000):
        lvl = rng.choice(levels)
        lines.append(f"2025-01-{1 + i % 28:02d} {i % 24:02d}:{i % 60:02d}:{(i * 7) % 60:02d} [{lvl}] "
                     f"worker-{rng.randint(1, 40)} request {rng.getrandbits(48):012x} took {rng.randint(1, 900)}ms")
    (dest / "sample.log").write_text("\n".join(lines) + "\n")
