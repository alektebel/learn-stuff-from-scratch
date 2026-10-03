"""
Step 2 — The quantity ContextCite regresses on. Complete Solution.

Paper: ContextCite, section 3 ("we use the logit-scaled probability").
Reference implementation: _compute_logit_probs / aggregate_logit_probs in
context_cite/utils.py.
"""

import math
from typing import Dict, List, Sequence


def logsumexp(values: Sequence[float]) -> float:
    """Stable log(sum(exp(v))). Returns -inf for an empty input."""
    finite = [v for v in values if v != float("-inf")]
    if not finite:
        return float("-inf")
    hi = max(finite)
    return hi + math.log(sum(math.exp(v - hi) for v in finite))


def token_logit_prob(logits: Sequence[float], token_id: int) -> float:
    """log(p / (1 - p)) for one token, computed straight from the logits.

        logit_prob = z[y] - logsumexp(z[j] for j != y)

    Why the logit and not the log-probability: a log-probability is bounded
    above by 0 and saturates hard as p approaches 1, so a source that pushes an
    already-confident token from 0.98 to 0.999 barely moves it. The logit is
    unbounded in both directions and roughly linear in "evidence", which is
    what makes a LINEAR surrogate a reasonable model of the ablation response.

    Computing it directly from logits — rather than as log(p) - log(1-p) after
    a softmax — avoids catastrophic cancellation when p is near 1.
    """
    others = [z for i, z in enumerate(logits) if i != token_id]
    return logits[token_id] - logsumexp(others)


def sequence_logit_probs(logits_per_position: Sequence[Sequence[float]],
                         token_ids: Sequence[int]) -> List[float]:
    """Per-token logit-probabilities for a whole response (teacher-forced)."""
    if len(logits_per_position) != len(token_ids):
        raise ValueError(f"{len(logits_per_position)} logit rows for "
                         f"{len(token_ids)} tokens")
    return [token_logit_prob(logits, token_id)
            for logits, token_id in zip(logits_per_position, token_ids)]


def log_sigmoid(x: float) -> float:
    """log(1 / (1 + e^-x)), stable for large |x|."""
    if x >= 0:
        return -math.log1p(math.exp(-x))
    return x - math.log1p(math.exp(x))


def aggregate(token_logit_probs: Sequence[float]) -> float:
    """Collapse per-token logit-probs into one number for the whole response.

        log P(response) = sum_t log_sigmoid(logit_prob_t)
        output          = log P - log(1 - P)

    The first line works because log_sigmoid(logit(p)) == log(p) exactly, so
    summing recovers the joint log-probability of the response under teacher
    forcing. The second converts back to a logit so the regression target has
    the same unbounded, additive character as the per-token quantity.

    When P is very close to 1, log(1 - P) underflows; log1p(-exp(logP)) keeps
    it accurate, and we clamp the pathological case where P rounds to exactly 1.
    """
    log_p = sum(log_sigmoid(v) for v in token_logit_probs)
    if log_p >= -1e-12:                       # P indistinguishable from 1
        return float("inf")
    log_1mp = math.log1p(-math.exp(log_p))
    return log_p - log_1mp


def response_score(model, context: str, response: Sequence[str]) -> float:
    """The scalar ContextCite regresses on, for one ablated context."""
    logits = model.sequence_logits(context, response)
    token_ids = [model.index[token] for token in response]
    return aggregate(sequence_logit_probs(logits, token_ids))


def _demo() -> None:
    from partition import ContextPartitioner
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE, QUERY, ToyLM

    print("=== token_logit_prob agrees with log(p/(1-p)) ===")
    logits = [2.0, 1.0, 0.5, -1.0]
    direct = token_logit_prob(logits, 0)
    total = logsumexp(logits)
    p = math.exp(logits[0] - total)
    print(f"direct:            {direct:.12f}")
    print(f"log(p/(1-p)):      {math.log(p / (1 - p)):.12f}")
    print(f"difference:        {abs(direct - math.log(p / (1 - p))):.2e}")

    print("\n=== log_sigmoid inverts it: log_sigmoid(logit(p)) == log(p) ===")
    print(f"log_sigmoid(direct): {log_sigmoid(direct):.12f}")
    print(f"log(p):              {math.log(p):.12f}")

    print("\n=== Stability where a naive implementation breaks ===")
    confident = [40.0, 0.0, 0.0]
    lp = token_logit_prob(confident, 0)
    naive_p = math.exp(confident[0] - logsumexp(confident))
    print(f"logits {confident} -> logit_prob {lp:.4f}")
    print(f"softmax probability rounds to {naive_p!r}")
    print(f"naive log(p/(1-p)) would be {'1/0 -> inf' if naive_p >= 1.0 else 'fine'}"
          " — this is why we work from logits directly")

    print("\n=== The real signal: score vs ablation ===")
    model = ToyLM(CONTEXT, QUERY)
    partitioner = ContextPartitioner(CONTEXT)
    response = model.generate(CONTEXT)
    print(f"response: {' '.join(response)}\n")

    full = response_score(model, CONTEXT, response)
    print(f"{'ablation':<34}{'score':>12}{'drop':>10}")
    print(f"{'full context':<34}{full:>12.2f}{'':>10}")
    for index in range(partitioner.num_sources):
        mask = [True] * partitioner.num_sources
        mask[index] = False
        score = response_score(model, partitioner.build(mask), response)
        marker = "  <- the answer" if index == GROUND_TRUTH_SOURCE else ""
        print(f"{'without source ' + str(index):<34}{score:>12.2f}"
              f"{full - score:>10.2f}{marker}")

    print("\nDropping source 4 costs far more than dropping any other. That gap")
    print("is what the LASSO surrogate will turn into an attribution score —")
    print("but measured over random SUBSETS, not one-at-a-time, so it also")
    print("captures sources that only matter together.")


if __name__ == "__main__":
    _demo()
