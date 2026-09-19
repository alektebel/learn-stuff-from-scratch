"""
The KV cache — why generation gets linearly more expensive instead of quadratically.

A decoder generates one token at a time. At step *t* the new token's query must attend
to every token so far. Naively you recompute the keys and values of the whole prefix at
every step; the cache keeps them and appends one row per token.

DESIGN DECISION — cache the projections or the raw hidden states?
  Caching hidden states saves memory but forces you to re-project every prefix row at
  every step — the expensive matrix multiply you were trying to avoid.
  CHOSEN: cache the projected key and value vectors. That is what a real KV cache stores,
  and it is why the cache size is 2 · layers · heads · head_dim · tokens.

DESIGN DECISION — what does "correct" mean for a cache?
  A cache that is *approximately* right changes the model's output relative to the
  uncached path, and the difference is invisible until it compounds over hundreds of
  tokens.
  CHOSEN: exactness. `cached_step` must equal the last query's output from a full
  recompute to within floating-point error (1e-9 here, not "close enough").

DESIGN DECISION — model cost honestly?
  The win is not free memory. Cost is measured in query-key interactions: recompute does
  O(L²·d) per step over a growing prefix, the cache does O(L·d). The cost functions below
  make that ratio a number you can print.
"""

import math
from typing import Dict, List


def softmax(scores: List[float]) -> List[float]:
    """Stable softmax; subtract the max first. `-inf` entries become 0."""
    raise NotImplementedError


def attention(q: List[float], keys: List[List[float]], values: List[List[float]]) -> List[float]:
    """One query against a full set of keys/values; stable softmax weights."""
    raise NotImplementedError


class KVCache:
    """Accumulates projected keys and values, one row per generated token."""

    def __init__(self) -> None:
        self._keys: List[List[float]] = []
        self._values: List[List[float]] = []

    def append(self, key: List[float], value: List[float]) -> None:
        """Append one key row and one value row."""
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError

    def keys(self) -> List[List[float]]:
        raise NotImplementedError

    def values(self) -> List[List[float]]:
        raise NotImplementedError


def cached_step(q: List[float], cache: KVCache) -> List[float]:
    """Attend a single new query against everything in the cache."""
    raise NotImplementedError


def recompute_step(q: List[float], keys: List[List[float]], values: List[List[float]]) -> List[float]:
    """Attend a single query against an explicitly provided full history."""
    raise NotImplementedError


def recompute_work(prompt_len: int, decode_steps: int, d: int) -> int:
    """Query-key interactions if every step re-runs attention over the whole prefix.

    Step t (1-indexed) has prefix length `prompt_len + t`; a full pass costs
    length² · d. Sum over the steps.
    """
    raise NotImplementedError


def cached_work(prompt_len: int, decode_steps: int, d: int) -> int:
    """Query-key interactions with a cache: one new query, length keys, per step."""
    raise NotImplementedError
