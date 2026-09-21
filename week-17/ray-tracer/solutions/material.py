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
        direction = hit.normal + random_unit_vector(rng)
        if direction.near_zero():
            # The random vector landed exactly opposite the normal. Rare, and
            # it produces a zero-length direction that becomes NaN two lines
            # later — a single black pixel with no explanation.
            direction = hit.normal
        return Scatter(Ray(hit.point, direction.unit()), self.albedo)


class Metal:
    """Mirror, optionally roughened."""

    def __init__(self, albedo: Vec3, roughness: float = 0.0):
        self.albedo = albedo
        self.roughness = min(1.0, max(0.0, roughness))

    def __repr__(self) -> str:
        return f"Metal({self.albedo}, rough={self.roughness})"

    def scatter(self, ray: Ray, hit, rng: random.Random) -> Optional[Scatter]:
        reflected = reflect(ray.direction.unit(), hit.normal)
        if self.roughness:
            reflected = reflected + random_unit_vector(rng) * self.roughness
        # A rough enough reflection can point INTO the surface. Absorb it —
        # returning it would send the ray through the object it just hit.
        if reflected.dot(hit.normal) <= 0:
            return None
        return Scatter(Ray(hit.point, reflected.unit()), self.albedo)


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
        ratio = (1.0 / self.index) if hit.front_face else self.index
        direction = ray.direction.unit()
        cos_theta = min(-direction.dot(hit.normal), 1.0)

        refracted = refract(direction, hit.normal, ratio)
        if refracted is None or schlick(cos_theta, ratio) > rng.random():
            outgoing = reflect(direction, hit.normal)
        else:
            outgoing = refracted
        # Glass absorbs nothing: attenuation is white. All the visual interest
        # comes from WHERE the ray goes, not from how much it is dimmed.
        return Scatter(Ray(hit.point, outgoing), ONE)


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
        return None

    def emitted(self) -> Vec3:
        return self.colour


def sky(ray: Ray) -> Vec3:
    """A vertical gradient. The only light source in most of these scenes."""
    t = 0.5 * (ray.direction.unit().y + 1.0)
    return Vec3(1.0, 1.0, 1.0) * (1.0 - t) + Vec3(0.5, 0.7, 1.0) * t


