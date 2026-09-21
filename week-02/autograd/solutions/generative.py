"""
generative — learning to WRITE digits instead of read them. Complete Solution.

A classifier maps an image to a label: 64 numbers in, 10 out, and it throws
away everything it did not need. A generative model goes the other way — it has
to represent what a digit IS well enough to produce one that was never in the
training set.

This file builds it in the repo's usual order: the MVP first, then the limit
case that forces the complication.

  1. An AUTOENCODER. Squeeze the image through a narrow bottleneck and
     reconstruct it. It works, and reconstructions are good.
  2. The limit case: SAMPLE from the bottleneck and decode. You get noise.
     Nothing ever asked the latent space to be shaped like anything, so almost
     every point in it decodes to garbage — the model only learned what to do
     at the handful of points its training images happened to land on.
  3. A VAE fixes exactly that, by adding one term to the loss that pulls the
     latent distribution towards a standard normal. Now sampling works.

DESIGN DECISION — what makes a model "generative" rather than compressive?
  Both an autoencoder and a VAE have an encoder, a bottleneck and a decoder.
  The difference is entirely in the LOSS: a VAE adds a KL term that says "the
  distribution of codes must look like N(0, I)". That is what makes the latent
  space samplable, and it is the whole of the difference. Section 2 measures
  the gap by sampling from both.

DESIGN DECISION — how do you backpropagate through a random sample?
  You cannot. `z = sample(N(mu, sigma))` has no derivative with respect to mu:
  the sampling is a coin flip and coin flips have no gradient.
  CHOSEN: the REPARAMETERISATION TRICK. Draw the randomness OUTSIDE the
  computation — `eps ~ N(0, 1)` — and write `z = mu + sigma * eps`. Now z is a
  deterministic, differentiable function of mu and sigma, with eps as a
  constant input. The randomness is still there; it just moved somewhere the
  chain rule does not have to pass through.
  This one idea is why VAEs are trainable at all, and it is why the code below
  builds `eps` as a plain Tensor with no gradient rather than sampling inside
  the graph.

DESIGN DECISION — how much weight on the KL term?
  It trades reconstruction against samplability, and both ends are bad:
  beta = 0 is an autoencoder whose samples are noise; a large beta gives
  "posterior collapse", where the encoder outputs N(0, I) for every input, the
  KL term is perfectly zero, and the decoder produces the same blurry average
  digit for everything. Section 4 sweeps beta and shows both failures.
"""

import math
import random
from typing import List, Optional, Sequence, Tuple

import digits
from nn import Linear, Module, ReLU, Sequential, Tanh
from optim import Adam
from tensor import Tensor


class Autoencoder(Module):
    """Encode to `latent` numbers, decode back. No constraint on the code."""

    def __init__(self, hidden: int = 24, latent: int = 6, seed: int = 0):
        rng = random.Random(seed)
        self.latent = latent
        self.encoder = Sequential(
            Linear(digits.PIXELS, hidden, activation="tanh", rng=rng), Tanh(),
            Linear(hidden, latent, activation="linear", rng=rng))
        self.decoder = Sequential(
            Linear(latent, hidden, activation="tanh", rng=rng), Tanh(),
            Linear(hidden, digits.PIXELS, activation="linear", rng=rng))

    def forward(self, x: Tensor) -> Tensor:
        return self.decoder(self.encoder(x))

    def encode(self, x: Tensor) -> Tensor:
        return self.encoder(x)

    def decode(self, z: Tensor) -> Tensor:
        return self.decoder(z)


