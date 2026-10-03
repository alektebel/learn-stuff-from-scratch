"""
Materials — what happens when a ray arrives. Complete Solution.

A material answers one question: given an incoming ray and a surface hit, which
way does the ray leave, and by how much is it dimmed? That is `scatter`, and
three of them cover most of what a renderer needs.

DESIGN DECISION — trace from the eye, or from the light?
  Light physically travels from the source to the eye. Tracing that way is
  hopeless: almost every photon misses the camera entirely.
  CHOSEN: trace BACKWARDS, from the eye into the scene. This works because the
  physics is symmetric — the rendering equation does not care which end you
  start from — and it means every ray you spend contributes to a pixel. It is
  the single decision that makes ray tracing feasible, and it is why materials
  below are written as "where did this ray COME from" rather than "where does
  it go".

DESIGN DECISION — where does colour come from?
  Nothing here emits light except the sky. A ray that bounces until it escapes
  is coloured by the sky it escapes into; a ray that runs out of bounces is
  BLACK. So the image is built entirely from paths that found their way out,
  which is why an enclosed scene with no light source renders black and why
  increasing the bounce limit makes an image brighter rather than sharper.

DESIGN DECISION — how do you handle a rough metal, or a rough anything?
  CHOSEN: perturb the ideal direction by a random vector scaled by a roughness
  parameter. It is not a physically-based BRDF and it is the right first
  version: at roughness 0 you get a mirror, at 1 you get something close to
  diffuse, and the continuum between them is visible.
  A real renderer uses a microfacet model with a proper distribution and an
  importance-sampled BRDF, which is a much better answer to a question you
  cannot ask until you have built this one.

Learning Path:
1. Lambertian.scatter — normal + random_unit_vector, which IS cosine weighting
2. Metal.scatter, and absorb a reflection that points into the surface
3. Dielectric.scatter — refract, fall back to reflect, and apply Fresnel as a
   random CHOICE rather than a blend
4. sky(), which is the only light source in most of these scenes
"""

import math
import random
from typing import NamedTuple, Optional, Tuple

from vec import (ONE, Ray, Vec3, ZERO, random_in_hemisphere,
                 random_unit_vector, reflect, refract, schlick)


class Scatter(NamedTuple):
    ray: Ray
    attenuation: Vec3


class Lambertian:
    """Matte. Scatters in a cosine-weighted direction around the normal.

    The trick is `normal + random_unit_vector()`. That is not the same as a
    uniform direction in the hemisphere: adding a unit sphere centred on the
    normal biases the result towards the normal by exactly cos(theta), which is
    Lambert's cosine law — surfaces look dimmer at a grazing angle because the
    same light spreads over more area.

    Getting this "wrong" by sampling the hemisphere uniformly still renders,
    just slightly flatter, which is a good example of a bug that produces a
    plausible image.
    """

    def __init__(self, albedo: Vec3):
        self.albedo = albedo

    def __repr__(self) -> str:
        return f"Lambertian({self.albedo})"

    def scatter(self, ray: Ray, hit, rng: random.Random) -> Optional[Scatter]:
        raise NotImplementedError


class Metal:
    """Mirror, optionally roughened."""

    def __init__(self, albedo: Vec3, roughness: float = 0.0):
        self.albedo = albedo
        self.roughness = min(1.0, max(0.0, roughness))

    def __repr__(self) -> str:
        return f"Metal({self.albedo}, rough={self.roughness})"

    def scatter(self, ray: Ray, hit, rng: random.Random) -> Optional[Scatter]:
        raise NotImplementedError


class Dielectric:
    """Glass. Refracts, except when it cannot — and then it reflects.

    Two things make this look like glass rather than a bubble:

      TOTAL INTERNAL REFLECTION, when Snell's law has no solution past the
      critical angle. Handle it and the bottom of a sphere becomes a mirror.

      FRESNEL, via Schlick's approximation: reflectance rises steeply at
      grazing angles. Without it a sphere is equally transparent everywhere.

    Note how Fresnel is applied — as a RANDOM CHOICE weighted by the
    reflectance, not as a blend of two rays. One ray in, one ray out, and the
    average over many samples is the blend. Splitting the ray at every glass
    surface would double the work at every bounce and give you 2^depth rays.
    """

    def __init__(self, index: float = 1.5):
        self.index = index

    def __repr__(self) -> str:
        return f"Dielectric(n={self.index})"

    def scatter(self, ray: Ray, hit, rng: random.Random) -> Optional[Scatter]:
        raise NotImplementedError


class Emissive:
    """A light. Scatters nothing and returns colour instead.

    Included because it is the shortest path to understanding why the sky is
    the light source in the demo scenes: without an emitter, colour can only
    come from a ray that ESCAPES.
    """

    def __init__(self, colour: Vec3):
        self.colour = colour

    def __repr__(self) -> str:
        return f"Emissive({self.colour})"

    def scatter(self, ray: Ray, hit, rng: random.Random) -> Optional[Scatter]:
        raise NotImplementedError

    def emitted(self) -> Vec3:
        raise NotImplementedError


def sky(ray: Ray) -> Vec3:
    """A vertical gradient. The only light source in most of these scenes."""
    raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. The distribution of `normal + random_unit_vector()` against a uniform
       hemisphere, bucketed by cos(theta). The first is Lambert's cosine law;
       the second still renders, just flatter — a bug that produces a
       plausible picture.
    2. Metal roughness from 0 to 1: mean angle from the mirror direction, and
       the fraction ABSORBED because the perturbed ray points into the surface.
    3. Glass at several angles: what fraction reflects rather than refracts.
    4. Total internal reflection from inside the glass, bracketing the critical
       angle at about 41.8 degrees.
    5. The sky gradient, and the note that nothing else emits light — which is
       why an enclosed scene renders black.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
