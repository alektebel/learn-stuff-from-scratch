# Autograd From Scratch

Build the thing every other ML directory in this repo imports. Reverse-mode
automatic differentiation, layers, optimisers, a training loop and a generative
model — in pure Python, with no framework anywhere.

## Why this directory exists

The repo's ML track goes: CUDA kernels → inference and serving → papers. Every
directory from `world-models` onwards begins `import torch`, so torch is a black
box for the entire back half of the plan. Nothing ever builds a tensor that
carries a gradient.

This is that missing middle, and it is the highest-leverage directory here: once
you have written `backward()`, six other directories stop being magic.

## What you build

| File | What it is | Stubs |
|---|---|---|
| `tensor.py` | Array autograd: a tape, broadcasting, matmul, fused cross-entropy | 27 |
| `nn.py` | Module, Linear, activations, Sequential, Dropout, initialisation | 13 |
| `optim.py` | SGD, momentum, RMSProp, Adam, AdamW, clipping, schedules | 7 |
| `digits.py` | **Provided.** An MNIST-shaped 8x8 dataset that works offline | — |
| `train.py` | The six-line loop, and the instrumentation around it | 7 |
| `generative.py` | An autoencoder, its failure, and the VAE that fixes it | 13 |

---

## How to use this directory

The files at the top level are **templates**: every function has a docstring
explaining what to build and why, then `raise NotImplementedError`. You fill them
in. `solutions/` holds complete working versions.

```bash
cd autograd
python3 check.py            # what to build next
```

**10 graded checks** against your code. It never imports `solutions/`.

| Command | Does |
|---|---|
| `python3 check.py` | Run in order, stop at the first unimplemented step |
| `python3 check.py 4` | Run only step 4 |
| `python3 check.py --all` | Run everything |
| `python3 <file>.py` | Run that file's own demo |

`digits.py` is **given to you**, like `contextcite/toy_lm.py`. Retyping a dataset
loader teaches nothing, and MNIST is a 45 MB download this repo cannot make.

---

## The four decisions this directory is built around

### 1. Array autograd, not scalar autograd

The clearest possible autograd is one object per **number** — micrograd's design,
and genuinely the best way to explain the idea. It also cannot train anything: a
64x32 layer is 2,048 objects and a batch of 32 is 65,536, all allocating on every
multiply.

So: one node per **tensor**, a flat list of floats, and a shape. The chain rule is
identical and the constant factor is three orders of magnitude better — which is
what makes the rest of the directory possible.

### 2. Reverse mode, not forward mode

```
  parameters   forward ops   backward ops   ratio
         200         1,000          2,000     2.0x
      80,000     8,000,000     16,000,000     2.0x
```

A backward pass costs about **twice** a forward one, whatever the parameter
count. Forward mode would cost one forward pass *per parameter*. That asymmetry
is the entire reason training is possible, and it is why `backward()` walks the
tape once rather than being called per weight.

### 3. Broadcasting forwards is summing backwards

Exactly two broadcasts are supported — a scalar, and a `(1, N)` row against an
`(M, N)` matrix, which is what a bias add is. Everything else raises with both
shapes named.

The half people get wrong is the backward pass. A value reused across `N` rows
receives `N` contributions and they must be **summed**:

```
  batch shape (3, 2), bias shape (1, 2)
  d(sum)/d(bias) = [3.0, 3.0]
```

Skip the fold and every bias gradient is a factor of `batch_size` too small. The
loss still goes down — just wrongly — which is what makes it hard to find.

### 4. Softmax and cross-entropy are one operation

Two reasons, and both matter. **Numerically**: softmax computes `exp(x)` and
cross-entropy immediately takes `log`; separately, logits of 1000 overflow.
**Analytically**: the gradient of the fused pair is simply
`softmax(x) - onehot(y)` — two elegant expressions collapse to a subtraction.

This is why `nn.CrossEntropyLoss` takes **logits**, and why passing it softmax
output is a real and common bug: it applies softmax twice.

---

## Measured results

### Depth without a nonlinearity is not depth

```
  5 stacked Linear layers, no activation: [0.30398319, 0.41235212, 0.09832655]
  one matrix, their product:              [0.30398319, 0.41235212, 0.09832655]
  max difference: 5.41e-16
```

