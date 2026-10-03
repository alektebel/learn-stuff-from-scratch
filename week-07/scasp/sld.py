"""
SLD resolution on *positive* programs.

A goal is a list of positive literals. A step picks the first,
finds a renamed clause whose head unifies, and replaces it with
the clause body (then applies the unifier to the whole goal).

Success is an empty goal. Failure is no matching clause.

This is Prolog. It is the MVP. The limit cases that force the rest
of the directory:

  p :- q. q :- p.          even loop — SLD diverges; coSLD succeeds
  p :- not p.              negation — SLD has no not
  flies(tweety)            default negation — needs duals + not

DESIGN DECISION — leftmost selection, depth-first.
  Any fair selection works for the positive programs here.
  Leftmost DFS is what you will have to *cut off* in
  coinductive.py when the same atom reappears, so CHOSEN: leftmost
  so the call stack is the ancestor list.
"""

from typing import Iterator, List, Optional, Tuple

from program import Atom, Clause, Literal
from term import Subst


def sld_step(goal: List[Literal], program: List[Clause],
             stamp: int) -> List[Tuple[List[Literal], Subst, int]]:
    """One expansion of the leftmost literal.

    TODO: if the leftmost is neg, raise ValueError — that is not
    this file's job. Rename the clause with `stamp`, unify heads,
    apply the unifier to (body + rest of goal). Return every
    matching clause as (new_goal, subst, stamp+1).
    """
    raise NotImplementedError


def sld(goal: List[Literal], program: List[Clause],
        max_steps: int = 64) -> Optional[Subst]:
    """Depth-first SLD. First success substitution, or None.

    TODO: if you hit max_steps, return None (do not raise). The
    even-loop program will hit this — that is the limit case
    coinductive.py exists for. The checker asserts sld(p, EVEN_LOOP)
    is None and coinductive_query(p, EVEN_LOOP) is a success.
    """
    raise NotImplementedError


def sld_all(goal: List[Literal], program: List[Clause],
            max_answers: int = 8,
            max_steps: int = 64) -> Iterator[Subst]:
    """Every success, up to max_answers.

    TODO: used by member/2, which has two answers in [a,a].
    """
    raise NotImplementedError
