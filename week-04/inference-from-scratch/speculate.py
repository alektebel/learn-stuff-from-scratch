"""
Step 8 — Speculative decoding
=============================
A cheap draft model proposes K tokens; the target model verifies them in
one forward. Accepted prefix is committed; the first rejected token is
resampled from the target.

Speedup ≈ (tokens committed per verify) / (1 + draft_cost_ratio * K)
and ONLY if accept_rate is high enough to beat the draft overhead.

The function `should_speculate` is the whole lesson: it is not always
faster. Short drafts with a bad accept rate lose.

TODO:
  accept_prefix(draft_tokens, target_tokens) -> accepted count
    longest shared prefix length. 0 if the first token differs.
  verify_step(draft, target, k) -> {accepted, committed, target_forwards}
    committed = accepted + 1 (the resampled or next target token),
    target_forwards = 1
  expected_speedup(accept_rate, k, draft_cost_ratio) -> float
  should_speculate(accept_rate, k, draft_cost_ratio) -> bool
    True iff expected_speedup > 1.0
"""

from typing import Dict, Sequence


def accept_prefix(draft: Sequence[int], target: Sequence[int]) -> int:
    """TODO: length of the shared prefix. Stop at the first mismatch."""
    raise NotImplementedError


def verify_step(draft: Sequence[int], target: Sequence[int],
                k: int) -> Dict[str, int]:
    """TODO: look at draft[:k] vs target[:k].
    accepted = accept_prefix(...)
    committed = min(accepted + 1, k) if you resample inside the window,
                or accepted + 1 always (the +1 is the bonus token the
                target produces for free on a verify).
    The checker wants committed == accepted + 1 and target_forwards == 1.
    """
    raise NotImplementedError


def expected_speedup(accept_rate: float, k: int,
                     draft_cost_ratio: float) -> float:
    """E[committed] / (1 + draft_cost_ratio * k)

    E[committed] under independent per-token accept_rate is
        (1 - accept_rate**(k+1)) / (1 - accept_rate)     if accept_rate != 1
        k + 1                                            if accept_rate == 1
    That is the geometric series for "how many tokens survive".
    """
    raise NotImplementedError


def should_speculate(accept_rate: float, k: int,
                     draft_cost_ratio: float) -> bool:
    """TODO: expected_speedup(...) > 1.0"""
    raise NotImplementedError
