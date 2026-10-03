# LLM From Scratch

A byte-pair tokeniser, multi-head causal attention, a GPT, a training loop and
four decoding strategies — in pure Python, on the autograd engine you wrote in
[`../autograd/`](../autograd/).

By the end it trains on real text and generates from it. Nothing here imports a
framework.

## Prerequisite

Do [`../autograd/`](../autograd/) first. `engine.py` in this directory is that
engine — `tensor.py`, `nn.py` and `optim.py` concatenated — plus the four
operations a transformer needs that a plain MLP does not:

| Operation | Why it is not in the MLP engine |
|---|---|
| `layer_norm` | Normalises each **row**, not each batch. The backward pass is written by hand because every element of a row affects every other through the shared statistics |
| `embedding` | Forward is a gather; backward is a **scatter-add**. A token appearing five times contributes five gradients to one row and they must accumulate |
| `slice_columns` / `concat_columns` | Heads are a **view** of one projection, not h separate ones |
| `masked_softmax` | The mask goes in as `-inf` **before** the exponential |

It is vendored rather than imported across directories so this one runs
standalone.

## What you build

| File | What it is | Stubs |
|---|---|---|
| `tokenizer.py` | BPE: learn merges, replay them in rank order | 10 |
| `attention.py` | Scaled dot-product, causal masking, multi-head | 4 |
| `transformer.py` | LayerNorm, feed-forward, pre-norm blocks, GPT | 8 |
| `train.py` | Next-token prediction, gradient accumulation, perplexity | 4 |
| `sample.py` | Greedy, temperature, top-k, top-p | 9 |
| `distill.py` | On-policy distillation: KLs, OPD, OPSD, Privilege Illusion | 11 |
| `engine.py` | **Provided** | — |

```bash
cd llm-from-scratch
python3 check.py          # 15 graded checks against YOUR code
```

---

## Measured results

### Tokenisation decides your attention bill

```
  vocabulary   merges   tokens  chars/token  attention cost
          34        0       59         1.00           1.00x
          80       46       23         2.57           0.15x
         300      266       16         3.69           0.07x
```

Attention is **quadratic** in sequence length, so the last column is the token
count squared. This is why nobody trains a character-level model at scale — not
because characters are a worse representation, but because there are four times
as many of them.

And two different ways text gets expensive:

```
  text                              tokens  chars/token  round-trips?
  in-distribution English                6         3.67           yes
  English, unfamiliar words             18         1.44           yes
  outside the alphabet                   9         1.56     NO — lost
```

Unfamiliar text is *expensive* — no merges apply, so it costs a token per
character, which is why the same sentence can cost several times more in a
language the merge table was not trained on. Text outside the alphabet is
**lost**, and that is precisely the failure real tokenisers avoid by working on
**bytes**: there are only 256 of them, every one is in the alphabet, and nothing
can ever be unrepresentable.

### Why sqrt(d_k), as attention entropy

```
     d_k    unscaled entropy    scaled entropy   even would be
       4               2.427             3.421           4.000
      64               0.807             3.445           4.000
     256               0.206             3.284           4.000
```

Unscaled at `d_k = 256`, the softmax has collapsed to near-certainty **before a
single gradient step** — and the gradient through a saturated softmax is ~0, so
it cannot learn its way out. The scaling holds entropy near the even value at
every width, which is what lets you make `d_k` large at all.

### Residual connections are a gradient highway

```
  depth   grad norm WITH residual       WITHOUT       ratio
      2                    8.7925      0.987095          9x
     12                   27.2205      0.000077     352177x
```

`y = x + f(x)` has derivative `1 + f'(x)`. The **1** is a path along which the
gradient reaches every earlier layer unchanged, whatever `f'` does. Without it
the gradient is a product of N Jacobians and decays geometrically — by twelve
layers there is nothing left to train the first one with.

### Attention has no idea what order anything is in

```
  unmasked attention, rows shuffled [2, 0, 3, 1]:
    max difference from the same rows, shuffled the same way: 2.22e-16
  the same, with a positional vector added first:              5.27e-01
```

Attention is a weighted **sum**, and a sum is permutation-equivariant to the
last bit. *dog bites man* and *man bites dog* are the same input. Adding a
position vector is what breaks the symmetry — and a causal mask breaks it too,
which is why a decoder-only model can partly infer position from the mask alone.

### The ablation that looks like a triumph

Same model, same data, same steps — one with the causal mask, one without:

```
  model                         final training loss   perplexity
  with the causal mask                       3.2906         26.9
  without it                                 1.1518          3.2
```

The unmasked model's loss is **eight times better** and the model is worthless:
predicting token *t* is trivial when you can attend to token *t*. Nothing in
the training curve hints at it. The only ways to catch it are to generate, or
to assert the mask directly in a test — which `check.py` does.

### Decoding changes the output more than most architecture choices

```
  strategy                  repetition   distinct  sample
  greedy                          85%        12%  ' cat ate the cat ate the cat ate t'
  T=0.5                            0%        50%  ' cat ate the rat and the catv the '
  T=1.0, top-p=0.9                 0%        70%  ' catnd sd and the st pa5sll.  corh'
  T=2.0                            0%        72%  ' fo gc os.ll he3batghened sted and'
```

Greedy is deterministic and **loops**: the most likely continuation of a common
phrase is very often the phrase again, and nothing is random enough to break
out. A model that seems repetitive and a model that seems incoherent are
frequently the same model at two temperatures.

