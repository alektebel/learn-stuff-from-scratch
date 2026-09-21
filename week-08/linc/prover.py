"""
A finite-domain propositional prover with a proof object.

After fol.ground, every formula is built from pred / not / and / or
/ implies. We saturate a set of true atoms under Horn-ish steps
and a small set of classical rules sufficient for the fixtures:

    fact P                  → P ∈ Δ
    (P → Q) and P ∈ Δ       → Q ∈ Δ          modus ponens
    ¬¬P                     → treat as P
    (P ∧ Q)                 → both
    (P ∨ Q) and ¬P ∈ Δ      → Q              disjunctive syllogism
    ¬(P → Q)                → P and ¬Q

The conclusion is
    True       if it is in Δ
    False      if its negation is in Δ
    Uncertain  otherwise

That is LINC's {True, False, Uncertain} without Prover9.

The proof object is the point:

    {"label": str,
     "steps": [{"rule": str, "derived": Formula, "from": [idx,...]}],
     "axioms": [idx, ...]}   # premise indices that were used

DESIGN DECISION — emit the proof, not just the label.
  LINC's solver returns a truth value (or throws). That is enough
  to *score* FOLIO and not enough to *trace* an answer. CHOSEN:
  every derived atom records the step that produced it. Traceability
  is walking `axioms`. Replicability is: same theory, same steps,
  because saturation is deterministic if you iterate premises in
  order and apply rules in the order above.
"""

from typing import Dict, List, Sequence

from fol import Formula


def negate(phi: Formula) -> Formula:
    """TODO: if phi is ("not", ψ) return ψ, else ("not", phi)."""
    raise NotImplementedError


def prove(premises: Sequence[Formula], conclusion: Formula,
          domain: Sequence[str]) -> Dict:
    """Ground, nnf, saturate, label.

    TODO:
      ground every premise and the conclusion over domain
      nnf them
      saturate until Δ does not grow, scanning premises in order
      look up conclusion and negate(conclusion) in Δ
      fill axioms with the *original* (pre-ground) premise indices
      that contributed to the conclusion or its negation
      if the conclusion contains a predicate of mixed arity vs the
      premises, set label="Error" — L3, LINC's exception path
    """
    raise NotImplementedError


def used_premise_indices(proof: Dict) -> List[int]:
    """TODO: sorted unique proof['axioms']."""
    raise NotImplementedError
