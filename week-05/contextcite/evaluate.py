"""
Step 6 — Evaluating attributions
=================================
Paper: ContextCite, section 4 (linear datamodeling score; top-k drop).

Effort: medium. The honesty step — it is what tells you whether the scores from
step 5 mean anything at all.

What you build:
  spearman                 -> rank correlation, ties averaged
  linear_datamodeling_score-> the paper's LDS, on HELD-OUT ablations
  top_k_drop / random_k_drop -> a counterfactual check and its baseline

Background:
  It is easy to produce attribution scores that look plausible and mean
  nothing. Two independent checks:

  LDS (linear datamodeling score). Fit the surrogate on the training masks,
  then draw a FRESH set of random ablations, predict their scores, and take the
  Spearman correlation with what the model actually does. This cannot be gamed
  by giving the surrogate more freedom — which in-sample R^2 very much can. With
  8 sources and 8 ablations, R^2 goes to ~0.999 because the surrogate can
  interpolate all 8 points exactly. LDS will tell you it knows far less.

  Top-k drop. Remove the k highest-scoring sources and measure how far the
  response's score falls. On its own the number is uninterpretable — you need
  the baseline of removing k RANDOM sources. The ratio is the real result.
"""

import math
from typing import Callable, List, Optional, Sequence, Tuple

from ablation import sample_masks
from lasso import fit_lasso, predict
from logit_probs import aggregate


def spearman(a: Sequence[float], b: Sequence[float]) -> float:
    """Rank correlation.

    TODO:
    1. Convert both to ranks, averaging ranks within ties. (Ties are common
       here because LASSO produces exact zeros.)
    2. Pearson correlation of the two rank vectors.
    3. Return 0.0 if either has no variance.
    """
    raise NotImplementedError


def linear_datamodeling_score(citer, num_held_out: int = 64,
                              seed: int = 9_000) -> float:
    """Does the surrogate predict the model on ablations it never saw?

    TODO:
    1. Fit on the citer's training masks and aggregated scores.
    2. Draw num_held_out fresh masks with a DIFFERENT base_seed — reusing the
       training seed silently makes this in-sample again and the number
       meaningless.
    3. For each, run the model on the ablated context and aggregate the true
       score.
    4. Return spearman(predicted, actual).
    """
    raise NotImplementedError


def top_k_drop(citer, k: int = 1) -> Tuple[float, float, float]:
    """Remove the k top-scoring sources; return (full, ablated, drop).

    TODO: take the top-k indices from citer.attribute(), build the mask that
    excludes them, and score the response with and without.
    """
    raise NotImplementedError


def random_k_drop(citer, k: int = 1, trials: int = 20, seed: int = 5) -> float:
    """The baseline: mean drop from removing k RANDOM sources.

    TODO: average top_k_drop's measurement over `trials` random choices of k
    sources. Without this number, a raw drop of "36.9" says nothing.
    """
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, produce and explain:

    1. A table of in-sample R^2 against held-out LDS for 8/16/32/64/128
       ablations. Expect roughly:
           8   ablations -> R^2 0.999, LDS 0.76
           64  ablations -> R^2 0.989, LDS 0.94
       R^2 goes DOWN as the estimate gets better. Understand why before moving
       on, and report LDS from then on.
    2. Top-k drop against the random baseline for k = 1, 2, 3. Removing the top
       source should hurt roughly 13x more than removing a random one.
    3. The ground-truth check: top-1 source == 4, with a margin of ~39 over the
       runner-up.
    4. An off-topic query ("What is the boiling point of mercury?"). The scores
       stay well-defined and the LDS stays high — because the response IS
       grounded in the context, it just does not answer the question.
       Attribution tells you WHERE text came from. Never whether it is true,
       and never whether it is responsive.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