The same function. A composition of affine maps is an affine map, so five layers
have exactly the expressive power of one.

### Initialisation, through six layers

```
  init scale            L1        L2        L3        L4        L5        L6
  too small (x0.1)      8.5e-02   8.5e-03   7.8e-04   6.5e-05   6.2e-06   6.2e-07
  He: sqrt(2/fan_in)    8.5e-01   8.5e-01   7.8e-01   6.5e-01   6.2e-01   6.2e-01
  too large (x3)        2.6e+00   7.6e+00   2.1e+01   5.3e+01   1.5e+02   4.5e+02
```

At the small scale the signal is 1e-7 by layer six — and so is the gradient
reaching layer one, so the early layers never learn. The factor of 2 in He init
pays back exactly the half of the signal ReLU throws away.

### Four optimisers on the same ravine

`f(x, y) = 0.5x² + 20y²` — steep across, shallow along. `final |x|` is how far
along the valley each one travelled from `x = 2`:

```
  optimiser                 step 1   step 20   step 60   final |x|
  SGD lr=0.02               82.000    0.9282   0.18438      0.5951
  SGD + momentum 0.9        82.000   11.7835   0.19175      0.0029
  RMSProp lr=0.1            82.000    0.5838   0.00000      0.0000
  Adam lr=0.1               82.000    1.7078   0.02694      0.0429
```

Plain SGD is limited by the *steep* direction: a rate large enough to progress
along the valley diverges across it. Momentum cancels the oscillating component
and accumulates the consistent one.

### Adam's bias correction cuts the other way from the usual summary

```
  step   |update| corrected   |update| raw   raw / corrected
     1             0.010000       0.031623              3.16x
     5             0.009978       0.057246              5.74x
```

Both moments start at zero, but the *second* is under-estimated by `(1 - 0.999)`
and sits under a square root — so the raw step comes out about **3x too large**
on step one, not too small. With correction, Adam's first step is exactly the
learning rate.

### Overfitting, produced on demand

```
  training examples   train acc   test acc     gap
                 40      100.0%      48.0%   52.0%
                120      100.0%      78.5%   21.5%
                600      100.0%      95.0%    5.0%
```

Training loss falls just as smoothly in every row. The **gap** is the
measurement, which is why a training curve alone tells you nothing.

### A generative model, and the term that makes it one

`generative.py` is the repo's MVP-then-limit-case ladder in miniature:

1. An **autoencoder** squeezes each image through six numbers and reconstructs it
   well.
2. **Sample** from that bottleneck and decode. Noise.
3. A **VAE** adds one term to the loss and sampling starts working.

The measurement that explains why:

```
  model           code std   draw -> nearest real code
  autoencoder         1.96                        2.22
  VAE                 0.88                        1.49
```

The second column is the important one. The autoencoder's codes sit in clusters
with emptiness between them, so a draw from `N(0, I)` lands where the decoder has
never been asked anything. The KL term **fills** the space.

And both failure modes of the weight on it:

```
   beta   reconstruction       KL   sample sharpness   what happened
    0.0           0.2676   5.6162             0.5124   codes scattered; samples are noise
    0.3           0.5563   0.6210             0.4149   usable
   30.0           0.9656   0.0003             0.2038   posterior collapse; one blurry average
   real                —        —             0.6392   the data itself
```

Opposite signs, one number telling them apart.

---

## The reparameterisation trick, in one paragraph

You cannot backpropagate through `z = sample(N(mu, sigma))` — a coin flip has no
derivative. So draw the randomness **outside** the computation, `eps ~ N(0, 1)`,
and write `z = mu + exp(log_var/2) * eps`. Now `z` is a deterministic,
differentiable function of `mu` and `log_var`, with `eps` as a constant input. The
randomness is still there; it moved somewhere the chain rule does not have to go.

Note the `/2`: `log_var` is a log **variance**, and the standard deviation is its
square root. Miss it and every sample is far too spread out while the KL term is
computed against a distribution the sampler is not using.

---

## The habit worth taking away

> Before any hyperparameter: **overfit ten examples.**

