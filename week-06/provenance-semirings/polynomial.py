"""
ℕ[X] — the free commutative semiring on a set of tuple ids.

A polynomial is a finite map monomial → coefficient, coefficients in ℕ.
A monomial is a finite map variable → exponent (exponent ≥ 1). Zero
coefficients are dropped; the zero polynomial is the empty map.

    2xy + z²   has   { {x:1, y:1}: 2, {z:2}: 1 }

This is the *most general* annotation for positive relational algebra.
Every other commutative semiring K is a homomorphic image of ℕ[X]:
you evaluate the polynomial in K after sending each variable to an
element of K. That is the whole point of the directory.

DESIGN DECISION — sparse maps, not dense arrays.
  The support of a how-polynomial is the set of derivations. A dense
  encoding in |X| variables is exponential in the number of tuples
  and hides the thing you want to read. CHOSEN: dict of monomials.
"""

from typing import Dict, Iterable, Tuple

# Monomial key: a sorted tuple of (name, exponent), exponents ≥ 1.
Monomial = Tuple[Tuple[str, int], ...]
Poly = Dict[Monomial, int]


def zero() -> Poly:
    """The empty map."""
    raise NotImplementedError


def one() -> Poly:
    """The empty monomial with coefficient 1 — the unit of ⊗."""
    raise NotImplementedError


def variable(name: str) -> Poly:
    """The polynomial that is just `name`."""
    raise NotImplementedError


def monomial_mul(left: Monomial, right: Monomial) -> Monomial:
    """Add exponents of like variables. Drop nothing; inputs are ≥ 1.

    TODO: merge the two sorted tuples like a merge-join on name.
    """
    raise NotImplementedError


def add(left: Poly, right: Poly) -> Poly:
    """Pointwise sum of coefficients. Drop zeros if any appear.

    TODO: do not mutate the inputs.
    """
    raise NotImplementedError


def mul(left: Poly, right: Poly) -> Poly:
    """Convolution: every pair of monomials, multiply, add coeffs.

    TODO: (x + y)(x + z) is x² + xz + xy + yz, not x + y + z.
    """
    raise NotImplementedError


def equal(left: Poly, right: Poly) -> bool:
    """True iff the same monomials have the same coefficients.

    TODO: treat a missing key as coefficient 0.
    """
    raise NotImplementedError


def support(poly: Poly) -> Iterable[Monomial]:
    """Monomials with positive coefficient."""
    raise NotImplementedError


def variables_of(poly: Poly) -> frozenset:
    """Every variable that appears in any monomial.

    TODO: this is the lineage homomorphism, as a set.
    """
    raise NotImplementedError


def coeff_sum(poly: Poly) -> int:
    """Sum of coefficients. The bag homomorphism (evaluate every xᵢ = 1,
    and also drop exponents: x² at 1 is still 1, so you must use
    Σ c_m · 1, not Σ c_m · ∏ exponents).

    Wait: evaluating x² at x=1 gives 1, and the coefficient is already
    the number of that derivation *shape*. For 2x + y the bag is 3.
    For x² (a derivation that used the same tuple twice) the bag is 1.
    TODO: sum of coefficients.
    """
    raise NotImplementedError