class VAE(Module):
    """An autoencoder whose encoder outputs a DISTRIBUTION, not a point.

    `mu` and `log_var` come from the same trunk. Predicting log-variance rather
    than variance is not cosmetic: variance must be positive, and a network's
    output is not. Exponentiating a free-valued output guarantees positivity for
    nothing, and it makes the KL term numerically well behaved besides.
    """

    def __init__(self, hidden: int = 24, latent: int = 6, seed: int = 0):
        rng = random.Random(seed)
        self.latent = latent
        self.trunk = Sequential(
            Linear(digits.PIXELS, hidden, activation="tanh", rng=rng), Tanh())
        self.to_mu = Linear(hidden, latent, activation="linear", rng=rng)
        self.to_log_var = Linear(hidden, latent, activation="linear", rng=rng)
        self.decoder = Sequential(
            Linear(latent, hidden, activation="tanh", rng=rng), Tanh(),
            Linear(hidden, digits.PIXELS, activation="linear", rng=rng))

    def encode(self, x: Tensor) -> Tuple[Tensor, Tensor]:
        h = self.trunk(x)
        return self.to_mu(h), self.to_log_var(h)

    def reparameterize(self, mu: Tensor, log_var: Tensor,
                       rng: random.Random) -> Tensor:
        """z = mu + exp(log_var / 2) * eps, with eps drawn OUTSIDE the graph.

        `eps` is a constant tensor with `requires_grad=False`, so the chain rule
        never has to differentiate the sampling. Everything random happens
        before the graph starts, and z is then a smooth function of mu and
        log_var. That is the entire trick.
        """
        eps = Tensor([rng.gauss(0.0, 1.0) for _ in mu.data], mu.shape)
        return mu + (log_var * 0.5).exp() * eps

    def decode(self, z: Tensor) -> Tensor:
        return self.decoder(z)

    def forward(self, x: Tensor, rng: Optional[random.Random] = None) -> Tensor:
        mu, log_var = self.encode(x)
        return self.decode(self.reparameterize(mu, log_var,
                                               rng or random.Random(0)))

    def loss(self, x: Tensor, rng: random.Random, beta: float = 1.0
             ) -> Tuple[Tensor, float, float]:
        """Reconstruction + beta * KL, and both halves reported separately.

        Watching the two terms individually is the only way to diagnose a VAE.
        A KL that collapses to zero means the encoder gave up and is emitting
        N(0, I) for every input; a KL that grows without bound means it is
        smuggling information through by pushing the codes far apart, and your
        samples will be as bad as an autoencoder's.
        """
        mu, log_var = self.encode(x)
        z = self.reparameterize(mu, log_var, rng)
        reconstruction = self.decode(z)

        difference = reconstruction - x
        recon_loss = (difference * difference).mean()

        # KL(N(mu, sigma) || N(0, I)) = -0.5 * sum(1 + log_var - mu^2 - var)
        kl_terms = (Tensor([1.0], (1,)) + log_var
                    - mu * mu - log_var.exp()) * -0.5
        kl = kl_terms.mean()

        return recon_loss + kl * beta, recon_loss.item(), kl.item()


def train_autoencoder(model: Autoencoder, xs: List[List[float]],
                      epochs: int = 20, batch_size: int = 32, lr: float = 0.01,
                      seed: int = 0) -> List[float]:
    optimizer = Adam(model.parameters(), lr=lr)
    rng = random.Random(seed)
    history = []
    for _ in range(epochs):
        total, count = 0.0, 0
        order = list(range(len(xs)))
        rng.shuffle(order)
        for start in range(0, len(order) - batch_size + 1, batch_size):
            batch = Tensor.from_rows([xs[i] for i in
                                      order[start:start + batch_size]])
            optimizer.zero_grad()
            out = model(batch)
            difference = out - batch
            loss = (difference * difference).mean()
            loss.backward()
            optimizer.step()
            total += loss.item()
            count += 1
        history.append(total / max(1, count))
    return history


def train_vae(model: VAE, xs: List[List[float]], epochs: int = 20,
              batch_size: int = 32, lr: float = 0.01, beta: float = 1.0,
              seed: int = 0) -> List[Tuple[float, float]]:
    optimizer = Adam(model.parameters(), lr=lr)
    rng = random.Random(seed)
    history = []
    for _ in range(epochs):
        recon_total, kl_total, count = 0.0, 0.0, 0
        order = list(range(len(xs)))
        rng.shuffle(order)
        for start in range(0, len(order) - batch_size + 1, batch_size):
            batch = Tensor.from_rows([xs[i] for i in
                                      order[start:start + batch_size]])
            optimizer.zero_grad()
            loss, recon, kl = model.loss(batch, rng, beta)
            loss.backward()
            optimizer.step()
            recon_total += recon
            kl_total += kl
            count += 1
        history.append((recon_total / max(1, count), kl_total / max(1, count)))
    return history


def sample_prior(model, count: int, rng: random.Random) -> Tensor:
    """Draw z ~ N(0, I) and decode. This is the test of a generative model.

    An autoencoder will do this too — it has a decoder — and what comes out is
    the measurement that matters, because it shows whether the latent space has
    any structure away from the training points.
    """
    z = Tensor([rng.gauss(0.0, 1.0) for _ in range(count * model.latent)],
               (count, model.latent))
    return model.decode(z)


