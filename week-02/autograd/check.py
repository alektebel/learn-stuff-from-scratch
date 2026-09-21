"""
Progress checker for the autograd templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

Nothing here imports solutions/. It tests YOUR code.
"""

import math
import pathlib
import random
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# Tensor
# ---------------------------------------------------------------------------

def check_forward() -> None:
    from tensor import Tensor

    a = Tensor([1.0, 2.0, 3.0, 4.0], (2, 2))
    b = Tensor([10.0, 20.0, 30.0, 40.0], (2, 2))
    assert (a + b).data == [11.0, 22.0, 33.0, 44.0]
    assert (a * b).data == [10.0, 40.0, 90.0, 160.0]
    assert (a * 2.0).data == [2.0, 4.0, 6.0, 8.0], "scalars must broadcast"
    assert (a - b).data == [-9.0, -18.0, -27.0, -36.0]

    m = Tensor([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], (2, 3))
    n = Tensor([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], (3, 2))
    product = m @ n
    assert product.shape == (2, 2), f"(2,3) @ (3,2) is (2,2), got {product.shape}"
    assert product.data == [22.0, 28.0, 49.0, 64.0], (
        f"got {product.data}, expected [22, 28, 49, 64] — row times column, "
        "and the inner dimensions are the ones that vanish")
    try:
        (m @ m)
        raise AssertionError("mismatched inner dimensions must raise")
    except ValueError:
        pass

    assert m.transpose().shape == (3, 2)
    assert m.transpose().data == [1.0, 4.0, 2.0, 5.0, 3.0, 6.0]
    assert abs(a.sum().item() - 10.0) < 1e-12
    assert abs(a.mean().item() - 2.5) < 1e-12
    assert Tensor([-1.0, 0.0, 2.0]).relu().data == [0.0, 0.0, 2.0]

    bias = Tensor([1.0, 2.0], (1, 2))
    batch = Tensor([0.0, 0.0, 10.0, 10.0, 20.0, 20.0], (3, 2))
    assert (batch + bias).data == [1.0, 2.0, 11.0, 12.0, 21.0, 22.0], (
        "a (1, N) row must broadcast across every row of an (M, N) matrix — "
        "that is what a bias add is")


def check_backward() -> None:
    from tensor import Tensor, check_gradient

    x = Tensor([3.0], requires_grad=True)
    y = Tensor([4.0], requires_grad=True)
    z = (x * y + x).tanh()
    z.backward()
    inner = math.tanh(15.0)
    assert abs(x.grad[0] - (1 - inner * inner) * 5) < 1e-9, (
        f"dz/dx is {x.grad[0]}, expected {(1 - inner * inner) * 5}")
    assert abs(y.grad[0] - (1 - inner * inner) * 3) < 1e-9

    rng = random.Random(0)
    cases = [
        ("add", lambda t: (t[0] + t[1]).sum(),
         [Tensor.randn(3, 4, rng=rng), Tensor.randn(3, 4, rng=rng)]),
        ("mul", lambda t: (t[0] * t[1]).sum(),
         [Tensor.randn(3, 4, rng=rng), Tensor.randn(3, 4, rng=rng)]),
        ("matmul", lambda t: (t[0] @ t[1]).sum(),
         [Tensor.randn(3, 4, rng=rng), Tensor.randn(4, 2, rng=rng)]),
        ("relu(matmul)", lambda t: (t[0] @ t[1]).relu().sum(),
         [Tensor.randn(3, 4, rng=rng), Tensor.randn(4, 2, rng=rng)]),
        ("tanh/mean", lambda t: t[0].tanh().mean(),
         [Tensor.randn(4, 5, rng=rng)]),
        ("exp/log", lambda t: t[0].exp().log().sum(),
         [Tensor.randn(3, 3, rng=rng)]),
        ("transpose", lambda t: (t[0].transpose() @ t[0]).sum(),
         [Tensor.randn(3, 2, rng=rng)]),
    ]
    for label, build, inputs in cases:
        ok, worst = check_gradient(build, inputs)
        assert ok, (
            f"the gradient of `{label}` disagrees with central differences by "
            f"{worst:.2e}. numeric_gradient is the oracle here: an analytic "
            "gradient that is subtly wrong still TRAINS, just worse, so this "
            "comparison is the only thing that catches it.")


