"""
Vectors and rays — the geometry everything else is written in.
Complete Solution.

A ray tracer is one question asked billions of times: "starting here, going
this way, what do I hit first?" This file is the vocabulary for asking it.

DESIGN DECISION — a class per vector, or flat tuples?
  A `Vec3` class reads beautifully: `p + t * direction`. It also allocates an
  object per operation, and a path tracer performs hundreds of millions of
  them.
  CHOSEN: a NamedTuple. It reads like a class, unpacks like a tuple, and is
  immutable — which matters more than it sounds, because a mutable vector
  shared between a hit record and the scene is the kind of aliasing bug that
  produces one wrong pixel and no error.
  REJECTED: flat floats threaded through every signature (fastest, unreadable)
  and mutable classes with in-place operations (fast, and a source of aliasing
  bugs).
  Be honest about the cost: this is 50-100x slower than the same algorithm in C
  and thousands of times slower on a GPU. The measurements in `render.py` are
  about RATIOS — BVH against brute force, variance against sample count — and
  those hold at any speed.

DESIGN DECISION — normalise everywhere, or track it?
  Half the operations in a ray tracer are only correct for unit vectors —
  reflection, refraction, cosine weighting, and every dot product used as a
  cosine.
  CHOSEN: normalise at the boundaries (ray directions and normals are always
  unit) and never inside the hot loop. `reflect` and `refract` document that
  they assume it. Renormalising defensively costs a square root per call in the
  innermost loop of the program; forgetting to normalise once gives you an
  image that is subtly too bright in one direction.

THE ONE EQUATION:

    P(t) = origin + t * direction

  Everything below is a way of solving that for t against some surface. A
  sphere gives a quadratic, a plane gives a division, a triangle gives a 3x3
  solve. The rest of a ray tracer is deciding which t you care about and what
  to do when you get there.
"""

import math
import random
from typing import Iterator, NamedTuple, Optional, Sequence, Tuple


class Vec3(NamedTuple):
    x: float
    y: float
    z: float

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self) -> "Vec3":
        return Vec3(-self.x, -self.y, -self.z)

    def __mul__(self, other) -> "Vec3":
        if isinstance(other, Vec3):
            return Vec3(self.x * other.x, self.y * other.y, self.z * other.z)
        return Vec3(self.x * other, self.y * other, self.z * other)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> "Vec3":
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)

    def dot(self, other: "Vec3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vec3") -> "Vec3":
        return Vec3(self.y * other.z - self.z * other.y,
                    self.z * other.x - self.x * other.z,
                    self.x * other.y - self.y * other.x)

    def length_squared(self) -> float:
        """Prefer this to `length` whenever you are only COMPARING.

        A square root in the innermost loop of a ray tracer is a real cost, and
        `a.length() < b.length()` and `a.length_squared() < b.length_squared()`
        answer the same question.
        """
        return self.x * self.x + self.y * self.y + self.z * self.z

    def length(self) -> float:
        return math.sqrt(self.length_squared())

    def unit(self) -> "Vec3":
        length = self.length()
        return self / length if length else self

    def near_zero(self, epsilon: float = 1e-8) -> bool:
        return abs(self.x) < epsilon and abs(self.y) < epsilon \
            and abs(self.z) < epsilon

    def __repr__(self) -> str:
        return f"({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"


ZERO = Vec3(0.0, 0.0, 0.0)
ONE = Vec3(1.0, 1.0, 1.0)


class Ray(NamedTuple):
    origin: Vec3
    direction: Vec3

    def at(self, t: float) -> Vec3:
        return self.origin + self.direction * t


def reflect(direction: Vec3, normal: Vec3) -> Vec3:
    """Mirror `direction` about `normal`. Assumes `normal` is a unit vector.

    d - 2(d.n)n. The dot product is the length of d's component along n; remove
    it once to land on the surface, twice to come back out the other side.
    """
    return direction - normal * (2.0 * direction.dot(normal))


def refract(direction: Vec3, normal: Vec3, ratio: float) -> Optional[Vec3]:
    """Snell's law. Returns None on TOTAL INTERNAL REFLECTION.

    `ratio` is the index of refraction you are leaving divided by the one you
    are entering. Beyond a critical angle there is no solution — the light
    cannot escape and reflects instead — and returning None rather than a NaN
    is what makes the caller handle it. That case is not an edge case: it is
    why the bottom of a glass sphere looks like a mirror, and skipping it
    produces black pixels that look like a shadow bug.
    """
    cos_theta = min(-direction.dot(normal), 1.0)
    sin_theta_squared = ratio * ratio * (1.0 - cos_theta * cos_theta)
    if sin_theta_squared > 1.0:
        return None
    perpendicular = (direction + normal * cos_theta) * ratio
    parallel = normal * -math.sqrt(max(0.0, 1.0 - perpendicular.length_squared()))
    return perpendicular + parallel


def schlick(cosine: float, index: float) -> float:
    """Fresnel reflectance, Schlick's approximation.

    Glass is more reflective at a grazing angle than head on — look along a
    window versus through it. Without this, a glass sphere is transparent
    everywhere and looks like a bubble rather than glass. One line, and it is
    most of the difference between "refraction implemented" and "glass".
    """
    r0 = ((1 - index) / (1 + index)) ** 2
    return r0 + (1 - r0) * ((1 - cosine) ** 5)


