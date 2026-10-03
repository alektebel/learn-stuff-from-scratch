"""
LINC / Logic-LM / Faithful CoT, as one function.

    theory = parser.translate(premises_nl, conclusion_nl)
    if not theory["ok"]:
        return {"label": "Error", ...}      # L3, majority-vote would drop
    proof = prove(theory["premises"], theory["conclusion"], theory["domain"])
    return proof + {"theory": theory}

The parser is an argument. GoldParser on the fixtures is 3/3.
FaultyParser is how the answer becomes *un*-faithful: the prover
is still deterministic, the parse is not the gold.

DESIGN DECISION — no majority vote in the default pipeline.
  LINC's third stage (vote across samples) hides parse variance.
  The thing we are here to measure is how parse error rate moves
  the label. CHOSEN: one parse, one proof. Vote lives in
  sweep.voted() as an optional comparison, so you can see LINC's
  own mitigation against the thing you just measured.
"""

from typing import Dict, Sequence


def run(parser, premises_nl: Sequence[str],
        conclusion_nl: str) -> Dict:
    """TODO: the three lines in the module docstring.
    Always include "theory" on the result so sweep can see ok.
    """
    raise NotImplementedError


def voted(parser_factory, premises_nl: Sequence[str],
          conclusion_nl: str, n: int) -> Dict:
    """Run `n` times. parser_factory() returns a *fresh* parser
    (FaultyParser with the next rng state, or just GoldParser).

    TODO: among results whose label is in {True, False, Uncertain},
    majority vote. Ties → "Uncertain". Errors do not vote (LINC
    drops syntax failures). Return
      {"label": str, "votes": {label: count}, "n_ok": int}
    """
    raise NotImplementedError
