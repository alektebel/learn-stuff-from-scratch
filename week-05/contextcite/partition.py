"""
Step 1 — Partitioning the context into sources
===============================================
Paper: ContextCite (Cohen-Wang, Shah, Georgiev, Madry — NeurIPS 2024), section 3.
Reference implementation: context_cite/context_partitioner.py

Effort: small. This is the easiest file in the directory — get it exact anyway,
because every later step measures against the contexts it produces.

What you build:
  split_text          -> sentences plus the separators between them
  ContextPartitioner  -> .sources, and .build(mask) to reassemble an ablation

Background:
  A *source* is the unit of attribution: the thing an attribution score points
  at. Sentences are the useful default — small enough to localise an answer,
  large enough to still mean something on their own.

  Keeping the separators matters. If you rebuild an ablated context by joining
  sentences with a fixed string, the model sees text with different spacing and
  punctuation from the original, and every measurement is made against a
  context the model was never actually given.

  The invariant to protect: build() with an all-True mask must reproduce the
  original context EXACTLY.
"""

import re
from typing import List, Optional, Sequence, Tuple


def split_text(text: str) -> Tuple[List[str], List[str]]:
    """Split into sentences, returning (parts, separators).

    separators[i] is the whitespace that preceded parts[i] in the original
    text, so the pieces can be stitched back together losslessly.

    TODO:
    1. parts = re.split(r"(?<=[.!?])\\s+|\\n+", text.strip()), dropping blanks.
       The lookbehind keeps the punctuation attached to the sentence it ends.
    2. Walk the parts, using text.find(part, cursor) to locate each one, and
       record text[cursor:start] as that part's separator. Advance the cursor
       past the part.

    Test: for any text, "".join(interleaved separators and parts) should
    reconstruct it (modulo leading/trailing whitespace you stripped).
    """
    raise NotImplementedError


class ContextPartitioner:
    """Splits a context into sources and rebuilds ablated versions of it."""

    def __init__(self, context: str):
        self.context = context
        self.parts, self.separators = split_text(context)

    @property
    def num_sources(self) -> int:
        """TODO: how many sources the context was split into."""
        raise NotImplementedError

    def source(self, index: int) -> str:
        """TODO: the text of source `index`."""
        raise NotImplementedError

    @property
    def sources(self) -> List[str]:
        return list(self.parts)

    def build(self, mask: Optional[Sequence[bool]] = None) -> str:
        """Reassemble the context from the sources the mask keeps.

        TODO:
        1. A mask of None means "keep everything".
        2. Raise ValueError if the mask length does not match num_sources — a
           silent length mismatch here produces attributions for the wrong
           sources, which is very hard to notice later.
        3. Walk the sources in order. For each kept one: if anything has been
           emitted already, append its separator first (falling back to " " if
           the separator is empty), then append the source text.

        The "if anything has been emitted already" condition is what stops a
        stray leading separator when source 0 is ablated away.

        Test: build() == the original context. build([False] * n) == "".
        """
        raise NotImplementedError

    def __len__(self) -> int:
        return self.num_sources


def _demo() -> None:
    """Once implemented, check all of these:

    1. The running example splits into 8 sources, and source 4 is the sentence
       naming the P100 GPUs (see toy_lm.GROUND_TRUTH_SOURCE).
    2. build() reproduces the original context exactly — same string, same
       length. If this fails, stop and fix it now.
    3. Ablating source 4 removes 'P100' from the text.
    4. An all-False mask gives "", and a single-sentence context round-trips.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