### Why top-p rather than top-k

```
  context                     entropy   nucleus at p=0.9   top-k=8 keeps
  'the cat sat on the'           4.71                 29               8
  'a bird sat on the l'          6.00                 58               8
```

The nucleus grows and shrinks with the model's confidence; `k` cannot. After a
context with one obvious continuation, `k=8` admits seven wrong tokens; after
an open one it discards good ones.

---

## The three things worth carrying away

1. **The causal mask is load-bearing and silent.** It is one line, breaking it
   makes your metrics better, and no curve will tell you.
2. **Perplexity is only comparable within one tokeniser.** Different
   vocabularies are different denominators. Comparing perplexities across
   tokenisers is a very common mistake.
3. **Generation is quadratic because nothing remembers.** Every step re-runs the
   whole prefix. Removing exactly that waste is what
   [`context-caching/`](../../week-03/context-caching/) is about — the same model, from
   the serving side.
4. **A falling distillation loss is not capability.** Privilege Illusion is the
   student copying tokens that only exist because the teacher saw the answer.
   `distill.py` separates that tell from the tokens that are the actual skill.

---

## Where this implementation stops

- **One sequence at a time.** No batch dimension; `train.py` uses gradient
  accumulation instead, which is equivalent and much slower.
- **Character-level BPE, not byte-level.** Anything outside the training
  alphabet is dropped rather than encoded, which the demo measures. This is the
  most important detail skipped.
- **Learned absolute positions.** No RoPE, no ALiBi, no relative attention —
  and no ability to run past `block_size`.
- **No KV cache**, no dropout in the blocks, no gradient checkpointing, no
  mixed precision, no distributed anything.
- **Tiny.** ~10,000 parameters, a 16-token context, and a corpus of a few
  thousand tokens. It learns which tokens follow which, which is genuinely what
  next-token prediction is — but do not expect meaning.

## Extensions worth trying

1. **Byte-level BPE.** Start from 256 byte values instead of the corpus
   alphabet. Nothing can ever be out-of-vocabulary again, and the demo's
   round-trip failures disappear.
2. **RoPE.** Rotate the query and key vectors by an angle proportional to
   position, inside attention rather than added at the input. It is what modern
   models use, and it extrapolates past the trained length.
3. **A KV cache**, then measure generation cost against length before and after.
   Then read [`context-caching/`](../../week-03/context-caching/), which is that idea
   taken all the way to a serving stack.
4. **A batch dimension** in the tensor engine, so `train.py` can drop the
   accumulation loop. This is the single biggest speedup available.
5. **Grouped-query attention**: share K and V across query heads and measure the
   memory saving. It is the largest KV reduction in modern models.
6. **Train on something real** — a book from Project Gutenberg — and watch
   perplexity against corpus size. Then work out how far you are from a model
   that says anything, and why that gap is mostly compute.
7. **Distill this model into a shallower one** with reverse KL on student
   rollouts, then again with forward KL, and compare the samples. Mode-seeking
   versus mode-covering is not a slogan until you have heard both students.

---

## Structure

```
llm-from-scratch/
├── README.md
├── check.py              # progress checker — run this first
├── engine.py             # PROVIDED — ../autograd/ plus four operations
├── tokenizer.py          # templates with TODOs and DESIGN DECISION blocks
├── attention.py
├── transformer.py
├── train.py
├── sample.py
├── distill.py            # OPD / OPSD / Privilege Illusion — after sampling
└── solutions/
```

```bash
cd solutions
python3 tokenizer.py      # merges, compression, and the out-of-alphabet failure
python3 attention.py      # the sqrt(d_k) entropy table, masks, the quadratic cost
python3 transformer.py    # residual highway, permutation-equivariance, tying
python3 train.py          # a model that learns, then the mask ablation   (~80s)
python3 sample.py         # greedy degeneracy, temperature, top-k, top-p  (~35s)
```

No dependencies beyond the Python 3 standard library. `train.py` and `sample.py`
each train small models and take a minute or so; the rest are instant.

## Related directories

- [`autograd/`](../autograd/) — the engine this is built on. **Do it first.**
- [`context-caching/`](../../week-03/context-caching/) — the same architecture from the
  serving side: KV caching, prefix reuse, paged memory
- [`contextcite/`](../../week-05/contextcite/) — attributing a generated answer back to its
  context
- [`cuda-from-scratch/`](../../week-16/cuda-from-scratch/) — the matmuls, on hardware that
  can actually run them
- [`vllm-engine/`](../../reference/vllm-engine/) — serving one of these at scale
- [`PHILOSOPHY.md`](../../PHILOSOPHY.md) — why this repo is built the way it is

## Sources

Full list, including the distillation papers, in
[`../../REFERENCES.md`](../../REFERENCES.md#week-2--llm-from-scratch).

- Vaswani et al., **"Attention Is All You Need"**, NeurIPS 2017 — §3.2.1 is the
  scaled dot product and the √d_k.
- Sennrich et al., **ACL 2016** — BPE, and why merges apply in rank order.
- Xiong et al., **ICML 2020** — why pre-norm trains without a warmup.
- Holtzman et al., **ICLR 2020** — top-p, and what greedy decoding produces.
- Hinton, Vinyals & Dean, **2015**; Wang et al., **MiniLM**, NeurIPS 2020;
  Agarwal et al., **GKD**, 2023; Rafailov et al., **DPO**, NeurIPS 2023 — the
  four behind `distill.py`.
