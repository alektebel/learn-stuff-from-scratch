"""
Step 3 — Sampling ablations and building the regression dataset. Complete Solution.

Paper: ContextCite, section 3. Reference implementation: _create_mask and
_create_regression_dataset in context_cite/utils.py.
"""

import random
from typing import Callable, List, Sequence, Tuple

DEFAULT_NUM_ABLATIONS = 64          # the paper's default
DEFAULT_KEEP_PROB = 0.5             # each source kept independently, p = 1/2


def sample_mask(num_sources: int, keep_prob: float, seed: int) -> List[bool]:
    """One ablation: keep each source independently with probability keep_prob.

    Seeding per-mask (rather than once for the whole run) makes any individual
    ablation reproducible on its own, which matters when you are chasing down
    one anomalous row of the regression.
    """
    rng = random.Random(seed)
    return [rng.random() < keep_prob for _ in range(num_sources)]


def sample_masks(num_sources: int, num_ablations: int = DEFAULT_NUM_ABLATIONS,
                 keep_prob: float = DEFAULT_KEEP_PROB,
                 base_seed: int = 0) -> List[List[bool]]:
    """The design matrix of the regression: num_ablations x num_sources.

    Why random subsets rather than dropping one source at a time:

      - Leave-one-out costs d model calls and misses every interaction. If two
        sources both state the answer, removing either alone changes nothing,
        and leave-one-out concludes neither matters. Both get a score of zero,
        which is exactly backwards.
      - Random subsets at p = 1/2 vary every source over many contexts at once,
        so a fixed budget of n calls estimates all d effects rather than one.

    keep_prob = 1/2 maximises the variance of each column, which is what the
    regression needs to identify a coefficient.
    """
    return [sample_mask(num_sources, keep_prob, base_seed + i)
            for i in range(num_ablations)]


def build_dataset(partitioner, model, response: Sequence[str],
                  masks: Sequence[Sequence[bool]],
                  score_fn: Callable) -> Tuple[List[List[float]], List[float]]:
    """Run the model once per ablation. Returns (X, y) for the regression.

    X is the mask matrix as floats; y is the response score under each ablated
    context. This is the only expensive part of ContextCite — n forward passes
    over the response, with n = 64 by default. Everything after it is a
    regression over a matrix small enough to fit on screen.
    """
    X: List[List[float]] = []
    y: List[float] = []
    for mask in masks:
        context = partitioner.build(mask)
        X.append([1.0 if keep else 0.0 for keep in mask])
        y.append(score_fn(model, context, response))
    return X, y


def mask_statistics(masks: Sequence[Sequence[bool]]) -> dict:
    """Sanity checks on the design. A degenerate column cannot be attributed."""
    if not masks:
        return {"num_masks": 0}
    num_sources = len(masks[0])
    kept = [sum(1 for mask in masks if mask[i]) for i in range(num_sources)]
    return {
        "num_masks": len(masks),
        "num_sources": num_sources,
        "mean_kept_per_mask": sum(sum(m) for m in masks) / len(masks),
        "min_kept_per_source": min(kept),
        "max_kept_per_source": max(kept),
        "always_on": [i for i, k in enumerate(kept) if k == len(masks)],
        "always_off": [i for i, k in enumerate(kept) if k == 0],
    }


def _demo() -> None:
    from logit_probs import response_score
    from partition import ContextPartitioner
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE, QUERY, ToyLM

    partitioner = ContextPartitioner(CONTEXT)
    masks = sample_masks(partitioner.num_sources, num_ablations=64)

    print("=== The design matrix ===")
    print(f"{len(masks)} ablations x {partitioner.num_sources} sources")
    print("first 8 rows (1 = source kept, . = ablated away):")
    for mask in masks[:8]:
        print("   " + "".join("1" if keep else "." for keep in mask))

    stats = mask_statistics(masks)
    print(f"\nmean sources kept per ablation: {stats['mean_kept_per_mask']:.2f} "
          f"of {stats['num_sources']} (expected {stats['num_sources'] * 0.5:.1f})")
    print(f"each source kept between {stats['min_kept_per_source']} and "
          f"{stats['max_kept_per_source']} times of {len(masks)}")
    print(f"degenerate columns: always-on {stats['always_on']}, "
          f"always-off {stats['always_off']} (both must be empty)")

    print("\n=== Running the model over the ablations ===")
    model = ToyLM(CONTEXT, QUERY)
    response = model.generate(CONTEXT)
    X, y = build_dataset(partitioner, model, response, masks, response_score)
    print(f"X is {len(X)}x{len(X[0])}, y has {len(y)} entries")
    print(f"y ranges from {min(y):.1f} to {max(y):.1f}")

    with_source = [score for row, score in zip(X, y) if row[GROUND_TRUTH_SOURCE]]
    without = [score for row, score in zip(X, y) if not row[GROUND_TRUTH_SOURCE]]
    print(f"\nmean score WITH source {GROUND_TRUTH_SOURCE}:    "
          f"{sum(with_source) / len(with_source):>8.2f}  ({len(with_source)} ablations)")
    print(f"mean score WITHOUT source {GROUND_TRUTH_SOURCE}: "
          f"{sum(without) / len(without):>8.2f}  ({len(without)} ablations)")
    print("The regression's job is to find that difference for every source at")
    print("once, including sources whose effect only shows up in combination.")

    print("\n=== Why not leave-one-out? ===")
    print("Suppose two sources both contain the answer. Removing either alone")
    print("changes nothing, so leave-one-out scores BOTH as irrelevant. Random")
    print("subsets ablate them together often enough to see the truth — this is")
    print("demonstrated for real in applications.py.")


if __name__ == "__main__":
    _demo()
