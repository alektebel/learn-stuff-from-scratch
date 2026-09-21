"""
A semiring homomorphism h: K → K' preserves 0, 1, ⊕, ⊗:

    h(0) = 0'
    h(1) = 1'
    h(a ⊕ b) = h(a) ⊕' h(b)
    h(a ⊗ b) = h(a) ⊗' h(b)

The free-ness of ℕ[X] says: a homomorphism out of How is exactly a
valuation of the variables in the target. You do not get to pick
anything else. So "apply the trust homomorphism" *is* "evaluate the
polynomial with ⊕=max, ⊗=×, xᵢ ↦ trust(xᵢ)".

The provenance theorem (Green et al., Prop. 3.4 / the statement you
are here to feel):

    h( Q_How(I) )  =  Q_{K'}( h(I) )

Evaluate the query once, in ℕ[X]. Every other question is a
homomorphism. If this equality fails in your code, you did not
implement the query in the semiring — you implemented an annotation
pass that happens to look like one.

DESIGN DECISION — one `specialize`, not eight evaluators.
  A function per target (to_bag, to_trust, ...) will drift. CHOSEN:
  specialize(poly, target, valuation) and the target's own ⊕/⊗.
"""

from typing import Any, Dict

from polynomial import Poly
from semiring import Semiring


def specialize(poly: Poly, target: Semiring,
               valuation: Dict[str, Any]) -> Any:
    """Evaluate `poly` in `target` by sending each variable through
    `valuation` and using target.add / target.mul.

    A missing variable in `valuation` is target.one() for How-to-How
    identity tests; for every other target the checker passes a
    complete valuation. Boolean ignores the valuation (a variable
    is target.one() — the tuple exists). Bag ignores it too (each
    variable is 1). Why / lineage use the variable *name* as the
    payload: valuation may be omitted, treat x as { {x} } / {x}.

    TODO:
      empty poly → target.zero()
      a monomial c · x^e y^f → add(c copies of mul(val(x) e times,
        val(y) f times)). For Why/Lineage exponents collapse
        (x² is still {x}) — use the target's mul, which on a
        witness set is idempotent, so multiplying e times is fine
        as long as you start from the singleton, not from one().
      then ⊕ the monomials together.
    """
    raise NotImplementedError


def is_homomorphism(h, source: Semiring, target: Semiring,
                    samples) -> bool:
    """True iff h preserves 0, 1, add, mul on every pair in `samples`.

    `h` is a callable K → K'. `samples` is a list of source elements.
    Check h(0), h(1), and h(a⊕b), h(a⊗b) for every pair (a,b).

    TODO: use source.eq / target.eq, not ==, so Trust's epsilon applies.
    """
    raise NotImplementedError
