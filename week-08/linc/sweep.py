"""
Sweep the parse error rate.

For p in {0, 0.25, 0.5, 1.0}, build a FaultyParser(GoldParser(), p, rng)
and run every fixture. Accuracy = fraction of problems whose label
matches the gold label. Errors count as wrong.

The plot you write in the journal is this table. Predict it first:
p=0 is 1.0 (gold parser). p=1.0 is near 0 on p1 (every premise is
corrupted; Fiona no longer drinks). Monotonicity is the lesson —
if accuracy *rises* with p, the injector is not hitting the
critical path, or the prover is ignoring the premises.

DESIGN DECISION — accuracy against the gold *label*, not against
  the gold *parse*.
  A corrupted parse that still entails the right thing is a lucky
  fault (dropping an unused premise). Counting it as a win is
  honest: LINC scores labels, not formulas. The provenance check
  in trace.py is what catches "right answer, wrong reasons."
"""

from typing import Dict, List, Sequence


def accuracy(parser, problems: Sequence[dict]) -> float:
    """TODO: run pipeline.run on each problem; mean of
    (result['label'] == problem['label']).
    """
    raise NotImplementedError


def sweep(rates: Sequence[float], seed: int = 0) -> List[Dict]:
    """TODO: for each rate, FaultyParser(GoldParser(), rate,
    random.Random(seed + int(1000*rate))), accuracy on
    fixtures.problems(). Return
      [{"rate": p, "accuracy": a}, ...] in the same order as rates.
    """
    raise NotImplementedError


def is_monotone(rows: Sequence[Dict]) -> bool:
    """True iff accuracy is non-increasing as rate increases.

    TODO: allow equality. Floating noise of 1e-9 is fine.
    """
    raise NotImplementedError
