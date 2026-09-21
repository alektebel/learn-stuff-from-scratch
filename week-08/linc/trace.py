"""
Hang a how-polynomial on the proof.

Each original premise is a tuple id p0, p1, p2, ...
A proof that used premises 0 and 2 is the monomial p0 p2.
Two different proofs of the same label would be a sum; the
fixtures have one.

Then the homomorphism from provenance-semirings gives you
lineage (which premises), bag (how many proofs), trust (if
you ever score parses) — without re-proving.

This is what "the output of an LLM is fully traceable" means
in this repo:

    English
      → (untrusted) parse
      → (deterministic) proof
      → (free) how-polynomial
      → any later question is specialize()

Do ../provenance-semirings/ first. This file imports it.

DESIGN DECISION — annotate premises, not English sentences.
  ContextCite attributes tokens. That is a different question
  (which words moved the logit). Here the LLM has already been
  reduced to a parse; the thing worth tracing is which *axioms
  the prover used*. If you attribute the English you are
  answering ContextCite again. CHOSEN: premise indices.
"""

from typing import Any, Dict, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent
                       / "provenance-semirings"))


def how_of(proof: Dict):
    """ℕ[X] polynomial of the proof.

    TODO: import polynomial.variable / mul / add / one.
    Start from one(); for each idx in used_premise_indices(proof)
    multiply by variable(f"p{idx}").
    An Error / empty-axioms proof is zero() — nothing derived.
    """
    raise NotImplementedError


def lineage_of(proof: Dict) -> frozenset:
    """TODO: specialize how_of(proof) through Lineage, or
    equivalently {f"p{i}" for i in axioms}. Prefer specialize
    so the last check actually uses the homomorphism.
    """
    raise NotImplementedError


def faithful(proof: Dict, gold_axioms: List[int]) -> bool:
    """True iff the proof used *exactly* the gold axiom set.

    Right label, extra axiom: not faithful (Privilege Illusion,
    you have already seen this in distill.py).
    Right label, missing axiom: not faithful (the prover
    guessed, or a fault dropped a premise that was on the path
    and something else filled in — it didn't).
    """
    raise NotImplementedError
