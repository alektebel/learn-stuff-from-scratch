# ContextCite From Scratch — Solutions

Complete, runnable implementations of every template in the parent directory. Pure
Python 3 standard library — no numpy, no sklearn, no torch. The whole directory runs in
about a second.

```bash
python3 toy_lm.py         # the provided model and the running example
python3 partition.py      # sources and ablated contexts
python3 logit_probs.py    # the regression target
python3 ablation.py       # the design matrix
python3 lasso.py          # the surrogate
python3 contextcite.py    # attribution, end to end
python3 evaluate.py       # LDS vs in-sample R²
python3 applications.py   # verification, pruning, poisoning, leave-one-out
```

Files import each other by name, so run them from inside this directory.

## What each file demonstrates

### `toy_lm.py` — provided, not an exercise

A context-grounded bag-of-words language model. Scores each vocabulary word by its
frequency in the context, weighting each sentence by overlap with the query. Fixed
vocabulary (built from the *full* context, so ablation never changes it) and fully
deterministic.

The running example mirrors the one in the reference repo's README: an "Attention Is All
You Need" abstract, the query *"What type of GPUs were used for training?"*, and exactly
one sentence — index 4 — naming the P100 GPUs. That index is `GROUND_TRUTH_SOURCE`, and
it is what the checker and the evaluation measure against.

```
response with the full context:  ... eight gpus hours p100
response WITHOUT that sentence:  models attention based english mechanisms ...
```

### `partition.py`

`split_text` (sentences + separators) and `ContextPartitioner.build(mask)`.

`build()` with an all-True mask reproduces the 849-character context byte for byte.
Ablating source 4 removes `P100` and shortens it to 720 characters.

### `logit_probs.py`

The regression target. `token_logit_prob` computes `z[y] − logsumexp(z[≠y])` directly
from logits and agrees with `log(p/(1−p))` to 0.00e+00 on ordinary inputs — while
staying finite on `[40, 0, 0]`, where the softmax route gives `p == 1.0` exactly.

Leave-one-out scores under the toy model:

```
full context              -38.70
without source 4          -75.60   (drop 36.90)   <- the answer
every other source        ~-37.7   (drop ~ -1)    <- distractors
```

Several drops are *negative*: the response gets likelier without those sentences,
because they compete for probability mass.

### `ablation.py`

Mask sampling at `p=0.5`, plus `mask_statistics` to catch degenerate columns. Over 64
draws each source is kept 29–37 times, mean 4.06 sources kept per ablation of 8.

```
mean score WITH source 4:     -34.91  (32 ablations)
mean score WITHOUT source 4:  -75.84  (32 ablations)
```

### `lasso.py`

Coordinate descent matching scikit-learn's objective, with standardisation and the
un-standardising step that returns coefficients in raw units.

Recovering a known sparse signal from 200 samples:

```
  j     true    fitted
  0     3.00     2.986
  3    -2.00    -1.968
  6     0.50     0.479
  rest  0.00     0.000   (exactly zero, not merely small)
```

And the alpha sweep, which is the argument for L1:

```
 alpha  nonzero    R²
   0.0        8  0.999    <- plain least squares, nothing zeroed
  0.01        3  0.999    <- the paper's setting
   0.5        2  0.828
   2.0        0  0.000    <- everything crushed
```

### `contextcite.py`

The `ContextCiter`. Caches the per-token logit-probability matrix, so span attribution
costs **zero** extra model calls.

```
[4]  +40.47  The Transformer can reach a new state of the art ...  <- ground truth
[2]   +1.28  Experiments on two machine translation tasks ...
[5]   -2.36  Recurrent models typically factor computation ...
in-sample R²: 0.9888
```

Per-token scores separate cleanly by magnitude: `eight`, `gpus`, `p100` at ~4.5 against
`transformer`, `translation` at ~1.1.

### `evaluate.py`

LDS and top-k drop. The headline table:

```
 ablations   in-sample R²   held-out LDS
         8         0.9993         0.7586
        64         0.9888         0.9355
```

R² is *highest* where the estimate is *worst* — with 8 sources and 8 ablations the
surrogate interpolates its training points. That is the entire reason the paper reports
LDS.

Top-k drop against the random baseline: **12.9x** at k=1.

The last section runs an off-topic query. Scores stay well-defined and LDS stays at
0.83, because the response *is* grounded in the context — it just does not answer the
question. Attribution finds provenance, never truth or relevance.

### `applications.py`

Four experiments.

**Pruning** — keeping only source 4 (16% of the characters) *raises* the response score,
because the other seven sentences were competing for probability mass.

**Poisoning** — the interesting one:

```
clean response:     transformer translation ... eight gpus hours p100
poisoned response:  gpus h200 training only transformer translation ...

whole-response attribution -> source 5, MISSES the poison at 2
per-token: tokens 0-3      -> source 2  (the poison)
span [0, 4)                -> source 2 at +20.90, everything else ~0  DETECTED
```

Whole-response attribution is outvoted by the eight untouched tokens. Attributing the
*span that makes the claim* isolates the injection. This is why the paper supports
arbitrary spans — and why step 5's caching decision matters, since those refits are free.

**Leave-one-out fails** — duplicate the answer sentence so it appears twice:

```
 source   leave-one-out   ContextCite
      4            3.84         20.92   <- a copy
      8            3.84         21.61   <- a copy
```

Remove one copy and the other still answers the query, so leave-one-out sees almost
nothing. Random subsets remove both in ~25% of draws. This is the whole argument for the
sampling design.

## Implementation notes

- **The vocabulary is fixed at construction** from the full context. If ablation changed
  the vocabulary, logits from different ablations would not be comparable.
- **`token_logit_prob` works from logits, never from a softmax.** `p` rounds to 1.0 for
  a merely-confident token, making `1−p` exactly zero.
- **`aggregate` uses `log1p(-exp(log_p))`**, since the argument is tiny whenever the
  model is confident, and returns `inf` in the degenerate case rather than dividing by
  zero.
- **`log_sigmoid` branches on the sign**; a single-branch version overflows for large
  negative input.
- **`standardize` forces scale 1.0 on a constant column.** It then becomes all zeros
  after centring and the solver correctly assigns it a coefficient of 0.
- **The coordinate-descent residual is updated incrementally**, not recomputed — that is
  O(n·d) per sweep instead of O(n·d²).
- **`ContextCiter` caches the per-token matrix, not aggregated scores.** Span
  attribution is then a re-aggregation and a refit, with no model calls. The checker
  asserts this by counting calls.
- **`linear_datamodeling_score` draws held-out masks with a different `base_seed`.**
  Reusing the training seed silently makes the metric in-sample and meaningless.
- **The poison had to be designed to actually work.** A first attempt that said "ignore
  all other sources..." changed nothing — the model simply did not rate it relevant.
  The version used repeats the query's own terms so the model attends to it. An attack
  that fails makes the detection question meaningless.
