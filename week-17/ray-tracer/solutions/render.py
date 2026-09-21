"""
Render — the camera, the path tracer, and the image. Complete Solution.

    for each pixel:
        for each sample:
            fire a ray, follow it until it escapes or runs out of bounces
        average

That is the whole renderer. The interesting part is what "average" costs.

DESIGN DECISION — why is the image noisy, and why is that so expensive to fix?
  Every pixel is a Monte Carlo estimate of an integral over all the light
  arriving at it. The error of a Monte Carlo estimate falls as 1/sqrt(N).
  So HALVING the noise costs FOUR TIMES the samples, and a tenth of the noise
  costs a hundred times. Section 3 measures exactly that curve.
  This one fact explains the entire economics of production rendering: why
  frames take hours, why denoisers exist, why importance sampling matters more
  than any micro-optimisation, and why "just add more samples" stops being an
  answer very quickly.

DESIGN DECISION — gamma correction, which looks like a fudge and is not.
  Displays are not linear: an sRGB value of 0.5 emits about 21% of maximum
  light, not 50%. Light transport is linear, so it must be computed in linear
  space and CONVERTED at the end. Skip it — as everyone does the first time —
  and the image is uniformly, mysteriously too dark. Section 5 shows the same
  render both ways.

DESIGN DECISION — where does the ray stop?
  CHOSEN: a fixed maximum depth, returning black. Simple, biased, and visible:
  raising the limit makes the image BRIGHTER, because more paths find their
  way out to the sky.
  REJECTED here, and the best extension in this file: RUSSIAN ROULETTE, which
  terminates paths randomly with a probability based on their remaining
  contribution and divides the survivors by that probability. It is unbiased —
  the expected value is exactly right — and it is how production renderers
  spend their samples where they matter.
"""

import math
import random
import time
from typing import List, Optional, Sequence, Tuple

from bvh import BVH
from material import Dielectric, Lambertian, Metal, sky
from shapes import Plane, Sphere, World
from vec import ONE, Ray, Vec3, ZERO, random_in_unit_disk


class Camera:
    """Position, orientation, field of view, and an optional aperture."""

    def __init__(self, look_from: Vec3, look_at: Vec3, up: Vec3,
                 vertical_fov: float, aspect: float,
                 aperture: float = 0.0, focus_distance: Optional[float] = None):
        theta = math.radians(vertical_fov)
        half_height = math.tan(theta / 2)
        half_width = aspect * half_height
        self.origin = look_from
        focus = focus_distance or (look_at - look_from).length()

        self.w = (look_from - look_at).unit()
        self.u = up.cross(self.w).unit()
        self.v = self.w.cross(self.u)

        self.lower_left = (self.origin
                           - self.u * (half_width * focus)
                           - self.v * (half_height * focus)
                           - self.w * focus)
        self.horizontal = self.u * (2 * half_width * focus)
        self.vertical = self.v * (2 * half_height * focus)
        self.lens_radius = aperture / 2

    def ray(self, s: float, t: float, rng: random.Random) -> Ray:
        """A ray through (s, t) in [0,1]^2.

        With a non-zero aperture the ray starts from a random point on the LENS
        rather than a single point, so objects away from the focus plane are
        hit by rays from different origins and blur. Depth of field is not a
        post-process here — it falls out of modelling the lens as having a
        size, which is what a real lens has.
        """
        origin = self.origin
        if self.lens_radius:
            offset = random_in_unit_disk(rng) * self.lens_radius
            shift = self.u * offset.x + self.v * offset.y
            origin = origin + shift
        target = self.lower_left + self.horizontal * s + self.vertical * t
        return Ray(origin, (target - origin).unit())


def ray_colour(ray: Ray, world, rng: random.Random, depth: int) -> Vec3:
    """Follow one path until it escapes or runs out of bounces.

    Iterative rather than recursive, carrying `throughput` — the product of
    every attenuation so far. Recursion is the textbook form and it hits
    Python's stack limit at a depth real renders use, and more importantly it
    hides the thing worth seeing: a path's contribution is a PRODUCT, so one
    dark surface anywhere along it kills the whole path.
    """
    throughput = ONE
    for _ in range(depth):
        hit = world.hit(ray, 0.001, math.inf)
        if hit is None:
            colour = sky(ray)
            return Vec3(throughput.x * colour.x, throughput.y * colour.y,
                        throughput.z * colour.z)
        emitted = getattr(hit.material, "emitted", None)
        if emitted is not None:
            light = emitted()
            return Vec3(throughput.x * light.x, throughput.y * light.y,
                        throughput.z * light.z)
        scattered = hit.material.scatter(ray, hit, rng)
        if scattered is None:
            return ZERO                  # absorbed
        throughput = Vec3(throughput.x * scattered.attenuation.x,
                          throughput.y * scattered.attenuation.y,
                          throughput.z * scattered.attenuation.z)
        ray = scattered.ray
    return ZERO                          # ran out of bounces: black


