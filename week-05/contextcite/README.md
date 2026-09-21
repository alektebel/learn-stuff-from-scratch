# ContextCite From Scratch

Replicate **ContextCite** — the NeurIPS 2024 paper on context attribution — in pure
Python, one small step at a time.

> **Cohen-Wang, Shah, Georgiev, Mądry. "ContextCite: Attributing Model Generation to
> Context." NeurIPS 2024.**
> [paper](https://arxiv.org/abs/2409.00729) ·
> [blog](https://gradientscience.org/contextcite/) ·
> [reference code](https://github.com/MadryLab/context-cite)

## What the paper does

Given a model, a context, a query and the response the model produced, ContextCite
answers: **which parts of the context caused this response?**

It does so without touching the model's internals — no attention weights, no gradients.
The method is four steps, and you implement each one:

| # | Step | File |
|---|---|---|
| 1 | Split the context into `d` **sources** (sentences) | `partition.py` |
| 2 | Sample `n=64` random **ablations**, keeping each source with prob `0.5` | `ablation.py` |
| 3 | Score the *original* response under each ablated context (**logit-probability**) | `logit_probs.py` |
| 4 | Fit a **sparse linear surrogate** (LASSO, `alpha=0.01`) from mask → score | `lasso.py` |

**The LASSO weights are the attribution scores.** One number per source: how much
keeping that source raised the log-odds of the response.

Everything else — attributing individual clauses, verifying claims, pruning context,
catching prompt injection — falls out of those four steps.

## Why it is worth building yourself

The method is small enough to hold in your head and makes three decisions that only
become obvious once you have implemented them:

- **Why the logit and not the log-probability.** Log-probability saturates: a source
  moving a token from p=0.98 to p=0.999 barely registers. The logit is unbounded and
  roughly additive in evidence, which is what licenses a *linear* surrogate.
- **Why random subsets and not leave-one-out.** If two sources both state the answer,
  removing either alone changes nothing and leave-one-out concludes neither matters.
  You will measure this failure directly in step 7.
- **Why LASSO and not least squares.** L1 drives coefficients to *exactly* zero. "No
  evidence" is a stronger, more useful output than a small noisy number.

---

## How to use this directory

Top-level files are **templates**: each function has a docstring explaining what to
build and why, then `raise NotImplementedError`. You fill them in. `solutions/` holds
complete working versions for when you are stuck or want to compare afterwards.

```bash
cd contextcite
python3 check.py            # what to build next
# ... implement the functions the checker points at ...
python3 check.py            # re-run; it stops at the first thing not yet done
```

`check.py` runs **14 graded checks** against *your* code (it never imports
`solutions/`). Each names the file, the concept, and — when something is wrong — the
usual cause:

```
  ✓  1. partition.py         splitting text into sources
  ✓  2. partition.py         rebuilding ablated contexts
  ·  3. logit_probs.py       logit-prob math and stability
      not implemented yet — logit_probs.py:45 in logsumexp()

  2/14 passing, 1 to write

  Next: step 3 — logit-prob math and stability (logit_probs.py)
```

| Command | Does |
|---|---|
| `python3 check.py` | Run in order, stop at the first unimplemented step |
| `python3 check.py 6` | Run only step 6, while you iterate on it |
| `python3 check.py 6 9` | Run steps 6 through 9 |
| `python3 check.py --all` | Run everything, skipping nothing |
| `python3 <file>.py` | Run that file's own demo once it is implemented |

Grey `·` means not written yet. Red `✗` means written but wrong.

---

## The seven steps

Sized deliberately: two short files to start, the hard one in the middle, then payoff.

### Step 1 — `partition.py` · *small*
Split the context into sentences, keeping the separators, so an ablated context can be
reassembled as natural text. **The invariant:** `build()` with an all-True mask must
reproduce the original context *exactly*. If it does not, every later measurement is
made against a context the model never saw.

### Step 2 — `logit_probs.py` · *small code, careful thought*
The quantity being regressed:

```
logit_prob(token) = z[y] − logsumexp(z[j] for j ≠ y)      # = log(p / (1−p))
log P(response)   = Σ log_sigmoid(logit_prob_t)
score             = log P − log(1 − P)
```

Four short functions where the numerical detail *is* the lesson. Compute the logit
directly from logits — going via softmax makes `p` round to 1.0 and `1−p` exactly zero
for a token the model was merely confident about.

### Step 3 — `ablation.py` · *small*
Sample the design matrix. Keep-probability ½ maximises each column's variance, which is
exactly what the regression needs to identify a coefficient. Check for degenerate
columns: a source that was never ablated has no identifiable effect, and the failure is
silent.

### Step 4 — `lasso.py` · *the big one*
LASSO by coordinate descent, in pure Python, matching scikit-learn's objective:

```
minimise  (1/2n)·‖y − Xw − b‖²  +  alpha·‖w‖₁
```

Four pieces: soft-thresholding, standardisation, the descent loop, and undoing the
standardisation. Verify by recovering coefficients you generated yourself before
pointing it at real data.

### Step 5 — `contextcite.py` · *medium, mostly assembly*
The `ContextCiter`. One design decision matters: **cache the per-token matrix**
(`n_ablations × n_response_tokens`), not the aggregated scores. Aggregation is cheap and
span-dependent; model calls are expensive and span-independent. Get this right and
attributing any span afterwards is free — which is what makes step 7's poisoning
detection possible.

### Step 6 — `evaluate.py` · *medium — the honesty step*
Is any of this real? Two checks:

- **LDS** (linear datamodeling score): fit on training masks, predict *held-out*
  ablations, take the Spearman correlation.
- **Top-k drop** against a random-k baseline.

The result to internalise:

| ablations | in-sample R² | held-out LDS |
|---|---|---|
| 8 | 0.9993 | 0.7586 |
| 64 | 0.9888 | 0.9355 |

R² goes *down* as the estimate gets *better*. With 8 sources and 8 ablations the
surrogate simply interpolates. Report LDS.

### Step 7 — `applications.py` · *medium, the most fun*
The paper's three applications plus the experiment that justifies the sampling design:

1. **Verification** — which tokens the context actually supports
2. **Pruning** — one source out of eight (16% of the characters) preserves the answer
   *and raises its probability*, because the other seven were competing for probability
   mass
3. **Poisoning** — whole-response attribution **misses** an injected sentence; per-token
   and span attribution **catch** it. This is why the paper supports attributing
   arbitrary spans
4. **Leave-one-out fails** — duplicate the answer sentence and leave-one-out scores each
   copy at ~3.8 while ContextCite scores each at ~21

---

## The model: read this before you start

`toy_lm.py` is **provided complete — it is not an exercise.** ContextCite attributes *a
model's* response to *its* context, so you need a model. `ToyLM` is a small, honest
conditional language model: it scores each vocabulary word by how often it appears in
the context, weighting each sentence by its overlap with the query.

It is a real probability model — normalised, deterministic, teacher-forcible. **It is
not a transformer:** no parameters, no word order. That is a deliberate trade so the
whole directory runs in pure Python in under a second.

**The attribution method you implement is the paper's, unchanged.** What is
substituted is the thing being attributed. Two consequences to keep straight:

- The generated text is not fluent English — it is a bag of context words. Judge the
  *attributions*, not the prose.
- On the simple context every token attributes to the same source, because only one
  sentence is relevant. Add a competing sentence (step 7) and the top source varies per
  token, as it would with a real LLM.

### Swapping in a real model

The only interface ContextCite needs is:

```python
model.index                              # token -> id, over a FIXED vocabulary
model.sequence_logits(context, response) # one logit row per response token
model.generate(context)                  # optional; you can pass a response instead
```

Wrap a Hugging Face causal LM by tokenising `prompt + response`, running one forward
pass, and slicing `logits[-(len(response)+1):-1]`. The reference implementation does
exactly this in `context_cite/utils.py`. Nothing above `logit_probs.py` changes.

The vocabulary must be **fixed across ablations** — if ablating a source changes the
vocabulary, logits from different ablations are not comparable.

---

## What this implementation does not do

- **No real LLM**, per above. No batching, no GPU, no `left` padding subtleties.
- **Sentence sources only.** The reference also supports word-level sources; the paper
  notes these need far more ablations, since the number of subsets grows with `d`.
- **No hierarchical or adaptive ablation** — every source is sampled independently at
  a fixed rate.
- **No benchmark suite.** The paper evaluates on CNN-DailyMail, TyDi QA, HotpotQA and
  MS MARCO; here there is one worked example with a known ground-truth source.
- **`aggregate` returns `inf`** when the response probability rounds to 1. Fine at this
  scale; a real implementation would clamp.

## Extensions worth trying

1. **Word-level sources.** Change the partitioner, then find out empirically how many
   ablations you need before LDS recovers.
2. **A real Hugging Face model**, using the interface above. Attribute a genuine RAG
   answer to its retrieved passages.
3. **Cheaper attribution.** The paper discusses reducing the ablation count. Try a
   larger `alpha` with fewer ablations and track LDS — where does it break?
4. **Group sources.** Attribute to whole retrieved *documents* rather than sentences,
   which is what a RAG pipeline actually wants to cite.
5. **Compare against attention.** Attention weights are the intuitive baseline and a
   known-poor attribution method. Measure both with LDS and see for yourself.

---

## Structure

```
contextcite/
├── README.md
├── check.py              # progress checker — run this first
├── toy_lm.py             # PROVIDED complete, not an exercise
├── partition.py          # templates with TODOs
├── logit_probs.py
├── ablation.py
├── lasso.py
├── contextcite.py
├── evaluate.py
├── applications.py
└── solutions/            # complete, runnable implementations
```

```bash
cd solutions
python3 toy_lm.py         # the model and the running example
python3 partition.py      # sources and ablated contexts
python3 logit_probs.py    # the regression target
python3 ablation.py       # the design matrix
python3 lasso.py          # the surrogate
python3 contextcite.py    # attribution, end to end
python3 evaluate.py       # LDS vs in-sample R²
python3 applications.py   # verification, pruning, poisoning, leave-one-out
```

No dependencies beyond the Python 3 standard library. Everything runs in about a second.

## Related directories

- [`context-caching/`](../../week-03/context-caching/) — a different "context" problem: making
  inference cheap rather than explaining it
- [`dynamo-paper/`](../../week-10/dynamo-paper/) — another paper replicated section by section
- [`ml-in-production/`](../../week-18/ml-in-production/) — where attribution belongs in a real
  serving stack
