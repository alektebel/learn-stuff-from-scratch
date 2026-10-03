"""
Step 5 — The ContextCiter
==========================
Paper: ContextCite, section 3. Reference implementation:
context_cite/context_citer.py

Effort: medium. Mostly assembly — steps 1-4 do the work. The one design
decision that matters is what gets cached.

What you build:
  ContextCiter._compute_logit_probs -> the expensive pass, done once
  ContextCiter._fit                 -> fit the surrogate for a token span
  ContextCiter.attribute            -> ranked scores per source

Background:
  The pipeline is: partition -> ablate -> score -> regress.

  Cache the full per-token MATRIX of logit-probabilities, shape
  (num_ablations x len(response)) — not the aggregated scores. Aggregation is
  cheap and span-dependent; the model calls are expensive and span-independent.
  Cache the matrix and you can attribute any span of the response afterwards
  for free. Cache only the totals and every new span costs another 64 forward
  passes.

  That is not a micro-optimisation. Attributing individual clauses is how you
  find a poisoned sentence that whole-response attribution misses — you will
  see exactly that in applications.py.

Reading the scores:
  positive -> the source RAISED the response's logit-probability; the model
              leaned on it
  negative -> the response was likelier WITHOUT it; a distractor competing for
              probability mass
  zero     -> LASSO found no evidence either way. Stronger than "small".
"""

from typing import List, Optional, Sequence, Tuple

from ablation import DEFAULT_KEEP_PROB, DEFAULT_NUM_ABLATIONS, sample_masks
from lasso import DEFAULT_ALPHA, fit_lasso, predict, r_squared
from logit_probs import aggregate, sequence_logit_probs
from partition import ContextPartitioner


class Attribution:
    """One source's score, with its text for display."""

    __slots__ = ("index", "score", "source")

    def __init__(self, index: int, score: float, source: str):
        self.index = index
        self.score = score
        self.source = source

    def __repr__(self) -> str:
        preview = self.source[:58] + ("..." if len(self.source) > 58 else "")
        return f"[{self.index}] {self.score:+7.2f}  {preview}"


class ContextCiter:
    """Attribute a model's response to the sources in its context."""

    def __init__(self, model, context: str, query: str,
                 response: Optional[Sequence[str]] = None,
                 num_ablations: int = DEFAULT_NUM_ABLATIONS,
                 keep_prob: float = DEFAULT_KEEP_PROB,
                 alpha: float = DEFAULT_ALPHA, base_seed: int = 0):
        """TODO:
        1. Store model, context, query, alpha, keep_prob, num_ablations.
        2. self.partitioner = ContextPartitioner(context).
        3. self.response = the given response, or model.generate(context).
        4. self.masks = sample_masks(...).
        5. self._logit_probs = None — computed lazily, on first use.

        Accepting a response is what lets you compare configurations fairly:
        re-generating for each one would change the thing being attributed.
        """
        raise NotImplementedError

    @property
    def num_sources(self) -> int:
        return self.partitioner.num_sources

    @property
    def sources(self) -> List[str]:
        return self.partitioner.sources

    def _compute_logit_probs(self) -> List[List[float]]:
        """The expensive pass: num_ablations x len(response) per-token values.

        TODO: map response tokens to ids via model.index once, then for each
        mask build the ablated context, get model.sequence_logits(...), and
        convert with sequence_logit_probs.
        """
        raise NotImplementedError

    @property
    def logit_probs(self) -> List[List[float]]:
        """TODO: compute on first access, then reuse."""
        raise NotImplementedError

    def _fit(self, start: int, end: int) -> Tuple[List[float], float, float]:
        """Fit the surrogate for response tokens [start, end).

        TODO:
        1. Validate the span; raise ValueError on a bad one.
        2. X = the masks as floats.
        3. y = aggregate(row[start:end]) for each row of logit_probs — this is
           the re-aggregation that makes span attribution free.
        4. fit_lasso(X, y, alpha, normalize_by=(end - start)).
        5. Return (weights, bias, r_squared of the in-sample predictions).
        """
        raise NotImplementedError

    def attribute(self, start: Optional[int] = None, end: Optional[int] = None,
                  top_k: Optional[int] = None) -> List[Attribution]:
        """Scores for every source, highest first.

        TODO: default the span to the whole response, fit, wrap the weights in
        Attribution objects, sort by score descending, and apply top_k.
        """
        raise NotImplementedError

    def attribute_token(self, token_index: int,
                        top_k: Optional[int] = None) -> List[Attribution]:
        """TODO: attribute(token_index, token_index + 1). No new model calls."""
        raise NotImplementedError

    def surrogate_quality(self) -> float:
        """TODO: in-sample R^2 over the whole response.

        Treat this number with suspicion — evaluate.py shows why it can read
        0.999 while the surrogate has learned nothing.
        """
        raise NotImplementedError


def _demo() -> None:
    """Once implemented, verify:

    1. Whole-response attribution ranks source 4 first, at ~+40, with every
       other source between -3 and +2. In-sample R^2 ~0.99.
    2. Per-token attribution runs without further model calls. Every token here
       points at source 4 (this context has only one relevant sentence), but
       the SCORES separate: ~4.5 for 'eight', 'gpus', 'p100' against ~1.1 for
       generic words.
    3. Ablation budget: try 8, 16, 32, 64, 128. The top source should settle on
       4 immediately. Notice R^2 is HIGHEST at 8 ablations — with 8 points and
       8 coefficients the surrogate simply interpolates. That is overfitting
       wearing the costume of a good score, and it is what step 6 fixes.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
