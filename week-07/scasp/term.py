"""
Terms, atoms, substitutions.

A substitution is a dict var-name → arg. Application is recursive
through functors. Fresh variables are needed every time a clause is
used (otherwise member/2 on a nested list shares X with itself and
unifies when it must not).

DESIGN DECISION — explicit ("var","X") tags, not Prolog's uppercase
  convention on strings.
  A string is either a constant or a variable and you cannot tell
  after substitution. CHOSEN: tagged tuples, same as program.py.
"""

from typing import Dict, Set

from program import Arg, Atom, Literal


Subst = Dict[str, Arg]


def is_var(arg: Arg) -> bool:
    raise NotImplementedError


def var_name(arg: Arg) -> str:
    raise NotImplementedError


def apply_arg(arg: Arg, subst: Subst) -> Arg:
    """Walk functors. A variable not in subst is unchanged.

    TODO: if subst maps X to Y and Y to a, apply should give a
    (chase). One walk with recursion on the replacement is enough
    if you apply to the replacement too.
    """
    raise NotImplementedError


def apply_atom(atom: Atom, subst: Subst) -> Atom:
    raise NotImplementedError


def apply_literal(lit: Literal, subst: Subst) -> Literal:
    raise NotImplementedError


def vars_in_arg(arg: Arg) -> Set[str]:
    raise NotImplementedError


def vars_in_atom(atom: Atom) -> Set[str]:
    raise NotImplementedError


def rename_clause(head, body, stamp: int):
    """Return (head, body) with every variable suffixed by `_{stamp}`.

    TODO: X becomes X_7 when stamp=7. Walk every arg. The checker
    calls this before each resolution step; if you skip it, member
    will succeed on the wrong list.
    """
    raise NotImplementedError