def _std(values: Sequence[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def _mean_nearest(codes: Sequence[Sequence[float]], latent: int,
                  draws: int = 60, seed: int = 42) -> float:
    """Average distance from a random N(0, I) draw to the nearest real code.

    This is the direct measurement of "does the latent space have holes". A
    marginal standard deviation near 1 says nothing about whether the codes
    COVER the space or sit in a few tight clusters with emptiness between them,
    and the emptiness is what makes sampling fail.
    """
    rng = random.Random(seed)
    total = 0.0
    for _ in range(draws):
        point = [rng.gauss(0.0, 1.0) for _ in range(latent)]
        total += min(math.sqrt(sum((a - b) ** 2 for a, b in zip(point, code)))
                     for code in codes)
    return total / draws


def sharpness(image: Sequence[float]) -> float:
    """Mean absolute difference between neighbouring pixels.

    A crude proxy for "does this look like a drawing rather than a smear", and
    it is enough to separate the two failure modes numerically instead of by
    squinting: real digits have edges, blurry averages do not, and noise has
    far too many.
    """
    total, count = 0.0, 0
    for y in range(digits.HEIGHT):
        for x in range(digits.WIDTH - 1):
            total += abs(image[y * digits.WIDTH + x]
                         - image[y * digits.WIDTH + x + 1])
            count += 1
    return total / count


def _demo() -> None:
    print("=" * 76)
    print("generative — an autoencoder, its failure, and the term that fixes it")
    print("=" * 76)

    xs, ys = digits.make_dataset(400, noise=0.1, seed=0)
    xs = digits.normalize(xs)
    print(f"\n  {len(xs)} images, {digits.PIXELS} pixels, "
          f"squeezed through a {6}-number bottleneck")
    print("  (this file trains four small models; give it a minute)")

    print("\n1. The MVP: an autoencoder reconstructs well")
    print("-" * 76)
    auto = Autoencoder(hidden=24, latent=6, seed=1)
    history = train_autoencoder(auto, xs, epochs=25)
    print(f"  reconstruction MSE: {history[0]:.4f} -> {history[-1]:.4f} "
          f"over 25 epochs")
    originals = [xs[i] for i in range(4)]
    reconstructed = auto(Tensor.from_rows(originals)).rows()
    print("\n  original above, reconstruction below:")
    print(digits.side_by_side(originals, [ys[i] for i in range(4)]))
    print(digits.side_by_side(reconstructed, ["recon"] * 4))
    print(f"\n  Six numbers per image, down from {digits.PIXELS}. The model")
    print("  learned a compression, and it is a good one.")

    print("\n2. The limit case: sample from that bottleneck")
    print("-" * 76)
    rng = random.Random(7)
    samples = sample_prior(auto, 4, rng).rows()
    print(digits.side_by_side(samples, ["?"] * 4))
    print("  Noise. The decoder was only ever asked what to do at the ~400")
    print("  points the training images happened to encode to; everywhere else")
    print("  in that 6-dimensional space is undefined, and a random draw lands")
    print("  nowhere near any of them. Nothing in the loss ever mentioned the")
    print("  SHAPE of the latent space, so it has none.")

    print(f"\n  {'model':<14}{'code std':>10}{'draw -> nearest real code':>28}")
    for label, encode in (("autoencoder",
                           lambda: auto.encode(Tensor.from_rows(xs[:200]))),
                          ("VAE (below)", None)):
        if encode is None:
            continue
        codes = encode().rows()
        std = _std([v for row in codes for v in row])
        print(f"  {label:<14}{std:>10.2f}{_mean_nearest(codes, 6):>28.2f}")
    print("  Two numbers, and the second is the important one. The codes are")
    print("  spread about twice as wide as N(0, I), which is bad enough — but")
    print("  the measurement that explains the noise is the second column:")
    print("  draw from N(0, I) and ask how far the nearest code the model has")
    print("  ACTUALLY seen is. The codes sit in clusters, a random draw lands")
    print("  in the emptiness between them, and the decoder has never been")
    print("  asked anything there. Compare this pair against the VAE's below.")

    print("\n3. The fix: one extra term in the loss")
    print("-" * 76)
    vae = VAE(hidden=24, latent=6, seed=1)
    # beta=0.3, not 1.0. At beta=1 this small model already loses most of
    # its latent information (section 4 shows the KL near zero); 0.3 is
    # where reconstruction and samplability are both usable here.
    vae_history = train_vae(vae, xs, epochs=25, beta=0.3)
    print(f"    {'epoch':>7}{'reconstruction':>17}{'KL':>10}")
    for epoch in (0, 4, 12, 24):
        recon, kl = vae_history[epoch]
        print(f"    {epoch + 1:>7}{recon:>17.4f}{kl:>10.4f}")

    codes = vae.encode(Tensor.from_rows(xs[:200]))[0].rows()
    flat = [v for row in codes for v in row]
    print(f"\n  {'VAE':<14}{_std(flat):>10.2f}{_mean_nearest(codes, 6):>28.2f}")
    print(f"  mean {sum(flat) / len(flat):.2f}, against a target of 0.00 and a")
    print("  target std of 1.00 — and the distance from a random draw to the")
    print("  nearest real code has fallen by a third. The space is FILLED, so")
    print("  wherever you sample, the decoder has seen somewhere close by.")
    print("  That is the whole of what the KL term bought.")

    samples = sample_prior(vae, 4, random.Random(7)).rows()
    print("\n  samples from N(0, I), decoded:")
    print(digits.side_by_side(samples, ["~"] * 4))
    print("  Digit-shaped — blurry, but structured, and none of them is in the")
    print("  training set. The KL term is the entire difference: it pulls every")
    print("  image's code towards N(0, I), so the region you sample from is the")
    print("  region the decoder was trained on.")
    print("  Be honest about the blur, because it is not a bug in this")
    print("  implementation — it is what VAEs do. A squared-error reconstruction")
    print("  loss is a Gaussian likelihood, and when several digits are")
    print("  plausible for one code the loss is minimised by their AVERAGE")
    print("  rather than by picking one. GANs and diffusion models exist")
    print("  largely because of that single property.")

    print("\n4. Beta: reconstruction against samplability")
    print("-" * 76)
    print(f"    {'beta':>6}{'reconstruction':>17}{'KL':>9}{'sample sharpness':>19}"
          f"   what happened")
    reference = sum(sharpness(x) for x in xs[:50]) / 50
    for beta in (0.0, 0.3, 1.0, 30.0):
        model = VAE(hidden=24, latent=6, seed=2)
        history = train_vae(model, xs, epochs=20, beta=beta)
        recon, kl = history[-1]
        drawn = sample_prior(model, 12, random.Random(3)).rows()
        sharp = sum(sharpness(image) for image in drawn) / len(drawn)
        if kl > 3.0:
            verdict = "codes scattered; samples are noise"
        elif kl < 0.05:
            verdict = "posterior collapse; one blurry average"
        else:
            verdict = "usable"
        print(f"    {beta:>6.1f}{recon:>17.4f}{kl:>9.4f}{sharp:>19.4f}"
              f"   {verdict}")
    print(f"    {'real':>6}{'—':>17}{'—':>9}{reference:>19.4f}   the data itself")
    print("  Both ends fail, differently. At beta=0 it is an autoencoder and")
    print("  its samples are noise — note the sharpness ABOVE the real data,")
    print("  which is what noise looks like numerically. At beta=30 the KL is")
    print("  driven to zero: the encoder emits N(0, I) for every input, carries")
    print("  no information, and the decoder produces one blurry average for")
    print("  everything — sharpness far BELOW the real data.")
    print("  Two failure modes, opposite signs, one number telling them apart.")

    print("\n5. Walking the latent space")
    print("-" * 76)
    a_mu, _ = vae.encode(Tensor.from_rows([xs[0]]))
    b_index = next(i for i in range(1, len(xs)) if ys[i] != ys[0])
    b_mu, _ = vae.encode(Tensor.from_rows([xs[b_index]]))
    steps = []
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        blended = [a * (1 - t) + b * t for a, b in zip(a_mu.data, b_mu.data)]
        steps.append(vae.decode(Tensor(blended, (1, 6))).data)
    print(digits.side_by_side(steps, [ys[0], "", "", "", ys[b_index]]))
    print("  Every intermediate point decodes to something digit-like. That is")
    print("  what 'the latent space is continuous' means, and it is a property")
    print("  the KL term produced — the autoencoder's space has holes between")
    print("  its training points, which is exactly why sampling failed there.")

    print("\n" + "=" * 76)
    print("You built the autograd, the layers, the optimiser and the model.")
    print("Nothing above imported a framework.")
    print("=" * 76)


if __name__ == "__main__":
    _demo()
