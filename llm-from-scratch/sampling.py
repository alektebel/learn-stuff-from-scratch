"""
Decoding — turning a distribution over the vocabulary into one token.

The model outputs logits; this file picks a token. Temperature, top-k and top-p are the
three knobs every serving stack exposes, and each has one subtle rule that a plausible
implementation gets wrong.

DESIGN DECISION — filter logits or probabilities?
  top-k is naturally a logits operation (largest values). top-p is naturally a
  probability operation (cumulative mass). Mixing them invites double-softmax bugs.
  CHOSEN: filters take and return LOGITS, setting dropped entries to -inf; a single
  softmax at the very end turns whatever survived into probabilities. `exp(-inf) = 0`,
  so a dropped token gets exactly zero mass — no renormalisation step to forget.

DESIGN DECISION — what does temperature 0 mean?
  "Very small temperature" is a special case that still samples the tail occasionally.
  Greedy is a hard guarantee, not a limit.
  CHOSEN: temperature <= 0 returns a one-hot logits vector at the argmax, so the draw
  is deterministic by construction, not by chance.

DESIGN DECISION — top-p threshold comparison?
  Using `>` drops the token that crosses the threshold, so the kept mass can fall short
  of p and the nucleus is one token too small on exactly the examples people test by eye.
  CHOSEN: `>=`, checked AFTER adding each token, so the crossing token is always kept.

DESIGN DECISION — tie-break?
  Highest value, then smallest index. Without a rule, sampling is not reproducible.
"""

import math
from random import Random
from typing import List, Optional


def softmax(logits: List[float]) -> List[float]:
    """Stable softmax: subtract the max, normalise. `-inf` entries become 0."""
    raise NotImplementedError


def apply_temperature(logits: List[float], temperature: float) -> List[float]:
    """Divide logits by `temperature`.

    `temperature <= 0` means greedy: return a one-hot vector at the argmax (ties go
    to the smallest index), with -inf everywhere else.
    """
    raise NotImplementedError


def top_k_filter(logits: List[float], k: int) -> List[float]:
    """Keep the `k` largest logits, set the rest to -inf.

    Ties are broken by smallest index. `k >= len(logits)` is a no-op.
    """
    raise NotImplementedError


def top_p_filter(logits: List[float], p: float) -> List[float]:
    """Nucleus: keep the smallest set whose probability mass reaches `p`.

    Take probabilities (stable softmax), walk them from largest to smallest, and keep
    a token if the running sum is still below `p` BEFORE it or reaches `p` AT it —
    the token that crosses the threshold must survive.
    """
    raise NotImplementedError


def sample(
    logits: List[float],
    rng: Random,
    temperature: float = 1.0,
    k: Optional[int] = None,
    p: Optional[float] = None,
) -> int:
    """Apply temperature, then top-k, then top-p, softmax, and draw one index.

    Deterministic for a given `rng` state: two `Random(seed)` objects with the same
    logits and parameters return the same index.
    """
    raise NotImplementedError
