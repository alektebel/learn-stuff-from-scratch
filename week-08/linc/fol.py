"""
First-order formulas as tagged tuples. No parser here — see parser.py.

    ("const", name)  ("var", name)
    ("pred", name, (terms,))
    ("not", φ)
    ("and", φ, ψ)  ("or", φ, ψ)  ("implies", φ, ψ)
    ("forall", var, φ)  ("exists", var, φ)

DESIGN DECISION — finite domain, then ground.
  A real LINC uses Prover9 (skolemisation, resolution, unlimited
  Herbrand universe). This repo has no prover binary and the
  fixtures are one-constant stories. CHOSEN: the caller hands you
  a domain; ∀x φ becomes ∧_{c∈D} φ[c/x], ∃x φ becomes ∨_{c∈D} φ[c/x].
  After grounding, the formula is propositional and saturate.py
  (in prover.py) can emit a proof. Named because a forgotten
  domain element is a silent change of meaning.
"""

from typing import List, Sequence, Tuple

Term = tuple
Formula = tuple


def subst_term(term: Term, var: str, const: str) -> Term:
    """TODO: replace ("var", var) with ("const", const). Walk nothing
    else — terms here are not nested.
    """
    raise NotImplementedError


def subst_formula(phi: Formula, var: str, const: str) -> Formula:
    """TODO: walk every constructor. A binder with the same name
    shadows: subst of ∀x ψ under x is ψ unchanged (and the binder
    stays). The fixtures do not nest same-name binders; still
    implement the shadow or the next person will.
    """
    raise NotImplementedError


def ground(phi: Formula, domain: Sequence[str]) -> Formula:
    """Eliminate quantifiers over `domain`.

    TODO: ∀ → a right-associated chain of ∧ ; ∃ → ∨.
    Empty domain: ∀ is True-as-empty-and. Represent that as
    ("pred", "⊤", ()) so the prover has a unit it can drop.
    Empty ∃ is ("pred", "⊥", ()).
    """
    raise NotImplementedError


def nnf(phi: Formula) -> Formula:
    """Negation-normal form. Push ¬ through.

    TODO: ¬¬φ = φ, ¬(a∧b)=¬a∨¬b, ¬(a∨b)=¬a∧¬b,
    ¬(a→b)=a∧¬b, ¬∀ = ∃¬, ¬∃ = ∀¬.
    After ground() there are no quantifiers left; still handle
    them so ground∘nnf and nnf∘ground agree on the fixtures.
    """
    raise NotImplementedError


def conjuncts(phi: Formula) -> List[Formula]:
    """Flatten ∧ into a list. A non-and is a singleton.

    TODO: used to turn a grounded theory into a clause set.
    """
    raise NotImplementedError


def pretty(phi: Formula) -> str:
    """Readable. The checker looks for predicate names, not layout."""
    raise NotImplementedError
