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

Learning Path — this file is the MVP-then-limit-case ladder in miniature:
1. Autoencoder, and train_autoencoder. It reconstructs well.
2. sample_prior on it. Noise — that is the limit case.
3. VAE.encode / reparameterize / decode. The trick is that eps is drawn
   OUTSIDE the graph, so nothing has to differentiate a coin flip.
4. VAE.loss — reconstruction plus KL, and report BOTH halves separately or you
   cannot diagnose it
5. Sweep beta and find both failure modes
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
        raise NotImplementedError

    def encode(self, x: Tensor) -> Tensor:
        raise NotImplementedError

    def decode(self, z: Tensor) -> Tensor:
        raise NotImplementedError


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
        raise NotImplementedError

    def reparameterize(self, mu: Tensor, log_var: Tensor,
                       rng: random.Random) -> Tensor:
        """z = mu + exp(log_var / 2) * eps, with eps drawn OUTSIDE the graph.

        `eps` is a constant tensor with `requires_grad=False`, so the chain rule
        never has to differentiate the sampling. Everything random happens
        before the graph starts, and z is then a smooth function of mu and
        log_var. That is the entire trick.
        """
        raise NotImplementedError

    def decode(self, z: Tensor) -> Tensor:
        raise NotImplementedError

    def forward(self, x: Tensor, rng: Optional[random.Random] = None) -> Tensor:
        raise NotImplementedError

    def loss(self, x: Tensor, rng: random.Random, beta: float = 1.0
             ) -> Tuple[Tensor, float, float]:
        """Reconstruction + beta * KL, and both halves reported separately.

        Watching the two terms individually is the only way to diagnose a VAE.
        A KL that collapses to zero means the encoder gave up and is emitting
        N(0, I) for every input; a KL that grows without bound means it is
        smuggling information through by pushing the codes far apart, and your
        samples will be as bad as an autoencoder's.
        """
        raise NotImplementedError


def train_autoencoder(model: Autoencoder, xs: List[List[float]],
                      epochs: int = 20, batch_size: int = 32, lr: float = 0.01,
                      seed: int = 0) -> List[float]:
    raise NotImplementedError


def train_vae(model: VAE, xs: List[List[float]], epochs: int = 20,
              batch_size: int = 32, lr: float = 0.01, beta: float = 1.0,
              seed: int = 0) -> List[Tuple[float, float]]:
    raise NotImplementedError


def sample_prior(model, count: int, rng: random.Random) -> Tensor:
    """Draw z ~ N(0, I) and decode. This is the test of a generative model.

    An autoencoder will do this too — it has a decoder — and what comes out is
    the measurement that matters, because it shows whether the latent space has
    any structure away from the training points.
    """
    raise NotImplementedError


def sharpness(image: Sequence[float]) -> float:
    """Mean absolute difference between neighbouring pixels.

    A crude proxy for "does this look like a drawing rather than a smear", and
    it is enough to separate the two failure modes numerically instead of by
    squinting: real digits have edges, blurry averages do not, and noise has
    far too many.
    """
    raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. An autoencoder reconstructing digits through a 6-number bottleneck,
       original above and reconstruction below. It works.

    2. `sample_prior` on that same autoencoder. Noise. Then print the actual
       range of one latent dimension across the dataset and note how far it is
       from N(0, 1) — sampling from N(0, 1) is asking the decoder about a
       region it has never seen.

    3. The VAE, with reconstruction and KL reported separately per epoch, the
       latent dimension's mean and std (target 0 and 1), and samples from the
       prior. Be honest about the blur: it is not a bug in your code, it is
       what a squared-error reconstruction loss does when several digits are
       plausible for one code — it averages them. GANs and diffusion exist
       largely because of that.

    4. A beta sweep — 0, 0.3, 1, 30 — with reconstruction, KL, and the
       `sharpness` of sampled images against the real data's sharpness. Both
       ends fail and they fail in OPPOSITE directions: at beta=0 the samples
       are noise (sharpness above the real data), at beta=30 the KL collapses
       to zero and every sample is the same blurry average (sharpness far
       below).

    5. An interpolation between two images' latent codes, decoded at each step.
       Every intermediate point should look digit-like — that is what "the
       latent space is continuous" means, and it is what the KL term bought.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
