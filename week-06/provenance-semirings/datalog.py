"""
Recursive Datalog, annotated, and the reason it is not free.

Positive RA is a polynomial. Recursion is a *least fixpoint* of
polynomials. That LFP exists in every ω-continuous semiring, and
it is reached in finitely many steps in every *absorptive* one:

    a ⊕ (a ⊗ b)  =  a     for all a, b

Absorption says "a longer derivation of something you already have
does not change the annotation." Boolean (True ∨ (True ∧ b) = True),
Why, Lineage, Trust (max), Security (min), Tropical (min) are
absorptive. ℕ and ℕ[X] are not: each new cycle adds a new monomial
(or increments the bag count) forever.

So: you may evaluate a recursive query in How only on an acyclic
instance, or you must refuse. The checker has a 2-cycle for that.

DESIGN DECISION — refuse, do not approximate.
  A production system would switch to an absorptive semiring
  (Why, Tropical) when it sees a cycle. That is a homomorphism
  *after* you notice you cannot finish in How — it is not a
  silent truncation of the polynomial. CHOSEN: raise
  NonAbsorptiveRecursion after `max_iter` rounds that still
  change the relation. The caller who wants an answer picks K
  so that absorption holds.
"""


class NonAbsorptiveRecursion(Exception):
    """Raised when a fixpoint step still changes the relation
    after max_iter rounds.
    """


def is_absorptive(K, samples) -> bool:
    """True iff a ⊕ (a ⊗ b) = a for every pair (a, b) in samples.

    TODO: include K.zero() and K.one() in the pairs you test if
    the caller did not. Use K.eq.
    """
    raise NotImplementedError


def path_step(path, edges, K):
    """One round: path ⊕ (edges ⋈_{mid} path), projected to (src, dst).

    `path` and `edges` are Relations whose rows are
    {"src": int, "dst": int}. Join edges.dst = path.src, result
    src=edges.src, dst=path.dst.

    TODO: implement in terms of ra.join / ra.project / ra.union.
    Attribute names: use 'src','dst' on both, so you will need to
    rename before joining — or join on a temporary 'mid'. Either
    is fine; the checker only looks at the resulting (src,dst)
    annotations.
    """
    raise NotImplementedError


def reachable(edges, src: int, dst: int, K, max_iter: int = 16):
    """Least fixpoint of path, then lookup (src, dst).

    Seed: path_0 = edges.
    path_{n+1} = path_step(path_n, edges, K)
    Stop when path does not change (K.eq on every row, and same
    keys). If it still changes at max_iter, raise
    NonAbsorptiveRecursion.

    TODO: return K.zero() if (src,dst) is absent after convergence.
    """
    raise NotImplementedError
