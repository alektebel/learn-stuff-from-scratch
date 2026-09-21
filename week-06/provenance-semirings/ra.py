"""
Positive relational algebra, annotated.

    σ_p(R)     keep rows where p(row); annotation unchanged
    π_A(R)     drop attributes not in A; colliding rows ⊕
    R ⋈_B S    natural join on attribute set B; annotation ⊗
    R ∪ S      union; colliding rows ⊕

No difference, no division: those need − and break the semiring.
That is why the free object is ℕ[X] and not ℤ[X].

The evaluator takes K and never mentions a specific semiring.
If you write `if K.name == "bag"` you have already lost — the
payoff check is that the *same* functions, with a different K,
agree with specialize(Q_How(I), K).

DESIGN DECISION — natural join on a named attribute set, not
  theta-join with an arbitrary predicate.
  A theta-join is σ after ×, and × is just ⋈ on the empty set.
  CHOSEN: one join. You can write the product as join(R, S, [], K).
"""

from typing import Callable, Sequence

from relation import Relation, Row
from semiring import Semiring


def select(rel: Relation, pred: Callable[[Row], bool],
           K: Semiring) -> Relation:
    """TODO: keep rows for which pred(dict) is true. Same annotation."""
    raise NotImplementedError


def project(rel: Relation, attrs: Sequence[str],
            K: Semiring) -> Relation:
    """TODO: each row becomes {a: row[a] for a in attrs}.
    Two source rows that agree on attrs: ⊕ their annotations.
    Missing attribute → raise KeyError, do not silently drop the row.
    """
    raise NotImplementedError


def join(left: Relation, right: Relation, on: Sequence[str],
         K: Semiring) -> Relation:
    """Natural join. A pair of rows matches when they agree on every
    attribute in `on`. The result row is the union of the two dicts.
    Annotation is left ⊗ right.

    TODO: nested loop is fine. Compact with ⊕ if two pairs produce
    the same result row (the running query should not, but union
    of two joins will).
    """
    raise NotImplementedError


def union(left: Relation, right: Relation, K: Semiring) -> Relation:
    """TODO: ⊕ on collision, otherwise copy."""
    raise NotImplementedError


def query_who_eats_where(likes: Relation, serves: Relation,
                         K: Semiring) -> Relation:
    """The running query: π_{person, cafe}(Likes ⋈_{food} Serves).

    TODO: join on ['food'], project ['person', 'cafe']. One line
    each. If you write a special case for Ada/Bar you will pass
    the fixture and fail the homomorphism the moment the instance
    grows.
    """
    raise NotImplementedError