def check_accumulation() -> None:
    from tensor import Tensor, check_gradient

    ok, worst = check_gradient(lambda t: (t[0] * t[0] + t[0]).sum(),
                               [Tensor.randn(3, 3, rng=random.Random(1))])
    assert ok, (
        f"a tensor used TWICE has a gradient error of {worst:.2e}. Its gradient "
        "is the SUM of both contributions, and a node's _backward must not run "
        "until every child has contributed — that is what the topological sort "
        "is for. Get it wrong and nothing crashes; the model just trains a "
        "little worse, forever.")

    w = Tensor([2.0], requires_grad=True)
    (w * w).backward()
    first = w.grad[0]
    (w * w).backward()
    assert abs(w.grad[0] - 2 * first) < 1e-12, (
        f"after two backward passes grad is {w.grad[0]}, expected {2 * first}. "
        "Gradients must ACCUMULATE. The engine cannot know where one training "
        "step ended, which is exactly why training loops call zero_grad().")
    w.zero_grad()
    (w * w).backward()
    assert abs(w.grad[0] - first) < 1e-12, "zero_grad must actually clear it"

    batch = Tensor.from_rows([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
                             requires_grad=True)
    bias = Tensor([0.5, -0.5], (1, 2), requires_grad=True)
    (batch + bias).sum().backward()
    assert bias.grad == [3.0, 3.0], (
        f"the bias gradient is {bias.grad}, expected [3.0, 3.0]. Each bias "
        "element was used once per row, so it receives one contribution per "
        "row and they must be SUMMED. Skip that fold and every bias gradient "
        "is a factor of batch_size too small — the loss still goes down, which "
        "is what makes it hard to find.")


def check_cross_entropy() -> None:
    from tensor import Tensor, check_gradient

    logits = Tensor([0.0, 0.0, 0.0, 0.0], (1, 4))
    loss = logits.softmax_cross_entropy([2])
    assert abs(loss.item() - math.log(4)) < 1e-9, (
        f"uniform logits over 4 classes should give log(4) = {math.log(4):.4f}, "
        f"got {loss.item():.4f}")

    confident = Tensor([0.0, 0.0, 20.0, 0.0], (1, 4))
    assert confident.softmax_cross_entropy([2]).item() < 1e-6
    assert confident.softmax_cross_entropy([0]).item() > 15

    huge = Tensor([1000.0, 999.0], (1, 2))
    value = huge.softmax_cross_entropy([0]).item()
    assert math.isfinite(value), (
        "logits of 1000 overflowed. exp(1000) is inf, so softmax must subtract "
        "the row maximum first. This is half the reason softmax and cross "
        "entropy are fused rather than composed.")

    ok, worst = check_gradient(
        lambda t: t[0].softmax_cross_entropy([0, 2, 1]),
        [Tensor.randn(3, 4, rng=random.Random(2))])
    assert ok, (
        f"cross-entropy gradient off by {worst:.2e}. Fused, it is simply "
        "softmax(x) - onehot(y) — the other half of why the two are one "
        "operation.")

    probabilities = Tensor([0.7, 0.2, 0.1], (1, 3))
    logits_version = Tensor([math.log(0.7), math.log(0.2), math.log(0.1)], (1, 3))
    assert abs(probabilities.softmax_cross_entropy([0]).item()
               - logits_version.softmax_cross_entropy([0]).item()) > 0.1, (
        "passing probabilities where logits are expected must give a DIFFERENT "
        "answer — it applies softmax twice. If they agree, softmax is not "
        "being applied inside the loss at all.")


# ---------------------------------------------------------------------------
# nn
# ---------------------------------------------------------------------------

def check_layers() -> None:
    from nn import Linear, ReLU, Sequential, Tanh, init_scale
    from tensor import Tensor, check_gradient

    layer = Linear(4, 3, rng=random.Random(0))
    out = layer(Tensor.randn(5, 4, rng=random.Random(1)))
    assert out.shape == (5, 3), f"got {out.shape}"
    assert len(layer.parameters()) == 2, "weight and bias"

    model = Sequential(Linear(4, 6, rng=random.Random(2)), ReLU(),
                       Linear(6, 3, activation="linear", rng=random.Random(3)))
    assert len(model.parameters()) == 4, (
        f"{len(model.parameters())} parameter tensors found, expected 4. "
        "parameters() must recurse into child modules AND into lists of them — "
        "a parameter it misses is one the optimiser never updates, and there is "
        "no error, just a network that plateaus early.")
    assert model.num_parameters() == 4 * 6 + 6 + 6 * 3 + 3

    assert abs(init_scale(100, "relu") - math.sqrt(2 / 100)) < 1e-12, (
        "He init is sqrt(2/fan_in); the 2 pays back the half of the signal "
        "that ReLU throws away")
    assert abs(init_scale(100, "tanh") - math.sqrt(1 / 100)) < 1e-12

    zeroed = Linear(8, 8, rng=random.Random(4))
    zeroed.weight = Tensor([0.0] * 64, (8, 8), requires_grad=True)
    activations = zeroed(Tensor.randn(2, 8, rng=random.Random(5))).relu()
    assert len(set(activations.data)) == 1, (
        "a zero-initialised layer must produce identical outputs for every "
        "unit — that is precisely why zeros are a catastrophic init: every "
        "unit computes the same thing and receives the same gradient forever")

    def build(tensors):
        small = Sequential(Linear(3, 4, rng=random.Random(6)), Tanh(),
                           Linear(4, 3, activation="linear",
                                  rng=random.Random(7)))
        small.layers[0].weight = tensors[0]
        small.layers[2].weight = tensors[1]
        return small(tensors[2]).softmax_cross_entropy([0, 2])

    rng = random.Random(8)
    ok, worst = check_gradient(build, [Tensor.randn(3, 4, rng=rng),
                                       Tensor.randn(4, 3, rng=rng),
                                       Tensor.randn(2, 3, rng=rng)])
    assert ok, f"gradients through a two-layer model are off by {worst:.2e}"

    # Stacked Linear with no activation is exactly one Linear.
    stack = Sequential(*[Linear(5, 5, activation="linear",
                                rng=random.Random(n)) for n in range(4)])
    x = Tensor.randn(1, 5, rng=random.Random(20))
    collapsed = stack.layers[0].weight
    for layer in stack.layers[1:]:
        collapsed = collapsed @ layer.weight
    for a, b in zip(stack(x).data, (x @ collapsed).data):
        assert abs(a - b) < 1e-9, (
            "four stacked Linear layers with no bias and no activation must be "
            "identical to the single matrix product of their weights. If they "
            "differ, forward() is not simply x @ W per layer.")


def check_dropout() -> None:
    from nn import Dropout, Linear, Sequential, train_mode
    from tensor import Tensor

    layer = Dropout(0.5, rng=random.Random(0))
    x = Tensor.full(1.0, 1, 4000)

    layer.training = True
    trained = layer(x)
    zeros = trained.data.count(0.0)
    assert 1600 < zeros < 2400, f"{zeros} of 4000 zeroed at p=0.5"
    mean = sum(trained.data) / len(trained.data)
    assert abs(mean - 1.0) < 0.08, (
        f"training-time mean is {mean:.3f}, expected ~1.0. Inverted dropout "
        "scales the surviving activations by 1/keep so the expected value is "
        "unchanged. Without it, inference sees activations twice as large as "
        "the next layer was trained for.")

    layer.training = False
    assert layer(x).data == x.data, "at eval, dropout is the identity"

    model = Sequential(Linear(4, 4, rng=random.Random(1)),
                       Dropout(0.5, rng=random.Random(2)))
    train_mode(model, False)
    assert model.layers[1].training is False, (
        "train_mode must reach Dropout modules inside a Sequential. Forgetting "
        "to switch it off is the classic 'eval accuracy is worse than training "
        "accuracy for no reason'.")


# ---------------------------------------------------------------------------
# optim
# ---------------------------------------------------------------------------

def check_optimizers() -> None:
    from optim import Adam, RMSProp, SGD
    from tensor import Tensor

    p = Tensor([1.0], requires_grad=True)
    optimizer = SGD([p], lr=0.1)
    p.grad = [2.0]
    optimizer.step()
    assert abs(p.data[0] - 0.8) < 1e-12, (
        f"p is {p.data[0]}, expected 0.8: p -= lr * g is 1.0 - 0.1*2.0")

    p = Tensor([1.0], requires_grad=True)
    optimizer = SGD([p], lr=0.1, momentum=0.9)
    for _ in range(2):
        p.grad = [1.0]
        optimizer.step()
    assert abs(p.data[0] - (1.0 - 0.1 - 0.19)) < 1e-9, (
        f"p is {p.data[0]}. With momentum 0.9 and a constant gradient, the "
        "velocity grows: 1.0 then 1.9, so the steps are 0.1 then 0.19. "
        "Momentum ACCUMULATES a consistent gradient — that is the whole point.")

    def descend(make, steps=80):
        q = Tensor([2.0, 2.0], requires_grad=True)
        optimizer = make([q])
        for _ in range(steps):
            optimizer.zero_grad()
            (q * q * Tensor([0.5, 20.0], (2,))).sum().backward()
            optimizer.step()
        return abs(q.data[0])

    plain = descend(lambda p: SGD(p, lr=0.02))
    momentum = descend(lambda p: SGD(p, lr=0.02, momentum=0.9))
    assert momentum < plain / 5, (
        f"after 80 steps in the ravine, |x| is {plain:.4f} with plain SGD and "
        f"{momentum:.4f} with momentum. Momentum should be much further along "
        "the shallow direction: it cancels the oscillating component (which "
        "flips sign each step) and accumulates the consistent one.")

    for label, make in (("RMSProp", lambda p: RMSProp(p, lr=0.1)),
                        ("Adam", lambda p: Adam(p, lr=0.1))):
        assert descend(make) < plain, (
            f"{label} did not beat plain SGD on the ravine. Both rescale each "
            "coordinate by its own gradient history, which is the other way to "
            "fix a single learning rate suiting only one direction.")

    # Adam's first corrected step is exactly the learning rate.
    p = Tensor([1.0], requires_grad=True)
    Adam([p], lr=0.01, bias_correction=True)
    optimizer = Adam([p], lr=0.01, bias_correction=True)
    p.grad = [5.0]
    optimizer.step()
    assert abs(abs(p.data[0] - 1.0) - 0.01) < 1e-6, (
        f"Adam's first step moved {abs(p.data[0] - 1.0):.6f}, expected exactly "
        "the learning rate 0.01. With bias correction, m_hat/sqrt(v_hat) is "
        "exactly 1 on step one whatever the gradient. Without the correction "
        "it comes out ~3.16x too LARGE — note the direction, the usual summary "
        "gets it backwards.")


def check_clipping_and_schedule() -> None:
    from optim import Adam, clip_grad_norm, cosine_schedule
    from tensor import Tensor

    a = Tensor([3.0, 4.0], requires_grad=True)
    b = Tensor([12.0], requires_grad=True)
    a.grad, b.grad = [3.0, 4.0], [12.0]
    norm = clip_grad_norm([a, b], max_norm=1.0)
    assert abs(norm - 13.0) < 1e-9, (
        f"the reported norm is {norm}, expected 13.0 = sqrt(9+16+144). It is "
        "the GLOBAL norm across every parameter, not per tensor.")
    new_norm = math.sqrt(sum(g * g for g in a.grad + b.grad))
    assert abs(new_norm - 1.0) < 1e-9, f"clipped norm is {new_norm}"
    assert abs(a.grad[1] / a.grad[0] - 4 / 3) < 1e-9, (
        "clipping must preserve the DIRECTION. Scaling tensors independently "
        "changes it, which makes it a different optimiser rather than the same "
        "one taking a shorter step.")

    a.grad, b.grad = [0.1, 0.1], [0.1]
    before = list(a.grad)
    clip_grad_norm([a, b], max_norm=10.0)
    assert a.grad == before, "a norm below the threshold must be left alone"

    assert abs(cosine_schedule(0, 100, 1e-3, warmup=10) - 1e-4) < 1e-12, (
        "step 0 of a 10-step warmup is 1/10 of the base rate")
    assert abs(cosine_schedule(9, 100, 1e-3, warmup=10) - 1e-3) < 1e-12
    assert cosine_schedule(99, 100, 1e-3, warmup=10, min_lr=1e-5) < 1e-4
    middle = cosine_schedule(55, 100, 1e-3, warmup=10)
    assert 1e-4 < middle < 1e-3, "cosine decay is monotonic in between"


# ---------------------------------------------------------------------------
# train
# ---------------------------------------------------------------------------

def check_training() -> None:
    import digits
    from nn import Sequential
    from tensor import Tensor
    from train import accuracy, build_mlp, confusion, overfit_check, train
    from optim import Adam

    model = build_mlp((16,), seed=0)
    assert isinstance(model, Sequential)
    assert model.num_parameters() == 64 * 16 + 16 + 16 * 10 + 10

    xs, ys = digits.make_dataset(200, noise=0.1, seed=0)
    xs = digits.normalize(xs)

    loss = overfit_check(build_mlp((32,), seed=1), xs[:10], ys[:10], steps=250)
    assert loss < 0.05, (
        f"the model could not memorise ten examples — loss {loss:.4f}. That is "
        "a plumbing failure, not a tuning one: gradients are not flowing, or a "
        "parameter is not registered, or the loss is not connected to the "
        "output. This is the first check to run on any new model.")

    (train_x, train_y), (test_x, test_y) = digits.split(xs, ys)
    model = build_mlp((32,), seed=2)
    before = accuracy(model, test_x, test_y)
    history = train(model, train_x, train_y, test_x, test_y,
                    Adam(model.parameters(), lr=0.01), epochs=6, batch_size=16)
    after = history["test_acc"][-1]
    assert 0.0 <= before <= 0.35, f"an untrained model scored {before:.1%}"
    assert after > 0.75, (
        f"after six epochs the model scores {after:.1%} on held-out data. "
        "These digits are easy; anything under 75% means the loop is not "
        "actually updating parameters — check that optimizer.step() runs and "
        "that zero_grad() is called BEFORE backward, not after.")
    assert len(history["loss"]) == 6
    assert history["loss"][-1] < history["loss"][0], "the loss must go down"

    matrix = confusion(model, test_x, test_y)
    assert sum(sum(row) for row in matrix) == len(test_y)
    assert sum(matrix[d][d] for d in range(10)) / len(test_y) == after, (
        "the confusion matrix diagonal must agree with the reported accuracy")


# ---------------------------------------------------------------------------
# generative
# ---------------------------------------------------------------------------

def check_generative() -> None:
    import digits
    from generative import (Autoencoder, VAE, sample_prior, sharpness,
                            train_autoencoder, train_vae)
    from tensor import Tensor

    xs, _ = digits.make_dataset(200, noise=0.1, seed=0)
    xs = digits.normalize(xs)

    auto = Autoencoder(hidden=16, latent=4, seed=0)
    history = train_autoencoder(auto, xs, epochs=12)
    assert history[-1] < history[0] * 0.6, (
        f"reconstruction loss went {history[0]:.4f} -> {history[-1]:.4f}; it "
        "should fall substantially")
    encoded = auto.encode(Tensor.from_rows(xs[:20]))
    assert encoded.shape == (20, 4), f"encode gave {encoded.shape}"
    assert auto.decode(encoded).shape == (20, digits.PIXELS)

    vae = VAE(hidden=16, latent=4, seed=0)
    mu, log_var = vae.encode(Tensor.from_rows(xs[:8]))
    assert mu.shape == log_var.shape == (8, 4), (
        "the encoder must produce a mean AND a log-variance, both (batch, "
        "latent). Predicting log-variance rather than variance is what "
        "guarantees positivity for free.")

    rng = random.Random(0)
    z1 = vae.reparameterize(mu, log_var, random.Random(1))
    z2 = vae.reparameterize(mu, log_var, random.Random(2))
    assert z1.data != z2.data, "reparameterize must actually be stochastic"
    assert z1.shape == (8, 4)

    zero_var = Tensor([-40.0] * 32, (8, 4))
    almost_mu = vae.reparameterize(mu, zero_var, random.Random(3))
    for a, b in zip(almost_mu.data, mu.data):
        assert abs(a - b) < 1e-6, (
            "with log_var very negative the noise term vanishes and z must "
            "equal mu. z = mu + exp(log_var/2) * eps — if this fails, eps is "
            "being added unscaled.")

    # The SCALE of the noise, which the vanishing test above cannot see:
    # exp(-40) and exp(-20) are both zero to a computer, so a missing /2 slips
    # straight through it. Measure the spread where the two answers differ:
    # exp(2/2) = 2.72 against exp(2) = 7.39.
    fixed_mu = Tensor([0.0] * 400, (100, 4))
    fixed_log_var = Tensor([2.0] * 400, (100, 4))
    draws = vae.reparameterize(fixed_mu, fixed_log_var, random.Random(11)).data
    spread = math.sqrt(sum(v * v for v in draws) / len(draws))
    assert abs(spread - math.exp(1.0)) < 0.4, (
        f"with log_var = 2 the noise has standard deviation {spread:.2f}; it "
        f"must be exp(log_var/2) = {math.exp(1.0):.2f}, not "
        f"{math.exp(2.0):.2f}. log_var is a LOG VARIANCE and the standard "
        "deviation is the square root of the variance, so the exponent is "
        "halved. Miss the /2 and every sample is far too spread out, while "
        "the KL term is computed against a distribution the sampler is not "
        "actually using.")

    loss, recon, kl = vae.loss(Tensor.from_rows(xs[:8]), rng, beta=1.0)
    assert kl >= -1e-9, f"KL divergence cannot be negative, got {kl}"
    loss.backward()
    assert vae.to_mu.weight.grad is not None, (
        "no gradient reached the mean head. The reparameterisation trick "
        "exists exactly so that it can: eps must be a CONSTANT tensor drawn "
        "outside the graph, so z is a differentiable function of mu.")
    assert vae.decoder.layers[0].weight.grad is not None

    zero_beta_loss, _, _ = vae.loss(Tensor.from_rows(xs[:8]),
                                    random.Random(4), beta=0.0)
    full_beta_loss, _, _ = vae.loss(Tensor.from_rows(xs[:8]),
                                    random.Random(4), beta=1.0)
    assert full_beta_loss.item() > zero_beta_loss.item(), (
        "beta must actually weight the KL term — at beta=0 the loss is "
        "reconstruction only, which is an autoencoder")

    # What the KL term does is checkable and deterministic: train the same
    # architecture at two betas and the reported KL must differ sharply.
    loose = VAE(hidden=16, latent=4, seed=1)
    loose_history = train_vae(loose, xs, epochs=15, beta=0.0)
    tight = VAE(hidden=16, latent=4, seed=1)
    tight_history = train_vae(tight, xs, epochs=15, beta=3.0)
    assert loose_history[-1][1] > tight_history[-1][1] * 5, (
        f"KL after training is {loose_history[-1][1]:.4f} at beta=0 and "
        f"{tight_history[-1][1]:.4f} at beta=3. Beta must actually control how "
        "hard the codes are pulled towards N(0, I) — at beta=0 nothing does, "
        "which is what makes it an autoencoder, and at beta=3 the KL should be "
        "driven towards zero.")
    assert tight_history[-1][0] > loose_history[-1][0], (
        "and the trade must go the other way too: a large beta costs "
        "reconstruction quality. If reconstruction improved as well, the KL "
        "term is not connected to the loss at all.")

    samples = sample_prior(tight, 8, random.Random(5))
    assert samples.shape == (8, digits.PIXELS)
    real = sum(sharpness(x) for x in xs[:40]) / 40
    assert real > 0, "sharpness should be positive on real data"
    # Deliberately NOT asserted: that VAE samples look better than an
    # autoencoder's. At this scale that comparison is genuinely noisy — an
    # autoencoder's noise can happen to score closer to the data on any single
    # summary statistic — and a checker that fails on a lucky seed teaches you
    # to ignore checkers. The demo measures it with context instead.


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [

    ("tensor.py", "shapes, matmul, broadcasting", check_forward),
    ("tensor.py", "backward, against numerical gradients", check_backward),
    ("tensor.py", "accumulation, and unbroadcasting", check_accumulation),
    ("tensor.py", "fused softmax cross-entropy", check_cross_entropy),
    ("nn.py", "modules, init, and why depth needs a kink", check_layers),
    ("nn.py", "dropout, and the scaling that hides it", check_dropout),
    ("optim.py", "SGD, momentum, RMSProp, Adam", check_optimizers),
    ("optim.py", "clipping and schedules", check_clipping_and_schedule),
    ("train.py", "the loop, and the overfit check first", check_training),
    ("generative.py", "autoencoder, VAE, and the KL term",
     check_generative),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:                       # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}Autograd From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None

    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<16} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<16} {title}")
            print(f"      {GREY}not implemented yet"
                  f"{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<16} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")

    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()

    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you built a deep learning "
              f"framework.{RESET}")
        print(f"  {GREY}Now run each file's own demo to see the measurements,"
              f"{RESET}")
        print(f"  {GREY}then compare your approach with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. "
              f"Stuck? solutions/{filename}{RESET}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
