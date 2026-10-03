"""
Step 6 — Evaluating attributions. Complete Solution.

Paper: ContextCite, section 4 (linear datamodeling score; top-k log-probability
drop).

The question this file answers: is a set of attribution scores any GOOD? It is
easy to produce numbers that look plausible and mean nothing, so the paper
evaluates two ways, and both are worth implementing.
"""

import math
from typing import Callable, List, Optional, Sequence, Tuple

from ablation import sample_masks
from lasso import fit_lasso, predict
from logit_probs import aggregate


def spearman(a: Sequence[float], b: Sequence[float]) -> float:
    """Rank correlation. The paper's LDS is a Spearman correlation."""
    def ranks(values: Sequence[float]) -> List[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        result = [0.0] * len(values)
        i = 0
        while i < len(order):                # average ranks within ties
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            shared = (i + j) / 2 + 1
            for k in range(i, j + 1):
                result[order[k]] = shared
            i = j + 1
        return result

    ra, rb = ranks(a), ranks(b)
    n = len(a)
    mean_a, mean_b = sum(ra) / n, sum(rb) / n
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(ra, rb))
    var_a = math.sqrt(sum((x - mean_a) ** 2 for x in ra))
    var_b = math.sqrt(sum((y - mean_b) ** 2 for y in rb))
    return cov / (var_a * var_b) if var_a > 1e-12 and var_b > 1e-12 else 0.0


def linear_datamodeling_score(citer, num_held_out: int = 64,
                              seed: int = 9_000) -> float:
    """LDS: does the surrogate predict the model on ablations it never saw?

    Fit on the training masks, then predict the true response score for a fresh
    set of random ablations and take the Spearman correlation between predicted
    and actual.

    This is the honest metric. In-sample R^2 can be driven to ~1.0 simply by
    using as many ablations as there are sources — the surrogate then has
    enough freedom to interpolate the training points and has learned nothing.
    LDS cannot be gamed that way.
    """
    X_train = [[1.0 if keep else 0.0 for keep in mask] for mask in citer.masks]
    y_train = [aggregate(row) for row in citer.logit_probs]
    weights, bias = fit_lasso(X_train, y_train, alpha=citer.alpha,
                              normalize_by=len(citer.response))

    held_out = sample_masks(citer.num_sources, num_held_out,
                            citer.keep_prob, base_seed=seed)
    token_ids = [citer.model.index[token] for token in citer.response]

    actual: List[float] = []
    for mask in held_out:
        from logit_probs import sequence_logit_probs
        ablated = citer.partitioner.build(mask)
        logits = citer.model.sequence_logits(ablated, citer.response)
        actual.append(aggregate(sequence_logit_probs(logits, token_ids)))

    X_test = [[1.0 if keep else 0.0 for keep in mask] for mask in held_out]
    return spearman(predict(X_test, weights, bias), actual)


def top_k_drop(citer, k: int = 1) -> Tuple[float, float, float]:
    """Remove the k top-scoring sources and see how far the response falls.

    Returns (full score, ablated score, drop). A large drop means the
    attribution found sources the response genuinely depended on. Compare
    against removing k RANDOM sources — that baseline is what makes the number
    meaningful.
    """
    from logit_probs import response_score

    ranked = citer.attribute()
    doomed = {a.index for a in ranked[:k]}
    mask = [i not in doomed for i in range(citer.num_sources)]

    full = response_score(citer.model, citer.context, citer.response)
    ablated = response_score(citer.model, citer.partitioner.build(mask),
                             citer.response)
    return full, ablated, full - ablated


def random_k_drop(citer, k: int = 1, trials: int = 20,
                  seed: int = 5) -> float:
    """The baseline for top_k_drop: mean drop from removing k random sources."""
    import random as _random
    from logit_probs import response_score

    rng = _random.Random(seed)
    full = response_score(citer.model, citer.context, citer.response)
    drops = []
    for _ in range(trials):
        doomed = set(rng.sample(range(citer.num_sources),
                                min(k, citer.num_sources)))
        mask = [i not in doomed for i in range(citer.num_sources)]
        ablated = response_score(citer.model, citer.partitioner.build(mask),
                                 citer.response)
        drops.append(full - ablated)
    return sum(drops) / len(drops)


def _demo() -> None:
    from contextcite import ContextCiter
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE, QUERY, ToyLM

    model = ToyLM(CONTEXT, QUERY)
    citer = ContextCiter(model, CONTEXT, QUERY)
    print(f"response: {' '.join(citer.response)}")

    print("\n=== In-sample R^2 flatters; LDS does not ===")
    print(f"{'ablations':>10}{'in-sample R^2':>16}{'held-out LDS':>15}")
    for budget in (8, 16, 32, 64, 128):
        probe = ContextCiter(model, CONTEXT, QUERY, response=citer.response,
                             num_ablations=budget)
        print(f"{budget:>10}{probe.surrogate_quality():>16.4f}"
              f"{linear_datamodeling_score(probe):>15.4f}")
    print("With 8 ablations and 8 sources the surrogate can interpolate the")
    print("training points exactly — R^2 says 0.999, LDS says what it really")
    print("knows. Always report the held-out number.")

    print("\n=== Top-k drop against a random baseline ===")
    print(f"{'k':>3}{'top-k drop':>13}{'random-k drop':>16}{'ratio':>9}")
    for k in (1, 2, 3):
        _full, _ablated, drop = top_k_drop(citer, k)
        baseline = random_k_drop(citer, k)
        ratio = drop / baseline if abs(baseline) > 1e-9 else float("inf")
        print(f"{k:>3}{drop:>13.2f}{baseline:>16.2f}{ratio:>9.1f}x")
    print("Removing the single top-scoring source hurts far more than removing")
    print("a random one. That gap IS the attribution's value; without the")
    print("baseline the raw drop would be uninterpretable.")

    print("\n=== Does it find the ground-truth source? ===")
    top = citer.attribute(top_k=1)[0]
    print(f"top-1 source:  {top.index}  (ground truth {GROUND_TRUTH_SOURCE})")
    print(f"correct: {top.index == GROUND_TRUTH_SOURCE}")
    scores = {a.index: a.score for a in citer.attribute()}
    runner_up = max(s for i, s in scores.items() if i != GROUND_TRUTH_SOURCE)
    print(f"margin over the runner-up: "
          f"{scores[GROUND_TRUTH_SOURCE] - runner_up:.2f}")

    print("\n=== A query whose answer is NOT in the context ===")
    off_topic = "What is the boiling point of mercury?"
    other_model = ToyLM(CONTEXT, off_topic)
    other = ContextCiter(other_model, CONTEXT, off_topic)
    print(f"query:    {off_topic}")
    print(f"response: {' '.join(other.response)}")
    print(f"LDS:      {linear_datamodeling_score(other):.4f}")
    for attribution in other.attribute(top_k=3):
        print(f"  {attribution}")
    print("The scores are still well-defined — the response IS grounded in the")
    print("context, it just does not answer the question. Attribution tells you")
    print("WHERE text came from, never whether it is true or responsive.")


if __name__ == "__main__":
    _demo()