If the model cannot drive the loss on ten examples to nearly zero, gradients are
not flowing, or a parameter is not registered, or the loss is not connected to the
output. You have a bug, and no learning-rate sweep fixes a bug. `train.py` runs
this check first for that reason, and `check.py` asserts it.

The second habit: **compare every gradient against central differences.** An
analytic gradient that is subtly wrong still trains, just worse. `check_gradient`
is the oracle, and it is the first thing to write.

---

## Where this implementation stops

- **Pure Python, single-threaded, CPU.** A matmul is three nested loops. Real
  frameworks call BLAS, and the gap is roughly 1000x. See
  [`cuda-from-scratch/`](../../week-16/cuda-from-scratch/) for the other end of that.
- **Two broadcast rules**, not NumPy's full set.
- **2-D only.** No convolutions, so no CNNs — the digits are flattened to 64
  numbers and the model never knows they were a grid.
- **No graph optimisation, no fusion, no vectorised execution.** Every operation
  materialises its whole output.
- **No RNG control per device, no checkpointing, no mixed precision, no
  distributed anything.**
- **The dataset is synthetic.** It is MNIST-shaped, not MNIST.

## Extensions worth trying

1. **A `Conv2d` layer.** The forward pass is a loop; the backward pass is the
   interesting part, and it is a convolution too. Then compare against the MLP on
   the same digits and see what translation invariance is worth.
2. **Batch normalisation**, and then work out why its backward pass is genuinely
   hard — the batch statistics depend on every element, so every element's
   gradient depends on every other.
3. **A bounded top-N heap in `Sort`**... wrong directory. Instead: **gradient
   checkpointing** — drop stored activations and recompute them during backward,
   and measure the memory-against-time trade directly.
4. **An attention layer**, then head straight into
   [`../llm-from-scratch/`](../llm-from-scratch/), which is built on this engine.
5. **Vectorise the matmul** with `array` or by blocking, and measure. It is the
   same amortisation argument as everything in `../database-engine/executor.py`.
6. **Swap the VAE for a diffusion model** on the same digits and compare the
   sample sharpness table. The blur in a VAE is not a bug in your code — a
   squared-error loss averages over plausible outputs — and that single property
   is most of why diffusion models exist.

---

## Structure

```
autograd/
├── README.md
├── check.py              # progress checker — run this first
├── tensor.py             # templates with TODOs and DESIGN DECISION blocks
├── nn.py
├── optim.py
├── digits.py             # PROVIDED — do not implement
├── train.py
├── generative.py
└── solutions/
```

```bash
cd solutions
python3 tensor.py         # the chain rule, checked against central differences
python3 nn.py             # init, and why depth needs a nonlinearity
python3 optim.py          # four optimisers on one ravine
python3 digits.py         # the dataset, and what noise does to it
python3 train.py          # the loop and its instrumentation  (~60s)
python3 generative.py     # autoencoder, failure, VAE          (~40s)
```

No dependencies beyond the Python 3 standard library. Two of the demos train
several small models and take about a minute each; the rest are instant.

## Related directories

- [`llm-from-scratch/`](../llm-from-scratch/) — a transformer trained on this
  engine
- [`cuda-from-scratch/`](../../week-16/cuda-from-scratch/) — the same matmul, on a GPU,
  1000x faster
- [`world-models/`](../../reference/world-models/), [`diffusion-models/`](../../reference/diffusion-models/)
  — where `import torch` stops being a black box
- [`ml-inference/`](../../reference/ml-inference/) — what happens to a trained model next
- [`PHILOSOPHY.md`](../../PHILOSOPHY.md) — why this repo is built the way it is

## Sources

- Baydin, Pearlmutter, Radul & Siskind, **"Automatic Differentiation in Machine Learning: a Survey"**, JMLR 2018 — why reverse mode, and the cost asymmetry `tensor.py`'s demo measures.
- Kingma & Ba, **"Adam"**, ICLR 2015 — §2 for bias correction; check which direction it cuts before writing about it.
- Kingma & Welling, **"Auto-Encoding Variational Bayes"**, ICLR 2014 — the reparameterisation trick in `generative.py`.
- Glorot & Bengio, AISTATS 2010; He et al., ICCV 2015 — the two init scales in `init_scale`.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-2--autograd)