def render(world, camera: Camera, width: int, height: int,
           samples: int = 8, depth: int = 8, seed: int = 0
           ) -> List[List[Vec3]]:
    rng = random.Random(seed)
    image = []
    for y in range(height - 1, -1, -1):
        row = []
        for x in range(width):
            total = ZERO
            for _ in range(samples):
                # Jitter WITHIN the pixel. Sampling the exact centre every time
                # gives you the same ray `samples` times and no anti-aliasing
                # at all — a mistake that shows up as hard staircase edges in
                # an image that otherwise looks fine.
                s = (x + rng.random()) / (width - 1)
                t = (y + rng.random()) / (height - 1)
                total = total + ray_colour(camera.ray(s, t, rng), world,
                                           rng, depth)
            row.append(total / samples)
        image.append(row)
    return image


def gamma(colour: Vec3, power: float = 2.2) -> Vec3:
    """Linear light to display values.

    A display is not linear: sRGB 0.5 emits about 21% of maximum. Light
    transport IS linear, so it is computed in linear space and converted here.
    Skip it and the whole image is too dark in a way that is very hard to
    attribute — it looks like the lighting is wrong.
    """
    inverse = 1.0 / power
    return Vec3(max(0.0, colour.x) ** inverse,
                max(0.0, colour.y) ** inverse,
                max(0.0, colour.z) ** inverse)


def to_ascii(image: List[List[Vec3]], apply_gamma: bool = True) -> str:
    """Render to characters, so the result is visible in a terminal."""
    shades = " .:-=+*#%@"
    lines = []
    for row in image:
        line = ""
        for colour in row:
            if apply_gamma:
                colour = gamma(colour)
            brightness = (colour.x * 0.299 + colour.y * 0.587
                          + colour.z * 0.114)
            index = min(len(shades) - 1, int(brightness * len(shades)))
            line += shades[index] * 2
        lines.append(line)
    return "\n".join(lines)


def to_ppm(image: List[List[Vec3]], path: str) -> str:
    """Write a real image file. P3 is ASCII PPM — every viewer reads it."""
    height, width = len(image), len(image[0])
    with open(path, "w") as handle:
        handle.write(f"P3\n{width} {height}\n255\n")
        for row in image:
            for colour in row:
                corrected = gamma(colour)
                handle.write(
                    f"{int(255.99 * min(1.0, corrected.x))} "
                    f"{int(255.99 * min(1.0, corrected.y))} "
                    f"{int(255.99 * min(1.0, corrected.z))}\n")
    return path


def variance(image: List[List[Vec3]], other: List[List[Vec3]]) -> float:
    """Root-mean-square difference between two renders of the same scene.

    Against a high-sample reference this is the NOISE, and the number the
    1/sqrt(N) law predicts.
    """
    total, count = 0.0, 0
    for row_a, row_b in zip(image, other):
        for a, b in zip(row_a, row_b):
            difference = a - b
            total += difference.length_squared()
            count += 1
    return math.sqrt(total / max(1, count))


def demo_scene() -> Tuple[BVH, Camera, int, int]:
    ground = Lambertian(Vec3(0.55, 0.55, 0.5))
    shapes = [
        Plane(Vec3(0, -0.5, 0), Vec3(0, 1, 0), ground),
        Sphere(Vec3(0, 0, -1.2), 0.5, Lambertian(Vec3(0.7, 0.3, 0.3))),
        Sphere(Vec3(-1.05, 0, -1.2), 0.5, Metal(Vec3(0.8, 0.8, 0.85), 0.05)),
        Sphere(Vec3(1.05, 0, -1.2), 0.5, Dielectric(1.5)),
        Sphere(Vec3(0.3, -0.32, -0.55), 0.18, Metal(Vec3(0.8, 0.6, 0.2), 0.35)),
    ]
    camera = Camera(Vec3(0, 0.35, 1.1), Vec3(0, 0, -1.2), Vec3(0, 1, 0),
                    50, 2.0)
    return BVH(shapes), camera, 44, 22


