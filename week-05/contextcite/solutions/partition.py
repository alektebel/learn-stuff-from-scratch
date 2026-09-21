"""
Step 1 — Partitioning the context into sources. Complete Solution.

Paper: ContextCite, section 3 ("sources"). Reference implementation:
context_cite/context_partitioner.py.
"""

import re
from typing import List, Optional, Sequence, Tuple


def split_text(text: str) -> Tuple[List[str], List[str]]:
    """Split into sentence parts, keeping the separator that preceded each.

    Keeping separators is what lets an ablated context be reassembled as
    natural text rather than sentences jammed together. The reference
    implementation does the same thing with nltk; this uses a regex so the
    directory stays dependency-free.
    """
    parts = [p for p in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if p.strip()]

    separators: List[str] = []
    cursor = 0
    for part in parts:
        start = text.find(part, cursor)
        separators.append(text[cursor:start])
        cursor = start + len(part)
    return parts, separators


class ContextPartitioner:
    """Splits a context into sources and rebuilds ablated versions of it.

    A *source* is the unit of attribution. Sentences are the useful default:
    small enough to localise an answer, large enough to stay meaningful on
    their own. Words give finer attributions but need far more ablations to
    pin down, since the number of possible subsets grows with the source count.
    """

    def __init__(self, context: str):
        self.context = context
        self.parts, self.separators = split_text(context)

    @property
    def num_sources(self) -> int:
        return len(self.parts)

    def source(self, index: int) -> str:
        return self.parts[index]

    @property
    def sources(self) -> List[str]:
        return list(self.parts)

    def build(self, mask: Optional[Sequence[bool]] = None) -> str:
        """Reassemble the context from the sources the mask keeps.

        The all-ones mask must reproduce something equivalent to the original
        context — if it does not, every ablation is measured against a context
        the model never actually saw.
        """
        if mask is None:
            mask = [True] * self.num_sources
        if len(mask) != self.num_sources:
            raise ValueError(f"mask has {len(mask)} entries, "
                             f"expected {self.num_sources}")

        pieces: List[str] = []
        for index, keep in enumerate(mask):
            if not keep:
                continue
            if pieces:                       # no leading separator on the first
                pieces.append(self.separators[index] or " ")
            pieces.append(self.parts[index])
        return "".join(pieces)

    def __len__(self) -> int:
        return self.num_sources

    def __repr__(self) -> str:
        return f"<ContextPartitioner {self.num_sources} sources>"


def _demo() -> None:
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE

    partitioner = ContextPartitioner(CONTEXT)
    print(f"context split into {partitioner.num_sources} sources:\n")
    for index, source in enumerate(partitioner.sources):
        marker = "  <- answers the query" if index == GROUND_TRUTH_SOURCE else ""
        print(f"  [{index}] {source[:66]}{'...' if len(source) > 66 else ''}{marker}")

    print("\n=== The all-ones mask must round-trip ===")
    rebuilt = partitioner.build()
    print(f"rebuilt == original: {rebuilt == CONTEXT}")
    print(f"lengths: {len(rebuilt)} vs {len(CONTEXT)}")

    print("\n=== Ablating a single source ===")
    mask = [True] * partitioner.num_sources
    mask[GROUND_TRUTH_SOURCE] = False
    ablated = partitioner.build(mask)
    print(f"dropped source {GROUND_TRUTH_SOURCE}: "
          f"{len(CONTEXT)} -> {len(ablated)} characters")
    print(f"'P100' still present: {'P100' in ablated}")

    print("\n=== A random-looking ablation ===")
    mask = [True, False, False, True, True, False, True, False]
    print(f"mask {mask}")
    print(f"-> {partitioner.build(mask)[:120]}...")

    print("\n=== Edge cases ===")
    print(f"empty mask gives {partitioner.build([False] * 8)!r}")
    single = ContextPartitioner("Just one sentence with no separator.")
    print(f"single-sentence context: {single.num_sources} source, "
          f"round-trips: {single.build() == single.context}")


if __name__ == "__main__":
    _demo()
