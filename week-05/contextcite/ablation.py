"""
Step 3 — Sampling ablations
============================
Paper: ContextCite, section 3. Reference implementation: _create_mask and
_create_regression_dataset in context_cite/utils.py

Effort: small. The code is short; the design choice it encodes is the whole
reason the method works.

What you build:
  sample_mask / sample_masks -> the design matrix of the regression
  build_dataset              -> run the model once per ablation
  mask_statistics            -> sanity checks on the design

Background:
  The obvious way to measure a source's importance is to remove it and see what
  happens — leave-one-out. It costs d model calls and it is WRONG in a way that
  matters:

    If two sources both state the answer, removing either one alone changes
    nothing. Leave-one-out concludes that NEITHER matters. Both score zero,
    which is precisely backwards.

  ContextCite instead samples random subsets: each source is kept
  independently with probability 1/2. Over 64 such draws, every source is
  present in about half and absent in about half, in many different
  combinations — including the ~25% of draws where two particular sources are
  both absent. The regression then sees what happens when the answer is
  genuinely gone.

  Keep-probability 1/2 is not arbitrary: it maximises the variance of each
  column of the design matrix, and a column with no variance carries no
  information about its coefficient.

  You will prove the leave-one-out failure for real in applications.py.
"""

import random
from typing import Callable, List, Sequence, Tuple

DEFAULT_NUM_ABLATIONS = 64          # the paper's default
DEFAULT_KEEP_PROB = 0.5


def sample_mask(num_sources: int, keep_prob: float, seed: int) -> List[bool]:
    """One ablation: keep each source independently with probability keep_prob.

    TODO: use random.Random(seed) — a fresh generator per mask, not one shared
    generator advanced across masks. Per-mask seeding means you can reproduce
    ablation 37 on its own when its score looks wrong.
    """
    raise NotImplementedError


def sample_masks(num_sources: int, num_ablations: int = DEFAULT_NUM_ABLATIONS,
                 keep_prob: float = DEFAULT_KEEP_PROB,
                 base_seed: int = 0) -> List[List[bool]]:
    """TODO: num_ablations masks, seeded base_seed + i."""
    raise NotImplementedError


def build_dataset(partitioner, model, response: Sequence[str],
                  masks: Sequence[Sequence[bool]],
                  score_fn: Callable) -> Tuple[List[List[float]], List[float]]:
    """Run the model once per ablation. Returns (X, y).

    TODO: for each mask, build the ablated context, append the mask as floats
    to X, and append score_fn(model, context, response) to y.

    This is the only expensive part of ContextCite: n forward passes, n = 64 by
    default. Everything after it is a regression on a matrix you could print.
    """
    raise NotImplementedError


def mask_statistics(masks: Sequence[Sequence[bool]]) -> dict:
    """Sanity checks on the design matrix.

    TODO: return num_masks, num_sources, mean kept per mask, min/max times each
    source was kept, and lists of always_on / always_off source indices.

    always_on and always_off must both be EMPTY. A source that was never
    ablated (or never kept) has a constant column, and no regression can
    identify a coefficient from a constant. With 64 draws at p=1/2 this is
    vanishingly unlikely — but check, because the failure is silent.
    """
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, verify:

    1. Print the first 8 masks as 1s and dots. They should look random, with
       roughly half the sources kept in each.
    2. mean_kept_per_mask ~= num_sources / 2, and each source kept somewhere
       around 32 of 64 times. always_on and always_off both empty.
    3. Build the real dataset. Split y by whether source 4 was kept: the mean
       score should be around -35 with it and -76 without. That difference is
       the signal the regression will extract — for all sources at once.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
