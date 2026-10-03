"""
An annotated relation: a list of (tuple, annotation) where the
annotation lives in whatever semiring the caller is using.

Two rows with the same tuple values are *the same row*. Combining
them is ⊕ — that is projection and union. If you keep them as two
list entries and only ⊕ at the end, join will double-count. The
checker will notice on π of a join.

DESIGN DECISION — dict keyed by frozenset of items, not a list.
  A list is easier to append to and silently wrong the first time
  two derivations produce the same tuple. CHOSEN: compact on every
  write, so the representation *is* the invariant.
"""

from typing import Any, Dict, Iterable, List, Sequence, Tuple

from semiring import Semiring

Row = Dict[str, Any]
# Internal: map frozen row → annotation.
Relation = Dict[frozenset, Any]


def row_key(row: Row) -> frozenset:
    """TODO: frozenset(row.items()). Values must be hashable."""
    raise NotImplementedError


def empty() -> Relation:
    raise NotImplementedError


def add_row(rel: Relation, row: Row, annotation: Any,
            K: Semiring) -> Relation:
    """Insert, or ⊕ with the annotation already stored for this row.

    TODO: do not mutate `rel` — return a new dict. The evaluator
    is easier to test if operators are pure.
    """
    raise NotImplementedError


def from_annotated(pairs: Sequence[Tuple[Row, str]],
                   K: Semiring) -> Relation:
    """Build a base relation.

    For How: annotation is K.variable(name) (or How.variable).
    For Why: K.singleton(name).
    For Lineage: K.singleton(name).
    For Boolean / Bag: K.one() — the tuple exists / has multiplicity 1.
    For Trust / Tropical / Security: the caller passes a valuation
    via from_annotated_valued.

    TODO: dispatch on K.name.
    """
    raise NotImplementedError


def from_annotated_valued(pairs: Sequence[Tuple[Row, str]],
                          K: Semiring,
                          valuation: Dict[str, Any]) -> Relation:
    """Like from_annotated, but each variable is replaced by
    valuation[name]. Used to evaluate Q directly in Trust/Tropical/
    Security so the homomorphism check has something to compare to.
    """
    raise NotImplementedError


def rows_of(rel: Relation) -> Iterable[Tuple[Row, Any]]:
    """Yield (dict, annotation) pairs. Dict rebuilt from the key."""
    raise NotImplementedError


def lookup(rel: Relation, row: Row, K: Semiring) -> Any:
    """Annotation of `row`, or K.zero() if absent."""
    raise NotImplementedError