def _demo() -> None:
    print("=" * 78)
    print("RENDER — a picture, and why the noise is so expensive")
    print("=" * 78)

    world, camera, width, height = demo_scene()
    print(f"\n  {len(world.unbounded)} unbounded + "
          f"{world.stats['nodes']} BVH nodes, {width}x{height} ASCII")
    print("  (this file renders the same scene several times; give it a minute)")

    print("\n1. The image")
    print("-" * 78)
    start = time.perf_counter()
    image = render(world, camera, width, height, samples=24, depth=8, seed=1)
    elapsed = time.perf_counter() - start
    print(to_ascii(image))
    rays = width * height * 24
    print(f"  {rays:,} camera rays, up to 8 bounces each, in {elapsed:.1f}s "
          f"({rays / elapsed:,.0f} rays/s)")
    print("  Matte sphere in the middle, metal on the left, glass on the right.")
    print("  The glass one is bright because it lets the sky through and dark")
    print("  at its edge where Fresnel turns it into a mirror.")
    path = to_ppm(image, "render.ppm")
    print(f"  also written to {path} — open it in any image viewer")

    print("\n2. Anti-aliasing is jitter, nothing more")
    print("-" * 78)
    for label, samples in (("1 sample per pixel", 1), ("16 samples", 16)):
        small = render(world, camera, 30, 12, samples=samples, depth=4, seed=2)
        print(f"  {label}:")
        print(to_ascii(small))
    print("  Same code, same scene. The only difference is that each sample")
    print("  lands at a random point WITHIN the pixel instead of at its centre,")
    print("  so an edge crossing the pixel gets averaged rather than decided.")

    print("\n3. Noise falls as 1/sqrt(N), and that is the whole economics")
    print("-" * 78)
    reference = render(world, camera, 24, 12, samples=192, depth=6, seed=7)
    print(f"    {'samples':>9}{'noise (RMS)':>14}{'predicted':>12}"
          f"{'seconds':>10}")
    baseline = None
    for samples in (1, 4, 16, 64):
        start = time.perf_counter()
        test = render(world, camera, 24, 12, samples=samples, depth=6, seed=11)
        elapsed = time.perf_counter() - start
        noise = variance(test, reference)
        baseline = baseline or noise
        print(f"    {samples:>9}{noise:>14.4f}"
              f"{baseline / math.sqrt(samples):>12.4f}{elapsed:>10.2f}")
    print("  The measured noise tracks 1/sqrt(N) closely. Read that as a bill:")
    print("  HALVING the noise costs FOUR times the samples. A tenth of the")
    print("  noise costs a hundred times. That single fact is why production")
    print("  frames take hours, why denoisers exist, and why importance")
    print("  sampling is worth more than any amount of micro-optimisation —")
    print("  it changes the constant in front of the sqrt, and nothing else can.")

    print("\n4. Bounce depth changes BRIGHTNESS, not sharpness")
    print("-" * 78)
    print(f"    {'max depth':>11}{'mean brightness':>18}{'seconds':>10}")
    for depth in (1, 2, 4, 8, 16):
        start = time.perf_counter()
        test = render(world, camera, 24, 12, samples=16, depth=depth, seed=5)
        elapsed = time.perf_counter() - start
        mean = sum((c.x + c.y + c.z) / 3 for row in test for c in row) \
            / (24 * 12)
        print(f"    {depth:>11}{mean:>18.4f}{elapsed:>10.2f}")
    print("  A ray that runs out of bounces returns BLACK, so a low limit")
    print("  darkens the image rather than blurring it. The returns diminish")
    print("  fast — each bounce multiplies by an albedo below 1, so a path's")
    print("  contribution decays geometrically. That is exactly the observation")
    print("  Russian roulette exploits: terminate low-contribution paths early")
    print("  and divide the survivors by the survival probability, which is")
    print("  cheaper AND unbiased.")

    print("\n5. Gamma is not a fudge")
    print("-" * 78)
    small = render(world, camera, 30, 12, samples=16, depth=6, seed=3)
    print("  with gamma correction:")
    print(to_ascii(small, apply_gamma=True))
    print("  without:")
    print(to_ascii(small, apply_gamma=False))
    linear = sum((c.x + c.y + c.z) / 3 for row in small for c in row) / (30 * 12)
    corrected = sum((gamma(c).x + gamma(c).y + gamma(c).z) / 3
                    for row in small for c in row) / (30 * 12)
    print(f"  mean value {linear:.3f} linear, {corrected:.3f} after correction")
    print("  A display is not linear — sRGB 0.5 emits about 21% of maximum —")
    print("  and light transport IS linear, so it is computed in linear space")
    print("  and converted at the very end. Skip it and the image is uniformly")
    print("  too dark in a way that looks like a lighting bug.")

    print("\n6. Depth of field falls out of giving the lens a size")
    print("-" * 78)
    for aperture in (0.0, 0.25):
        blurred = Camera(Vec3(0, 0.35, 1.1), Vec3(0, 0, -1.2), Vec3(0, 1, 0),
                         50, 2.0, aperture=aperture, focus_distance=2.3)
        print(f"  aperture {aperture}:")
        print(to_ascii(render(world, blurred, 30, 12, samples=16, depth=4,
                              seed=4)))
    print("  Not a post-process and not a blur filter. Each ray starts at a")
    print("  random point on a lens of non-zero radius, so objects away from")
    print("  the focus plane are struck by rays from different origins and")
    print("  average out. A pinhole camera has an aperture of zero and infinite")
    print("  depth of field, which is why the default renders everything sharp.")

    print("\n" + "=" * 78)
    print("You wrote the geometry, the acceleration structure, the materials")
    print("and the integrator. The image above is the whole rendering equation,")
    print("solved by averaging a very large number of random guesses.")
    print("=" * 78)


if __name__ == "__main__":
    _demo()
