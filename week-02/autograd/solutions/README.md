# Autograd From Scratch — Solutions

Complete implementations of every template in the parent directory. Pure Python
3 standard library.

```bash
python3 tensor.py  nn.py  optim.py  digits.py
python3 train.py          # ~60s, trains a dozen small models
python3 generative.py     # ~40s, trains four
```

## Implementation notes

- **`Tensor.accumulate` adds, never assigns.** Not an optimisation — required
  whenever a tensor feeds more than one operation, which is every weight in a
  network with a residual connection or weight tying. It is also why the
  training loop must call `zero_grad()`: the engine cannot know where one step
  ended.
- **`backward()` topologically sorts before running any `_backward`.** A tensor
  used twice has two children contributing to its gradient, and running its own
  backward before both have arrived propagates a partial gradient. Nothing
  crashes; the model just trains slightly worse, forever. The `x * x + x` case
  in `check_gradient` is what catches it.
- **`_unbroadcast` folds a gradient back onto the shape it was broadcast from.**
  A bias used once per row receives one contribution per row and they must be
  summed. Return the gradient unfolded and every bias gradient is a factor of
  `batch_size` too small.
- **`exp` reuses its forward output in the backward pass** rather than
  recomputing. That is the most common backward-pass optimisation there is, and
  it is why activations stay alive until backward runs — the memory cost of
  training, in one line.
- **`softmax_cross_entropy` subtracts the row max before exponentiating.**
  Logits of 1000 overflow otherwise, and the fused gradient
  `softmax(x) - onehot(y)` is the other half of why the two are one operation.
- **`Module.parameters()` recurses into lists of modules.** A `Sequential`
  stores its layers in a list, so without that branch every parameter in every
  model is invisible to the optimiser — and there is no error.
- **`train_mode` checks the module ITSELF before its attributes.** A `Dropout`
  inside a `Sequential` arrives as a list item, not as an attribute, which is
  how it arrives in every real model. This was a bug the checker found.
- **`Dropout` scales by `1/keep` during training**, so the eval path is a plain
  identity. Zero half the units without it and inference sees activations twice
  as large as the next layer was trained for.
- **`Adam` divides by `(1 - beta**t)`.** Check which direction it cuts before
  writing anything about it: the second moment is under-estimated by
  `(1 - 0.999)` under a square root, so the RAW step is ~3.16x too **large** on
  step one. With correction it is exactly the learning rate.
- **`clip_grad_norm` uses the GLOBAL norm** across every parameter. Per-tensor
  clipping changes the update direction, which makes it a different optimiser
  rather than the same one taking a shorter step.
- **`VAE.reparameterize` draws `eps` outside the graph**, with
  `requires_grad=False`. That is the whole trick — and note `exp(log_var / 2)`,
  because `log_var` is a log variance and the standard deviation is its square
  root. A vanishing-noise test cannot catch a missing `/2` (both `exp(-40)` and
  `exp(-20)` are zero), so the checker measures the noise's spread at
  `log_var = 2` instead.
- **`VAE.loss` returns reconstruction and KL separately.** Watching the two
  terms individually is the only way to diagnose a VAE: a KL collapsing to zero
  means the encoder gave up, and a KL growing without bound means it is
  smuggling information through by scattering the codes.

## What the demos measure

`tensor.py` — every operation's gradient against central differences, including
a tensor used twice; the bias-broadcast fold; and the 2x forward/backward ratio
that makes reverse mode the only viable choice.

`nn.py` — five stacked Linear layers being bit-for-bit the same function as one
matrix; activation variance through six layers at three init scales; dropout's
training and eval means matching.

`optim.py` — four optimisers on one ravine with `final |x|` as the score; a
learning-rate sweep showing a sharp divergence threshold rather than a gradual
one; Adam's bias correction measured as update size.

`train.py` — the overfit check first; linear vs MLP vs deeper MLP with a seconds
column; overfitting produced on demand by shrinking the training set; batch size
against updates per epoch; a confusion matrix on deliberately harder data,
because at low noise the model is at 100% and the matrix is all zeros.

`generative.py` — the ladder: autoencoder works, sampling from it fails, the KL
term fixes it. The measurement that explains why is the distance from a random
`N(0, I)` draw to the nearest code the model has actually seen: 2.22 for the
autoencoder against 1.49 for the VAE. Then a beta sweep showing both failure
modes — scattered codes at 0, posterior collapse at 30 — with sample sharpness
against the real data as the discriminator.
