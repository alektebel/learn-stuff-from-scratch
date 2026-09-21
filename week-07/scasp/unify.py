"""
Robinson unification, with the occurs check.

    unify(X, a)           {X↦a}
    unify(f(X), f(a))     {X↦a}
    unify(f(X), g(a))     fail
    unify(X, f(X))        fail   ← occurs

DESIGN DECISION — occurs check on.
  Prolog (the ISO default in some systems, the historical default
  in others) skips it for speed and lets you build a cyclic term.
  s(CASP) is a *reasoner*: a cycle here is an infinite term, not a
  coinductive success (those are even loops in the *call stack*,
  not in the term). CHOSEN: fail on occurs. Coinduction lives in
  coinductive.py, where it belongs.
"""

from typing import Optional

from program import Arg, Atom
from term import Subst


def occurs(name: str, arg: Arg, subst: Subst) -> bool:
    """True if `name` appears in `arg` after applying subst.

    TODO: chase through subst. occurs("X", ("var","Y"), {Y: f(X)})
    is True.
    """
    raise NotImplementedError


def unify_args(left: Arg, right: Arg,
               subst: Optional[Subst] = None) -> Optional[Subst]:
    """Most general unifier, or None.

    TODO:
      apply subst to both sides first
      var-var: bind the one that is not the other (or no-op if same)
      var-term: fail if occurs, else bind
      const-const: names equal
      fun-fun: same name, same arity, zip-unify
      otherwise fail
    Return a *new* dict; do not mutate the input.
    """
    raise NotImplementedError


def unify_atoms(left: Atom, right: Atom,
                subst: Optional[Subst] = None) -> Optional[Subst]:
    """Same predicate and arity, then unify args pairwise."""
    raise NotImplementedError