def _demo() -> None:
    print("=" * 76)
    print("MATERIALS — one question, three answers")
    print("=" * 76)

    class FakeHit(NamedTuple):
        t: float
        point: Vec3
        normal: Vec3
        front_face: bool
        material: object

    rng = random.Random(0)
    up = Vec3(0, 1, 0)
    incoming = Ray(Vec3(0, 1, 0), Vec3(1, -1, 0).unit())
    hit = FakeHit(1.0, ZERO, up, True, None)

    print("\n1. Cosine weighting is what makes matte look matte")
    print("-" * 76)
    bands = 5
    cosine_weighted = [0] * bands
    uniform = [0] * bands
    samples = 40000
    for _ in range(samples):
        direction = (up + random_unit_vector(rng)).unit()
        cosine_weighted[min(bands - 1, int(direction.dot(up) * bands))] += 1
        other = random_in_hemisphere(up, rng)
        uniform[min(bands - 1, int(other.dot(up) * bands))] += 1
    print(f"    {'cos(theta) band':>18}{'normal + random':>18}"
          f"{'uniform hemisphere':>21}")
    for band in range(bands):
        low = band / bands
        print(f"    {low:>7.1f}..{low + 1 / bands:<8.1f}"
              f"{cosine_weighted[band] / samples:>18.1%}"
              f"{uniform[band] / samples:>21.1%}")
    print("  `normal + random_unit_vector()` biases towards the normal by")
    print("  exactly cos(theta) — Lambert's cosine law, which is why a surface")
    print("  looks dimmer at a grazing angle. Sample the hemisphere uniformly")
    print("  instead and the image still renders, just flatter: a bug that")
    print("  produces a plausible picture, which is the hardest kind to find.")

    print("\n2. Roughness, from mirror to almost-matte")
    print("-" * 76)
    print(f"    {'roughness':>11}{'mean angle from the mirror direction':>40}"
          f"{'absorbed':>11}")
    for roughness in (0.0, 0.1, 0.3, 0.6, 1.0):
        metal = Metal(Vec3(0.8, 0.8, 0.8), roughness)
        mirror = reflect(incoming.direction, up).unit()
        total, absorbed = 0.0, 0
        for _ in range(4000):
            result = metal.scatter(incoming, hit, rng)
            if result is None:
                absorbed += 1
                continue
            total += math.degrees(math.acos(
                max(-1.0, min(1.0, result.ray.direction.dot(mirror)))))
        scattered = 4000 - absorbed
        print(f"    {roughness:>11.1f}{total / max(1, scattered):>39.1f}°"
              f"{absorbed / 4000:>11.1%}")
    print("  At roughness 1 a fifth of rays are ABSORBED, because the")
    print("  perturbed direction points into the surface. Returning it anyway")
    print("  sends the ray through the object it just hit, and the result is")
    print("  light leaking out of solid geometry.")

    print("\n3. Glass: what fraction reflects rather than refracts")
    print("-" * 76)
    glass = Dielectric(1.5)
    print(f"    {'angle from normal':>19}{'reflected':>12}{'refracted':>12}"
          f"{'why':>28}")
    for degrees in (0, 30, 60, 80, 89):
        radians = math.radians(degrees)
        direction = Vec3(math.sin(radians), -math.cos(radians), 0).unit()
        ray = Ray(Vec3(0, 1, 0), direction)
        reflected = 0
        for _ in range(4000):
            result = glass.scatter(ray, hit, rng)
            if result.ray.direction.dot(up) > 0:
                reflected += 1
        fraction = reflected / 4000
        why = "Fresnel" if fraction < 0.99 else "Fresnel dominates"
        print(f"    {degrees:>18}°{fraction:>12.1%}{1 - fraction:>12.1%}"
              f"{why:>28}")
    print("  Applied as a random CHOICE weighted by the reflectance, not as a")
    print("  blend of two rays. One ray in, one ray out — split at every glass")
    print("  surface and you have 2^depth rays by the fifth bounce. The blend")
    print("  emerges from averaging many samples, which is what a path tracer")
    print("  does for free.")

    print("\n4. Total internal reflection from inside the glass")
    print("-" * 76)
    inside = FakeHit(1.0, ZERO, Vec3(0, -1, 0), False, None)
    print(f"    {'angle from normal':>19}{'escapes':>10}{'trapped':>10}")
    for degrees in (10, 30, 41, 42, 60):
        radians = math.radians(degrees)
        direction = Vec3(math.sin(radians), math.cos(radians), 0).unit()
        ray = Ray(Vec3(0, -1, 0), direction)
        trapped = 0
        for _ in range(2000):
            result = glass.scatter(ray, inside, rng)
            if result.ray.direction.dot(Vec3(0, -1, 0)) > 0:
                trapped += 1
        print(f"    {degrees:>18}°{1 - trapped / 2000:>10.1%}"
              f"{trapped / 2000:>10.1%}")
    print("  The critical angle for glass is about 41.8°. Beyond it Snell's")
    print("  law has no solution and every ray reflects — which is why the")
    print("  bottom of a glass sphere looks like a mirror, and why fibre optics")
    print("  work at all.")

    print("\n5. Where colour comes from")
    print("-" * 76)
    for label, direction in (("straight up", Vec3(0, 1, 0)),
                             ("horizon", Vec3(1, 0, 0)),
                             ("downwards", Vec3(0, -1, 0))):
        colour = sky(Ray(ZERO, direction))
        print(f"    {label:<14}{colour}")
    print("  Nothing in these scenes emits light except the sky. A ray that")
    print("  bounces until it ESCAPES is coloured by what it escapes into; a")
    print("  ray that runs out of bounces is black. That is why an enclosed")
    print("  scene with no emitter renders black, and why raising the bounce")
    print("  limit makes an image BRIGHTER rather than sharper.")

    print("\n" + "=" * 76)
    print("Next: render.py puts a camera in front of all this.")
    print("=" * 76)


if __name__ == "__main__":
    _demo()
