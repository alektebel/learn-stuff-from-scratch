"""
Step 5 — The ContextCiter. Complete Solution.

Paper: ContextCite, section 3. Reference implementation:
context_cite/context_citer.py.

Ties together the four previous steps:
    partition -> ablate -> score -> regress
"""

from typing import List, Optional, Sequence, Tuple

from ablation import DEFAULT_KEEP_PROB, DEFAULT_NUM_ABLATIONS, sample_masks
from lasso import DEFAULT_ALPHA, fit_lasso, predict, r_squared
from logit_probs import aggregate, sequence_logit_probs
from partition import ContextPartitioner


class Attribution:
    """One source's score, with the source text for display."""

    __slots__ = ("index", "score", "source")

    def __init__(self, index: int, score: float, source: str):
        self.index = index
        self.score = score
        self.source = source

    def __repr__(self) -> str:
        preview = self.source[:58] + ("..." if len(self.source) > 58 else "")
        return f"[{self.index}] {self.score:+7.2f}  {preview}"


class ContextCiter:
    """Attribute a model's response to the sources in its context.

    The expensive work — one forward pass per ablation — happens once, lazily,
    and is cached as a matrix of per-token logit-probabilities. Attributing a
    different span of the response afterwards is only a re-aggregation and a
    refit, costing no further model calls. That is what makes it practical to
    ask "where did THIS clause come from" sentence by sentence.
    """

    def __init__(self, model, context: str, query: str,
                 response: Optional[Sequence[str]] = None,
                 num_ablations: int = DEFAULT_NUM_ABLATIONS,
                 keep_prob: float = DEFAULT_KEEP_PROB,
                 alpha: float = DEFAULT_ALPHA, base_seed: int = 0):
        self.model = model
        self.context = context
        self.query = query
        self.partitioner = ContextPartitioner(context)
        self.num_ablations = num_ablations
        self.keep_prob = keep_prob
        self.alpha = alpha

        self.response: List[str] = (list(response) if response is not None
                                    else model.generate(context))
        self.masks = sample_masks(self.num_sources, num_ablations,
                                  keep_prob, base_seed)
        self._logit_probs: Optional[List[List[float]]] = None

    @property
    def num_sources(self) -> int:
        return self.partitioner.num_sources

    @property
    def sources(self) -> List[str]:
        return self.partitioner.sources

    # -- the expensive part, done once --------------------------------------

    def _compute_logit_probs(self) -> List[List[float]]:
        """num_ablations x len(response) per-token logit-probabilities."""
        token_ids = [self.model.index[token] for token in self.response]
        matrix: List[List[float]] = []
        for mask in self.masks:
            ablated = self.partitioner.build(mask)
            logits = self.model.sequence_logits(ablated, self.response)
            matrix.append(sequence_logit_probs(logits, token_ids))
        return matrix

    @property
    def logit_probs(self) -> List[List[float]]:
        if self._logit_probs is None:
            self._logit_probs = self._compute_logit_probs()
        return self._logit_probs

    # -- attribution --------------------------------------------------------

    def _fit(self, start: int, end: int) -> Tuple[List[float], float, float]:
        """Fit the surrogate for response tokens [start, end)."""
        if not 0 <= start < end <= len(self.response):
            raise ValueError(f"bad span [{start}, {end}) for a "
                             f"{len(self.response)}-token response")

        X = [[1.0 if keep else 0.0 for keep in mask] for mask in self.masks]
        y = [aggregate(row[start:end]) for row in self.logit_probs]

        weights, bias = fit_lasso(X, y, alpha=self.alpha,
                                  normalize_by=(end - start))
        return weights, bias, r_squared(y, predict(X, weights, bias))

    def attribute(self, start: Optional[int] = None, end: Optional[int] = None,
                  top_k: Optional[int] = None) -> List[Attribution]:
        """Scores for every source, highest first.

        A positive score means the source RAISED the logit-probability of the
        response: the model leaned on it. A negative score means the response
        became likelier without it — a distractor. Zero means the LASSO found
        no evidence either way, which is a stronger statement than "small".
        """
        start = 0 if start is None else start
        end = len(self.response) if end is None else end
        weights, _bias, _r2 = self._fit(start, end)

        ranked = sorted(
            (Attribution(i, w, self.partitioner.source(i))
             for i, w in enumerate(weights)),
            key=lambda a: a.score, reverse=True)
        return ranked[:top_k] if top_k else ranked

    def attribute_token(self, token_index: int,
                        top_k: Optional[int] = None) -> List[Attribution]:
        """Where did this one response token come from? No extra model calls."""
        return self.attribute(token_index, token_index + 1, top_k=top_k)

    def surrogate_quality(self) -> float:
        """In-sample R^2. See evaluate.py for the honest held-out version."""
        return self._fit(0, len(self.response))[2]

    def __repr__(self) -> str:
        return (f"<ContextCiter {self.num_sources} sources, "
                f"{len(self.response)} response tokens, "
                f"{self.num_ablations} ablations>")


def _demo() -> None:
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE, QUERY, ToyLM

    model = ToyLM(CONTEXT, QUERY)
    citer = ContextCiter(model, CONTEXT, QUERY)
    print(citer)
    print(f"query:    {QUERY}")
    print(f"response: {' '.join(citer.response)}")

    print("\n=== Attributing the whole response ===")
    for attribution in citer.attribute():
        marker = " <- ground truth" if attribution.index == GROUND_TRUTH_SOURCE else ""
        print(f"  {attribution}{marker}")

    top = citer.attribute(top_k=1)[0]
    print(f"\ntop source is {top.index}, ground truth is {GROUND_TRUTH_SOURCE}: "
          f"{'CORRECT' if top.index == GROUND_TRUTH_SOURCE else 'WRONG'}")
    print(f"in-sample surrogate R^2: {citer.surrogate_quality():.4f}")

    print("\n=== Attributing individual tokens (no extra model calls) ===")
    print(f"{'token':<16}{'top source':>12}{'score':>10}")
    for index, token in enumerate(citer.response):
        best = citer.attribute_token(index, top_k=1)[0]
        flag = " *" if best.index == GROUND_TRUTH_SOURCE else ""
        print(f"{token:<16}{best.index:>12}{best.score:>10.2f}{flag}")
    print("\nEvery token points at source 4 here, because this context has only")
    print("one sentence relevant to the query. Read the MAGNITUDES: the answer")
    print("tokens ('eight', 'gpus', 'p100') score ~4.5 while generic ones")
    print("('transformer', 'translation') score ~1.1.")
    print("Give the context two competing sentences and the top source varies")
    print("per token — applications.py section 3 shows exactly that, and shows")
    print("why it matters: whole-response attribution MISSES a poisoned claim")
    print("that per-token and span attribution both catch.")

    print("\n=== Ablation budget vs stability ===")
    print(f"{'ablations':>10}{'top source':>12}{'score':>10}{'R^2':>9}")
    for budget in (8, 16, 32, 64, 128):
        probe = ContextCiter(model, CONTEXT, QUERY, response=citer.response,
                             num_ablations=budget)
        best = probe.attribute(top_k=1)[0]
        print(f"{budget:>10}{best.index:>12}{best.score:>10.2f}"
              f"{probe.surrogate_quality():>9.4f}")
    print("More ablations cost linearly and buy a steadier estimate. The paper")
    print("defaults to 64; note how few are needed here for the ranking to")
    print("settle, and that R^2 near 1.0 on 8 ablations is overfitting, not")
    print("skill — 8 points cannot pin down 8 coefficients honestly.")


if __name__ == "__main__":
    _demo()
