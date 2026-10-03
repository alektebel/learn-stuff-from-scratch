"""
The parse step is a pluggable interface. That is the whole point.

LINC's premise is an LLM as the semantic parser. This repo has no
LLM: pure stdlib, no torch, and the tiny transformer in
llm-from-scratch cannot parse FOL and never will. A "faithful LINC"
that called a model would not be runnable here.

What is runnable — and the better directory — is: implement the
prover and the provenance layer exactly, make parse a protocol, and
drive it with a gold parser plus a fault injector whose taxonomy
comes from LINC's own error analysis.

    Parser.translate(premises_nl, conclusion_nl) -> Theory

    Theory = {"premises": [Formula, ...],
              "conclusion": Formula,
              "domain": [str, ...],   # gold parser fills this
              "ok": bool}             # False if the FOL is unparsable
                                      # (LINC L3 that the prover rejects)

DESIGN DECISION — the LLM is not in the deduction loop.
  Faithful CoT (Lyu et al.) is faithful *because* the chain is a
  program that is executed. Logic-LM and LINC are the same shape:
  translate, then solve. CHOSEN: deduction is the prover. The
  parser is allowed to be wrong; it is not allowed to be *consulted
  again* after it has emitted FOL. Replicability is "same parse,
  same proof." Traceability is the proof object plus the how-
  polynomial of the axioms it used.
"""

from typing import List, Protocol, Sequence


class Parser(Protocol):
    def translate(self, premises_nl: Sequence[str],
                  conclusion_nl: str) -> dict:
        ...


class GoldParser:
    """Look up the fixture by exact English. Unknown input → ok=False.

    TODO: match premises as a tuple of stripped strings against
    fixtures.problems(). Copy the gold FOL (do not return the
    fixture dict itself — the fault injector will mutate).
    """

    def translate(self, premises_nl: Sequence[str],
                  conclusion_nl: str) -> dict:
        raise NotImplementedError


def theory_ok(theory: dict) -> bool:
    """TODO: True iff theory['ok'] is True and premises + conclusion
    are tuples starting with a known constructor.
    """
    raise NotImplementedError
