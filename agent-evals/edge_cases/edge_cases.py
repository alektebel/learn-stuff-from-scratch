"""edge_cases — generate synthetic edge cases for a gold task set (LEARN mode).

This file is the *contract*, not the implementation. The similarity machinery
(``normalize``, ``shingles``, ``jaccard``, ``minhash``, ``minhash_similarity``) and the
data model (``Case``, the ``FAMILIES``/markers) ship as test infrastructure; the four core
functions — ``transform``, ``generate``, ``is_trivial``, ``deduplicate`` (and ``build``,
which chains them) — raise ``NotImplementedError`` until the learner writes them. The tests
in ``../tests/test_edge_cases.py`` define what must be made true.

Why not call a model to invent cases: anything that leaves the process is neither
reproducible nor testable, and a generated case that is a paraphrase of a gold task teaches
nothing. This generator is deterministic — a seed and the gold set fix every case — and it
guards the two ways a generator lies: producing a near-copy of a task already in the set
(caught by MinHash dedup) and producing a case that is trivially solvable (caught by
``is_trivial``). A model-backed generator is named as out of scope.

Standard library only, fully deterministic.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass, field
from typing import Mapping, Sequence

__all__ = [
    "Case",
    "FAMILIES",
    "NEGATIONS",
    "INJECTION_MARKERS",
    "GOLD",
    "normalize",
    "shingles",
    "jaccard",
    "minhash",
    "minhash_similarity",
    "transform",
    "generate",
    "is_trivial",
    "deduplicate",
    "build",
]

# The families a case can come from. Each is a class of failure worth probing:
# an empty input, a non-ascii one, an over-long one, a boundary value, a
# self-contradictory instruction, and a prompt-injection payload.
FAMILIES = ("empty", "unicode", "long", "boundary", "contradiction", "injection")

# Vocabulary the families are checked against, so the tests and the core agree.
NEGATIONS = ("not", "never", "no", "without", "instead")
INJECTION_MARKERS = ("ignore", "disregard", "system prompt", "you are now")

# A few gold tasks; small on purpose, so a reader can see every generated case.
GOLD: dict[str, str] = {
    "t01-sum": "Write a function that returns the sum of a list of numbers.",
    "t02-csv": "Read data.csv and print the number of rows.",
    "t03-date": "Parse the date 2024-01-31 and print the next day.",
    "t04-words": "Reverse the words in the string 'hello world'.",
}


@dataclass(frozen=True)
class Case:
    """One generated input. ``source`` is the gold task id it was derived from."""

    source: str
    family: str
    statement: str
    meta: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Similarity machinery — implemented; tests may rely on them right now.
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Case-fold and collapse whitespace, so cosmetic differences compare equal."""
    return " ".join(text.split()).casefold()


def shingles(text: str, k: int = 3) -> set[str]:
    """The set of overlapping k-character shingles of the normalised text."""
    norm = normalize(text)
    if len(norm) <= k:
        return {norm} if norm else set()
    return {norm[i:i + k] for i in range(len(norm) - k + 1)}


def jaccard(a: str, b: str, k: int = 3) -> float:
    """Exact Jaccard similarity of two texts' shingle sets."""
    sa, sb = shingles(a, k), shingles(b, k)
    if not sa and not sb:
        return 1.0
    union = sa | sb
    return len(sa & sb) / len(union) if union else 0.0


def _hash(value: str) -> int:
    # crc32, not Python's salted hash(), so a signature is stable across processes.
    return zlib.crc32(value.encode("utf-8"))


def minhash(text: str, k: int = 3, n: int = 64) -> tuple[int, ...]:
    """An n-dimensional MinHash signature of a text (deterministic)."""
    sh = shingles(text, k)
    return tuple(min((_hash(f"{i}:{s}") for s in sh), default=0) for i in range(n))


def minhash_similarity(a: str, b: str, k: int = 3, n: int = 64) -> float:
    """Estimated Jaccard similarity from MinHash signatures (cheap for long texts)."""
    sig_a, sig_b = minhash(a, k, n), minhash(b, k, n)
    return sum(1 for x, y in zip(sig_a, sig_b) if x == y) / n


# ---------------------------------------------------------------------------
# Core the learner writes (NotImplementedError until then)
# ---------------------------------------------------------------------------

def transform(family: str, statement: str, rng) -> list[str]:
    """Apply one family to a statement and return the mutated statement(s).

    `rng` is a seeded ``random.Random``. Must be a pure function of its inputs and
    return at least one string that differs from `statement` (see SPEC.md for what
    each family must produce).
    """
    raise NotImplementedError


def generate(gold: Mapping[str, str], seed: int = 0,
             families: Sequence[str] = FAMILIES) -> list[Case]:
    """Deterministically derive one `Case` per (gold task, family)."""
    raise NotImplementedError


def is_trivial(case: Case, gold: Mapping[str, str]) -> bool:
    """True when a case is not worth keeping (empty, or unchanged from its source)."""
    raise NotImplementedError


def deduplicate(cases: Sequence[Case], gold: Mapping[str, str], threshold: float = 0.9,
                k: int = 3, n: int = 64) -> list[Case]:
    """Drop cases that are near-copies of a gold task or of an already-kept case."""
    raise NotImplementedError


def build(gold: Mapping[str, str], seed: int = 0, families: Sequence[str] = FAMILIES,
          threshold: float = 0.9) -> list[Case]:
    """`generate` → drop trivial → `deduplicate`; the reproducible pipeline."""
    raise NotImplementedError
