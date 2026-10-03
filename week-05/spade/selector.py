"""
Step 4 — Select a minimal assertion set
=======================================
Paper: SPADE section 3. NP-hard; they solve an ILP. On the fixture (six
labels, a handful of candidates) exhaustive search is exact and honest.

Goal: choose a subset S of candidates such that
  - coverage: every labelled BAD output is flagged by at least one in S
  - FFR: the fraction of labelled GOOD outputs flagged by ANY in S
    is <= max_ffr
  - |S| is smallest among sets that satisfy the two constraints
  - if two sets are the same size, pick the one whose indices are
    lexicographically smallest (so the checker has one answer)

DESIGN DECISION — why not keep every candidate with FFR below the cap?
  Individually cheap assertions can be jointly expensive: the OR of ten
  noisy checks fails a clean output. The paper's second insight is that
  the SET has an FFR, not just the members. CHOSEN: evaluate the
  conjunction of "any selected assertion fired".

Subsumption (low-data): assertion A subsumes B if every example B flags
is also flagged by A. If A subsumes B, B is redundant. Drop B before
searching, unless A itself exceeds max_ffr as a singleton — then it is
not a usable cover and B stays.

This file is named selector.py because the stdlib already owns `select`.

TODO:
  false_failure_rate(assertions, labeled)
  coverage(assertions, labeled)          — fraction of bad outputs flagged
  subsumes(a, b, labeled)
  select(candidates, labeled, max_ffr)   — indices into candidates
"""

from typing import Callable, List, Sequence, Tuple


def evaluate(assertion: Callable[[str], bool],
             labeled: Sequence[Tuple[str, bool]]) -> List[bool]:
    """TODO: [not assertion(response) for response, _ in labeled]

    True means 'this assertion FLAGGED the output'. Keep that polarity
    straight: assertion returns True for OK, evaluate returns True for flag.
    """
    raise NotImplementedError


def false_failure_rate(flags_by_assertion: Sequence[Sequence[bool]],
                       labeled: Sequence[Tuple[str, bool]]) -> float:
    """FFR of the SET: a good output flagged by ANY assertion, over n_good.

    TODO: if there are no good labels, return 0.0 rather than dividing by 0.
    """
    raise NotImplementedError


def coverage(flags_by_assertion: Sequence[Sequence[bool]],
             labeled: Sequence[Tuple[str, bool]]) -> float:
    """Fraction of BAD outputs flagged by at least one assertion.

    TODO: 0.0 when there are no bad labels.
    """
    raise NotImplementedError


def subsumes(flags_a: Sequence[bool], flags_b: Sequence[bool]) -> bool:
    """A subsumes B iff every index where B is True, A is also True,
    and A flags at least everything B does (B may be weaker).

    An assertion does not subsume itself for the purpose of dropping
    (return False when flags_a == flags_b) — otherwise the selector
    deletes the whole pool.
    """
    raise NotImplementedError


def select(candidates: Sequence[dict],
           labeled: Sequence[Tuple[str, bool]],
           max_ffr: float = 0.25) -> List[int]:
    """Return a minimal list of candidate indices.

    TODO:
    1. Evaluate every candidate on `labeled`.
    2. Drop assertions subsumed by a cheaper-FFR singleton that itself
       is under max_ffr. If that is too much machinery for a first pass,
       skip subsumption and do the search over everyone — the fixture
       still has a unique minimum cover.
    3. Enumerate subsets by increasing size, then by index tuple.
    4. A subset is feasible when coverage == 1.0 and set-FFR <= max_ffr.
    5. Return the first feasible. [] if none (do not silently relax).
    """
    raise NotImplementedError
