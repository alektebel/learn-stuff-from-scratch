"""
CoSLD: success through even loops.

An *even loop* is a call that repeats an ancestor atom (under
unification) with an even number of intervening negations — in
this directory, zero, because we only close positive loops.

    p :- q.  q :- p.   query p
    ancestors: p, q, p   ← p unifies with an ancestor, even, succeed

An *odd loop* (p :- not p) is not a success. The dual of p calls
not_p which calls p again through the negation — the ancestor
list sees p under one negation and fails that branch.

DESIGN DECISION — succeed the call, do not cut the search.
  Some implementations throw "loop detected" and fail. That is
  sound for *least* models and wrong for answer sets: the even
  loop is the justified true. CHOSEN: a unifiable ancestor with
  even negation depth is a success with the current substitution.
  The justification node is marked 'coinductive' so you can see
  it in justify.py.

The ancestor list is the call stack of atoms, each tagged with
the current negation depth.
"""

from typing import List, Optional, Tuple

from program import Atom, Clause, Literal
from term import Subst


def even_ancestor(atom: Atom, ancestors: List[Tuple[Atom, int]],
                  subst: Subst) -> bool:
    """True iff some ancestor (A, depth) unifies with atom and
    depth is even (0, 2, 4, ...).

    TODO: unify a *copy* — do not let a successful occurs-free
    unify mutate the ancestor. Depth 0 is the positive even loop.
    """
    raise NotImplementedError


def query(goal: List[Literal], program: List[Clause],
          max_steps: int = 64) -> Optional[Subst]:
    """Goal-directed s(CASP) without emitting a tree.

    TODO:
      compile duals once
      leftmost, DFS, rename clauses
      if leftmost is ('neg', a): rewrite to ('pos', ('not_'+pred, args))
      if leftmost pred is 'neq': succeed iff the two args, after
        subst, are different consts; fail if either is still a var
        (the checker only asks neq on ground consts)
      if even_ancestor: succeed this branch
      if odd ancestor (unifiable and depth odd): fail this branch
      otherwise SLD-step
      cap at max_steps
    """
    raise NotImplementedError