def random_unit_vector(rng: random.Random) -> Vec3:
    """A uniformly random direction on the sphere, by rejection sampling.

    Rejection rather than picking two random angles, because random spherical
    coordinates cluster at the poles: uniform in (theta, phi) is NOT uniform on
    the sphere. That bias shows up as a subtle directional tint in the render
    and is very hard to spot after the fact — see the measurement in the demo.
    """
    while True:
        candidate = Vec3(rng.uniform(-1, 1), rng.uniform(-1, 1),
                         rng.uniform(-1, 1))
        squared = candidate.length_squared()
        if 1e-12 < squared <= 1.0:
            return candidate / math.sqrt(squared)


def random_in_hemisphere(normal: Vec3, rng: random.Random) -> Vec3:
    direction = random_unit_vector(rng)
    return direction if direction.dot(normal) > 0 else -direction


def random_in_unit_disk(rng: random.Random) -> Vec3:
    """For depth of field: a random point on the lens."""
    while True:
        candidate = Vec3(rng.uniform(-1, 1), rng.uniform(-1, 1), 0.0)
        if candidate.length_squared() < 1.0:
            return candidate


def _demo() -> None:
    print("=" * 74)
    print("VEC — the geometry, and two details that produce wrong images")
    print("=" * 74)

    print("\n1. Reflection about a normal")
    print("-" * 74)
    normal = Vec3(0, 1, 0)
    for direction in (Vec3(1, -1, 0).unit(), Vec3(0, -1, 0), Vec3(3, -1, 0).unit()):
        out = reflect(direction, normal)
        print(f"  incoming {direction}  ->  reflected {out}   "
              f"(angle preserved: "
              f"{abs(direction.dot(normal) + out.dot(normal)) < 1e-9})")

    print("\n2. Refraction, and the case that is not an edge case")
    print("-" * 74)
    normal = Vec3(0, 1, 0)
    print(f"    {'incoming angle':>16}{'air -> glass':>16}{'glass -> air':>16}")
    for degrees in (10, 30, 45, 60, 80):
        radians = math.radians(degrees)
        direction = Vec3(math.sin(radians), -math.cos(radians), 0)
        into = refract(direction, normal, 1.0 / 1.5)
        out_of = refract(direction, normal, 1.5)
        print(f"    {degrees:>15}°{'bends' if into else 'TOTAL INTERNAL':>16}"
              f"{'bends' if out_of else 'TOTAL INTERNAL':>16}")
    print("  Past a critical angle there is no solution and the light reflects")
    print("  instead. Return a NaN there and you get black pixels that look")
    print("  like a shadow bug; return None and the caller has to decide. It is")
    print("  why the bottom of a glass sphere looks like a mirror.")

    print("\n3. Fresnel: glass is a mirror at a grazing angle")
    print("-" * 74)
    print(f"    {'angle from normal':>19}{'reflectance':>14}")
    for degrees in (0, 30, 60, 80, 89):
        cosine = math.cos(math.radians(degrees))
        print(f"    {degrees:>18}°{schlick(cosine, 1.5):>14.1%}")
    print("  Look through a window and you see the street; look ALONG it and")
    print("  you see yourself. Without this one line a glass sphere is equally")
    print("  transparent everywhere and reads as a soap bubble.")

    print("\n4. Uniform on a sphere is not uniform in angles")
    print("-" * 74)
    rng = random.Random(0)
    bands = 6
    correct = [0] * bands
    naive = [0] * bands
    samples = 60000
    for _ in range(samples):
        v = random_unit_vector(rng)
        correct[min(bands - 1, int((v.z + 1) / 2 * bands))] += 1
        # The tempting version: pick two angles uniformly.
        theta = rng.uniform(0, math.pi)
        z = math.cos(theta)
        naive[min(bands - 1, int((z + 1) / 2 * bands))] += 1
    print(f"    {'band of z':>12}{'rejection sampling':>21}{'uniform angles':>17}")
    for band in range(bands):
        low = -1 + 2 * band / bands
        print(f"    {low:>6.2f}..{low + 2 / bands:<5.2f}"
              f"{correct[band] / samples:>20.1%}{naive[band] / samples:>17.1%}")
    print("  Every band of equal HEIGHT on a sphere has equal AREA — that is")
    print("  Archimedes' theorem — so a correct sampler puts the same fraction")
    print("  in each. Picking theta uniformly clusters at the poles, and the")
    print("  result is a render with a subtle directional tint that is very")
    print("  hard to attribute after the fact.")

    print("\n5. length_squared, because a square root is not free")
    print("-" * 74)
    import time
    vectors = [Vec3(rng.random(), rng.random(), rng.random())
               for _ in range(200000)]
    start = time.perf_counter()
    total = sum(1 for v in vectors if v.length() < 0.5)
    with_sqrt = time.perf_counter() - start
    start = time.perf_counter()
    total2 = sum(1 for v in vectors if v.length_squared() < 0.25)
    without = time.perf_counter() - start
    print(f"  same answer ({total} == {total2}), "
          f"{with_sqrt:.3f}s with sqrt against {without:.3f}s without "
          f"({with_sqrt / without:.2f}x)")
    print("  A ray tracer asks 'which is closer' hundreds of millions of times")
    print("  and never needs the actual distance to answer it.")

    print("\n" + "=" * 74)
    print("Next: shapes.py answers 'what did I hit'.")
    print("=" * 74)


if __name__ == "__main__":
    _demo()
