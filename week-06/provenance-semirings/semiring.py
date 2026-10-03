"""
Eight commutative semirings. Same operations, different meanings.

A commutative semiring is (K, ⊕, ⊗, 0, 1) where
  (K, ⊕, 0) is a commutative monoid,
  (K, ⊗, 1) is a commutative monoid,
  ⊗ distributes over ⊕,
  0 annihilates: k ⊗ 0 = 0.

The eight, and the question each one answers about a result tuple:

  name        K                    ⊕        ⊗        question
  ----------  -------------------  -------  -------  --------------------------------
  how         ℕ[X]                 +        ×        *how* was it derived (free)
  why         finite sets of sets  ∪        ⊔*       which *witnesses* (sets of tuples)
  lineage     𝒫(X)                 ∪        ∪        which tuples appear at all
  boolean     {0,1}                ∨        ∧        does it exist
  bag         ℕ                    +        ×        how many derivations
  trust       [0,1]                max      ×        most-trusted derivation
  security    ℕ                    min      max      least clearance that still works
  tropical    ℕ∪{∞}                min      +        cheapest derivation

* why-product: { s ∪ t | s ∈ A, t ∈ B }  — pairwise union, not ∪.
  If you use ∪ for ⊗ you have built lineage under the wrong name.

DESIGN DECISION — eight instances, one interface.
  Most systems ship one annotation (a set of source ids, a score, a
  count) and hard-code what you can ask. CHOSEN: one Semiring protocol
  and eight implementations. The query evaluator never mentions which
  K it is in. That is what makes the homomorphism theorem even
  *possible* — there is a single Q, not eight Qs.

DESIGN DECISION — why is not lineage.
  Buneman's why-provenance keeps the *witnesses* (minimal sets that
  jointly produce the result). Lineage flattens them. ac + bd has
  why {{a,c},{b,d}} and lineage {a,b,c,d}. Collapsing them is the
  annotation-scheme failure the payoff check is for.
"""

from typing import Any, FrozenSet, Set


class Semiring:
    """One instance. `add` is ⊕, `mul` is ⊗."""

    name: str = ""

    def zero(self) -> Any:
        raise NotImplementedError

    def one(self) -> Any:
        raise NotImplementedError

    def add(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def mul(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def eq(self, left: Any, right: Any) -> bool:
        """TODO: structural equality. Trust compares as floats."""
        raise NotImplementedError


class How(Semiring):
    """ℕ[X] — polynomials. Delegate to polynomial.py."""

    name = "how"

    def zero(self) -> Any:
        raise NotImplementedError

    def one(self) -> Any:
        raise NotImplementedError

    def add(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def mul(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def eq(self, left: Any, right: Any) -> bool:
        raise NotImplementedError

    def variable(self, name: str) -> Any:
        """The polynomial that is just the variable `name`."""
        raise NotImplementedError


class Why(Semiring):
    """Finite set of witnesses. Each witness is a frozenset of tuple ids.

    0 = empty set of witnesses (impossible).
    1 = { ∅ } — one witness that uses no tuples (the unit of join).
    A ⊕ B = A ∪ B
    A ⊗ B = { a ∪ b | a ∈ A, b ∈ B }
    """

    name = "why"

    def zero(self) -> Set[FrozenSet[str]]:
        raise NotImplementedError

    def one(self) -> Set[FrozenSet[str]]:
        raise NotImplementedError

    def add(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def mul(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def eq(self, left: Any, right: Any) -> bool:
        raise NotImplementedError

    def singleton(self, name: str) -> Set[FrozenSet[str]]:
        """The why-value of a base tuple: { {name} }."""
        raise NotImplementedError


class Lineage(Semiring):
    """𝒫(X) with ∪ for both operations. 0 = ∅, 1 = ∅.

    Yes, 0 and 1 are the same element. Lineage is a degenerate semiring
    — that is the lesson, not a bug. Join and union both just collect
    sources, so you cannot recover multiplicity or witnesses from it.
    """

    name = "lineage"

    def zero(self) -> FrozenSet[str]:
        raise NotImplementedError

    def one(self) -> FrozenSet[str]:
        raise NotImplementedError

    def add(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def mul(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def eq(self, left: Any, right: Any) -> bool:
        raise NotImplementedError

    def singleton(self, name: str) -> FrozenSet[str]:
        raise NotImplementedError


class Boolean(Semiring):
    """({False, True}, ∨, ∧, False, True)."""

    name = "boolean"

    def zero(self) -> bool:
        raise NotImplementedError

    def one(self) -> bool:
        raise NotImplementedError

    def add(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def mul(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def eq(self, left: Any, right: Any) -> bool:
        raise NotImplementedError


class Bag(Semiring):
    """(ℕ, +, ×, 0, 1). A base tuple is 1."""

    name = "bag"

    def zero(self) -> int:
        raise NotImplementedError

    def one(self) -> int:
        raise NotImplementedError

    def add(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def mul(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def eq(self, left: Any, right: Any) -> bool:
        raise NotImplementedError


class Trust(Semiring):
    """([0, 1], max, ×, 0, 1). Alternative paths take the most trusted;
    a path's trust is the product of its tuples' trusts.

    DESIGN DECISION — max/× not max/min.
      max/min is the security lattice under another name. Trust *decays*
      when more tuples have to fire, so ⊗ is ×. You will see this on
      path ac (0.9×0.8=0.72) vs a min-encoding (min(0.9,0.8)=0.8).
    """

    name = "trust"

    def zero(self) -> float:
        raise NotImplementedError

    def one(self) -> float:
        raise NotImplementedError

    def add(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def mul(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def eq(self, left: Any, right: Any) -> bool:
        """TODO: abs(left-right) < 1e-9."""
        raise NotImplementedError


class Security(Semiring):
    """Clearance levels (ℕ, min, max, ∞, 0).

    ⊕ is min: if either derivation is allowed at this clearance, take
    the one that needs less. ⊗ is max: a join is allowed only if you
    clear every tuple in it.

    0 (impossible) is +∞ — you cannot clear an impossible derivation.
    1 (no tuples) is 0 — no clearance required.
    """

    name = "security"
    INF = 10**9

    def zero(self) -> int:
        raise NotImplementedError

    def one(self) -> int:
        raise NotImplementedError

    def add(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def mul(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def eq(self, left: Any, right: Any) -> bool:
        raise NotImplementedError


class Tropical(Semiring):
    """Min-cost (ℕ∪{∞}, min, +, ∞, 0). Cheapest derivation; a path
    costs the sum of its tuples.
    """

    name = "tropical"
    INF = 10**9

    def zero(self) -> int:
        raise NotImplementedError

    def one(self) -> int:
        raise NotImplementedError

    def add(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def mul(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def eq(self, left: Any, right: Any) -> bool:
        raise NotImplementedError


def all_semirings():
    """TODO: return one instance of each, in this order:
    How, Why, Lineage, Boolean, Bag, Trust, Security, Tropical.
    """
    raise NotImplementedError
