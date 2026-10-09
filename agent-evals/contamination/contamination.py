"""contamination — detect train/eval overlap in text corpora (LEARN mode).

This file is the *contract*, not the implementation. ``jaccard`` ships as
test infrastructure (it is the exact oracle the MinHash estimate is graded
against); every core detector raises NotImplementedError until the learner
writes it. The tests in ``../tests/test_contamination.py`` define what must
be made true.

Standard library only. Fully deterministic: seed every random source, and
never use Python's built-in ``hash()`` — it is salted per process, so any
estimator built on it changes between runs, which defeats the point of a
reproducible contamination verdict.
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_N",
    "DEFAULT_THRESHOLD",
    "DEFAULT_NUM_PERM",
    "DEFAULT_SEED",
    "normalise",
    "tokenize",
    "exact_matches",
    "ngram_matches",
    "jaccard",
    "minhash",
    "report",
]

DEFAULT_N = 13
DEFAULT_THRESHOLD = 0.8
DEFAULT_NUM_PERM = 128
DEFAULT_SEED = 0


# ---------------------------------------------------------------------------
# Test infrastructure — implemented; tests may rely on it right now.
# ---------------------------------------------------------------------------

def jaccard(a: set, b: set) -> float:
    """Jaccard similarity |a ∩ b| / |a ∪ b|.

    Conventions: two empty sets are identical -> 1.0; exactly one empty
    set -> 0.0. This is the exact oracle the ``minhash`` estimate is
    graded against in the tests.
    """
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# Core detectors — stubs. Every test that calls one is marked
# xfail(raises=NotImplementedError, reason="core not implemented") until the
# learner implements it.
# ---------------------------------------------------------------------------

def normalise(text: str) -> str:
    """Canonical form every detector below works on.

    Must, in this order: drop fenced code blocks (a line starting with
    ``` or ~~~ opens/closes a fence; the delimiter lines and everything
    between them disappear), lowercase, delete every punctuation character
    (anything in ``string.punctuation``), collapse each run of whitespace
    to a single space, and strip the ends.

    Examples the tests pin down:
      "Hello,   WORLD!"  -> "hello world"
      "  don't  stop."   -> "dont stop"
    """
    raise NotImplementedError("core not implemented")


def tokenize(text: str) -> list[str]:
    """``normalise(text).split()`` — the token list n-grams are built from."""
    raise NotImplementedError("core not implemented")


def exact_matches(train: list[str], eval: list[str]) -> list[tuple[int, int]]:
    """Pairs ``(i, j)`` with ``normalise(train[i]) == normalise(eval[j])``.

    ``i`` indexes ``train``, ``j`` indexes ``eval``. Returned ascending by
    ``(i, j)``, each pair once.
    """
    raise NotImplementedError("core not implemented")


def ngram_matches(
    train: list[str], eval: list[str], n: int = DEFAULT_N
) -> list[tuple[int, int]]:
    """Pairs ``(i, j)`` whose normalised token lists share an n-gram.

    An n-gram is a tuple of ``n`` consecutive tokens, compared exactly.
    A text with fewer than ``n`` tokens has no n-grams: it can never match,
    and this must not crash. Returned ascending by ``(i, j)``, each pair
    once even when several n-grams are shared.
    """
    raise NotImplementedError("core not implemented")


def minhash(
    a: set, b: set, *, num_perm: int = DEFAULT_NUM_PERM, seed: int = DEFAULT_SEED
) -> float:
    """Estimate ``jaccard(a, b)`` with ``num_perm`` seeded hash functions.

    Reference shape: derive ``num_perm`` independent hash functions from
    ``random.Random(seed)`` (or equivalent keyed hashing, e.g.
    ``hashlib.blake2b`` with ``key=``), take each set's min-hash signature,
    and return the fraction of positions where the two signatures agree.

    Requirements the tests enforce: same inputs give the identical float
    across calls (and processes), the estimate tracks exact Jaccard within
    0.05 on a fixed pair, and built-in ``hash()`` is never used.
    """
    raise NotImplementedError("core not implemented")


def report(
    train: list[str],
    eval: list[str],
    *,
    n: int = DEFAULT_N,
    near_duplicate_threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    """One summary structure a caller can grade against.

    Keys:
      exact          -> exact_matches(train, eval)
      ngram          -> ngram_matches(train, eval, n)
      near_duplicate -> pairs (i, j) NOT in `exact` whose exact Jaccard of
                        token sets is >= near_duplicate_threshold (use the
                        exact computation so the report is reproducible;
                        minhash is the scale path, graded separately)
      n_eval         -> len(eval)
      flagged        -> [(eval_j, reason), ...] ascending by eval_j, one
                        entry per eval item touched by any match, reason
                        precedence "exact" > "ngram" > "near_duplicate"
    """
    raise NotImplementedError("core not implemented")
