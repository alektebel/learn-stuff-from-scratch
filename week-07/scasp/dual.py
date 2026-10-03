"""
Dual rules — constructive negation for s(CASP).

A Clark completion reads a predicate as its if-and-only-if
definition. The *dual* is the completion's only-if direction,
skolemised into clauses for `not p`:

    p(X) :- q(X).
    p(X) :- r(X).

    # p holds iff q or r, so not-p holds iff not-q AND not-r
    not p(X) :- not q(X), not r(X).

For a fact p(a):

    not p(X) :- X ≠ a.

For a clause with a conjunction in the body, De Morgan splits
into one dual clause per conjunct (a choice of which conjunct
you refute):

    p(X) :- q(X), r(X).
    not p(X) :- not q(X).
    not p(X) :- not r(X).

s(CASP) generates these automatically so `not` is a *call*, not
a failure-as-negation. That is why it can return a binding for
`not p(X)` (X = b, when p(a) is the only fact) instead of just
failing or succeeding.

DESIGN DECISION — generate duals, do not implement negation-as-failure.
  NAF says "not p if p finitely fails". That cannot bind X in
  not p(X), and it diverges on even loops. Duals are clauses
  you already know how to run. CHOSEN: duals. The constructive
  witness is the substitution.
"""

from typing import List

from program import Atom, Clause


def group_by_predicate(program: List[Clause]):
    """TODO: dict pred → list of clauses whose head predicate is pred.
    Facts and rules both. Arity is part of the key: ('p', 1).
    """
    raise NotImplementedError


def duals_for(pred: str, arity: int, clauses: List[Clause]) -> List[Clause]:
    """Dual clauses for `not pred/arity`.

    Represent the dual head as the atom ("not_p", args) — a fresh
    predicate name, not a 'neg' literal. The engine will call
    not_p when it sees ('neg', ('p', args)).

    Cases the checker hits:
      UNIT, p/1, one fact p(a):
        not_p(X) :- neq(X, a).     (body is pos('neq', X, a))
      FLIES, penguin/1, one fact penguin(tweety):
        not_penguin(X) :- neq(X, tweety).
      FLIES, sparrow/1: same shape.
      A predicate with no clauses: not_p(...) is a fact
        (head not_p(X,Y,..), empty body) — everything is not-p.

    For p(X) :- q(X), r(X) the checker uses a tiny extra program
    (see check.py): two dual clauses, one per conjunct.

    TODO: do not emit a dual that calls not_not_p. Only one level.
    """
    raise NotImplementedError


def compile_duals(program: List[Clause]) -> List[Clause]:
    """Original program plus a dual family for every defined
    predicate, plus the built-in:

        neq(X, X) fails;  neq(X, a) binds nothing and succeeds
                          when X is already a different const.

    TODO: you do not implement neq as a clause — the engine
    special-cases the predicate 'neq'. Just generate the duals
    that *call* it. Return program + all duals.
    """
    raise NotImplementedError
