"""
LINC's error analysis, made operational.

The paper bins failures as:

    L1  implicit information loss     (Harry is a person, never said)
    L2  explicit information error    (wrong predicate, dropped 'not')
    L3  syntax                        (same symbol, two arities)

Those are *observations after the fact*. To sweep a parse-error
rate we need faults we can *inject*. Four, each named for what it
does to a formula:

    scope_invert      ∀x (P(x)→Q(x))  becomes  ∃x (P(x)→Q(x))
                      (quantifier scope inversion)
    drop_negation     ¬φ               becomes  φ
    arity_drift       P(x)             becomes  P(x, x)
                      — L3, the paper's most common syntax error
    hallucinate_const fiona            becomes  tom
                      in every constant of the formula

A fifth, implicit_drop, deletes the first premise — L1, the
information that was "obvious" and so never encoded.

DESIGN DECISION — inject on the gold FOL, not on the English.
  Corrupting the English and re-translating needs an LLM.
  Corrupting the formula is exact, seeded, and reversible.
  The sweep then has a well-defined rate: each premise is
  independently hit with probability p, with one fault kind
  chosen uniformly from the four (plus implicit_drop as its
  own kind when we test L1).
"""

from typing import List, Sequence

Formula = tuple

KINDS = (
    "scope_invert",
    "drop_negation",
    "arity_drift",
    "hallucinate_const",
    "implicit_drop",
)


def apply_fault(phi: Formula, kind: str) -> Formula:
    """Apply one fault, recursively, once — the first place it can
    fire — and return the new formula.

    TODO:
      scope_invert: the first ("forall", x, ψ) becomes ("exists", x, ψ).
        If there is no forall, return phi unchanged.
      drop_negation: the first ("not", ψ) becomes ψ. No not → unchanged.
      arity_drift: the first ("pred", n, args) becomes
        ("pred", n, args + (args[0] if args else ("const","★"),)).
      hallucinate_const: replace every ("const", c) with
        ("const", c + "_halluc"). One suffix so it is visible.
      implicit_drop: not a formula fault — raise ValueError; the
        injector handles it at the list level.
    """
    raise NotImplementedError


def bin_of(kind: str) -> str:
    """Map an operational fault to LINC's L1/L2/L3.

    TODO:
      implicit_drop                         → L1
      scope_invert, drop_negation,
        hallucinate_const                   → L2
      arity_drift                           → L3
    """
    raise NotImplementedError


class FaultyParser:
    """Wrap a Parser. After a successful gold translate, corrupt
    premises independently.

    `rate` is P(a given premise is hit). `kinds` defaults to the
    four formula faults (not implicit_drop). `rng` is
    random.Random(seed) so the sweep is replicable.

    On a hit: if kind is implicit_drop, delete that premise;
    otherwise replace it with apply_fault(premise, kind).
    If arity_drift produced a theory the prover will reject,
    set ok=False — that is L3 being *caught*, which is what
    LINC reports as an exception rather than a wrong label.
    """

    def __init__(self, inner, rate: float, rng,
                 kinds: Sequence[str] = ("scope_invert", "drop_negation",
                                         "arity_drift",
                                         "hallucinate_const")):
        self.inner = inner
        self.rate = rate
        self.rng = rng
        self.kinds = list(kinds)

    def translate(self, premises_nl: Sequence[str],
                  conclusion_nl: str) -> dict:
        raise NotImplementedError
