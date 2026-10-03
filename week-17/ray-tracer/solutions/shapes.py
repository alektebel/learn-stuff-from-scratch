"""
Shapes — solving "what did I hit first". Complete Solution.

One question, asked billions of times. Everything here is a way of solving
P(t) = origin + t*direction against a surface and picking the right root.

DESIGN DECISION — return the nearest hit, or all of them?
  All of them is more general and it is what a CSG renderer needs.
  CHOSEN: nearest only, inside a [t_min, t_max] window. The window is not a
  detail — passing the closest hit so far as `t_max` lets every subsequent test
  reject early, and that single trick is most of what makes a scene with many
  objects tractable before you build a BVH.

DESIGN DECISION — t_min = 0, or t_min = 0.001?
  Mathematically the surface you just bounced off is at exactly t = 0, so any
  t > 0 is a new surface.
  In floating point it is not. A ray leaving a sphere at t = 0 re-intersects
  the SAME sphere at t = 1e-9, because the origin is a float and the sphere is
  a float and they do not quite agree. The pixel comes out black — the ray
  bounced off the inside of the surface it started on — and an image full of
  these is called SHADOW ACNE.
  CHOSEN: t_min = 0.001, and section 3 measures how much of the image it saves.
  Every ray tracer has this constant and it is always chosen by looking at the
  result.

DESIGN DECISION — which way does the normal point?
  Two conventions: always outward, or always against the ray. They matter for
  refraction, where you must know whether you are entering or leaving.
  CHOSEN: store the outward normal AND a `front_face` flag, flipping the stored
  normal to face the ray. That way shading code never has to think about it and
  refraction code has the one bit it needs. Choose "always outward" and every
  material has to work out which side it is on; choose "always against the ray"
  and glass cannot tell entering from leaving.
"""

import math
from typing import List, NamedTuple, Optional, Sequence, Tuple

from vec import Ray, Vec3


class Hit(NamedTuple):
    """Everything the shading code needs, and nothing it does not."""
    t: float
    point: Vec3
    normal: Vec3           # always faces the incoming ray
    front_face: bool       # False means we hit the inside
    material: object

    def __repr__(self) -> str:
        side = "outside" if self.front_face else "INSIDE"
        return f"<hit t={self.t:.4f} at {self.point} {side}>"


class AABB(NamedTuple):
    """An axis-aligned bounding box, for bvh.py."""
    low: Vec3
    high: Vec3

    def hit(self, ray: Ray, t_min: float, t_max: float) -> bool:
        """The slab method: intersect three pairs of parallel planes.

        For each axis the box is the region between two planes, so the ray is
        inside the box on that axis for an interval of t. The ray hits the box
        exactly when all three intervals overlap — which is a running max of
        the entry times against a running min of the exit times. No square
        roots, no divisions if you precompute the reciprocal, and it rejects
        the vast majority of rays in a few comparisons. That cheapness is the
        entire reason a BVH pays.
        """
        for axis in range(3):
            direction = ray.direction[axis]
            origin = ray.origin[axis]
            if abs(direction) < 1e-12:
                if not (self.low[axis] <= origin <= self.high[axis]):
                    return False
                continue
            inverse = 1.0 / direction
            t0 = (self.low[axis] - origin) * inverse
            t1 = (self.high[axis] - origin) * inverse
            if inverse < 0.0:
                t0, t1 = t1, t0
            t_min = max(t_min, t0)
            t_max = min(t_max, t1)
            if t_max <= t_min:
                return False
        return True

    def union(self, other: "AABB") -> "AABB":
        return AABB(Vec3(min(self.low.x, other.low.x),
                         min(self.low.y, other.low.y),
                         min(self.low.z, other.low.z)),
                    Vec3(max(self.high.x, other.high.x),
                         max(self.high.y, other.high.y),
                         max(self.high.z, other.high.z)))

    def centroid(self) -> Vec3:
        return (self.low + self.high) * 0.5

    def surface_area(self) -> float:
        span = self.high - self.low
        return 2 * (span.x * span.y + span.y * span.z + span.z * span.x)


class Sphere:
    """The canonical shape, because its intersection is a quadratic.

        |P(t) - centre|^2 = r^2

    expands to at^2 + bt + c = 0 with a = d.d, b = 2d.(o-c),
    c = (o-c).(o-c) - r^2. Two roots means the ray passes through, one means it
    grazes, none means it misses.
    """

    def __init__(self, centre: Vec3, radius: float, material: object):
        self.centre = centre
        self.radius = radius
        self.material = material

    def __repr__(self) -> str:
        return f"Sphere({self.centre}, r={self.radius})"

    def hit(self, ray: Ray, t_min: float, t_max: float) -> Optional[Hit]:
        oc = ray.origin - self.centre
        a = ray.direction.length_squared()
        half_b = oc.dot(ray.direction)
        c = oc.length_squared() - self.radius * self.radius
        discriminant = half_b * half_b - a * c
        if discriminant < 0:
            return None

        root_disc = math.sqrt(discriminant)
        # NEAREST root inside the window first, then the far one. Checking only
        # the near root means a ray starting inside a sphere never escapes it.
        for root in ((-half_b - root_disc) / a, (-half_b + root_disc) / a):
            if t_min < root < t_max:
                point = ray.at(root)
                outward = (point - self.centre) / self.radius
                front = ray.direction.dot(outward) < 0
                return Hit(root, point, outward if front else -outward,
                           front, self.material)
        return None

    def bounds(self) -> AABB:
        radius = Vec3(self.radius, self.radius, self.radius)
        return AABB(self.centre - radius, self.centre + radius)


class Plane:
    """An infinite plane. One division, no roots to choose between."""

    def __init__(self, point: Vec3, normal: Vec3, material: object):
        self.point = point
        self.normal = normal.unit()
        self.material = material

    def __repr__(self) -> str:
        return f"Plane(through {self.point}, normal {self.normal})"

    def hit(self, ray: Ray, t_min: float, t_max: float) -> Optional[Hit]:
        denominator = ray.direction.dot(self.normal)
        if abs(denominator) < 1e-9:
            return None                  # parallel: never hits, or always does
        t = (self.point - ray.origin).dot(self.normal) / denominator
        if not t_min < t < t_max:
            return None
        front = denominator < 0
        return Hit(t, ray.at(t), self.normal if front else -self.normal,
                   front, self.material)

    def bounds(self) -> Optional[AABB]:
        """An infinite plane has no finite bounding box.

        Returning None rather than a huge box is deliberate: a box spanning the
        universe would sit at the root of every BVH subtree and defeat the whole
        structure. Unbounded objects are tested separately, which is what real
        renderers do.
        """
        return None


class World:
    """A list of shapes, tested one by one. The baseline BVH is measured against."""

    def __init__(self, shapes: Optional[Sequence[object]] = None):
        self.shapes = list(shapes or [])
        self.stats = {"rays": 0, "intersection_tests": 0}

    def add(self, shape: object) -> None:
        self.shapes.append(shape)

    def __len__(self) -> int:
        return len(self.shapes)

    def hit(self, ray: Ray, t_min: float = 0.001,
            t_max: float = math.inf) -> Optional[Hit]:
        """Test everything, keeping the closest.

        The one optimisation even the brute-force version gets: `closest` is
        passed as the new `t_max`, so every later shape can reject early
        against a shorter window. Without it you compute every intersection and
        sort at the end, which is measurably slower for no benefit.
        """
        self.stats["rays"] += 1
        closest = t_max
        best: Optional[Hit] = None
        for shape in self.shapes:
            self.stats["intersection_tests"] += 1
            hit = shape.hit(ray, t_min, closest)
            if hit is not None:
                closest = hit.t
                best = hit
        return best

    def bounds(self) -> Optional[AABB]:
        boxes = [b for b in (s.bounds() for s in self.shapes) if b is not None]
        if not boxes:
            return None
        total = boxes[0]
        for box in boxes[1:]:
            total = total.union(box)
        return total


def _demo() -> None:
    import random

    print("=" * 76)
    print("SHAPES — one quadratic, and the constant everyone tunes by eye")
    print("=" * 76)

    class Fake:
        def __repr__(self) -> str:
            return "material"

    print("\n1. A ray against a sphere: two roots, one root, none")
    print("-" * 76)
    sphere = Sphere(Vec3(0, 0, -5), 1.0, Fake())
    print(f"    {'aimed at':>22}{'result':>34}")
    for label, direction in (("dead centre", Vec3(0, 0, -1)),
                             ("the edge", Vec3(0.999, 0, -5).unit()),
                             ("just past", Vec3(1.01, 0, -5).unit()),
                             ("behind the camera", Vec3(0, 0, 1))):
        hit = sphere.hit(Ray(Vec3(0, 0, 0), direction), 0.001, math.inf)
        print(f"    {label:>22}{str(hit) if hit else 'miss':>34}")
    print("  Aiming behind you misses even though the LINE would hit it: the")
    print("  root is negative and falls outside the [t_min, t_max] window. A")
    print("  ray is a half-line, and forgetting that renders objects behind the")
    print("  camera onto the screen.")

    print("\n2. Inside a sphere, you must take the FAR root")
    print("-" * 76)
    inside = Ray(Vec3(0, 0, -5), Vec3(0, 0, -1))
    hit = sphere.hit(inside, 0.001, math.inf)
    print(f"  a ray starting at the centre: {hit}")
    print(f"  front_face is {hit.front_face} — we hit the INSIDE, and the")
    print("  normal was flipped to face the ray so shading code never has to")
    print("  ask. Check only the near root and a ray inside a sphere never")
    print("  escapes: glass would be solid black.")

    print("\n3. Shadow acne, and why the epsilon must scale with the scene")
    print("-" * 76)
    rng = random.Random(0)
    print(f"    {'scene scale':>14}" + "".join(
        f"{f't_min={t:g}':>16}" for t in (0.0, 1e-9, 1e-3)))
    for scale in (1, 1_000, 1_000_000):
        big = Sphere(Vec3(0, 0, -5 * scale), 1.0 * scale, Fake())
        row = []
        for t_min in (0.0, 1e-9, 1e-3):
            self_hits = 0
            for _ in range(1500):
                aim = Vec3(rng.uniform(-1, 1), rng.uniform(-1, 1), -1).unit()
                first = big.hit(Ray(Vec3(0, 0, 0), aim), 1e-3 * scale, math.inf)
                if first is None:
                    continue
                outward = Vec3(rng.uniform(-1, 1), rng.uniform(-1, 1),
                               rng.uniform(-1, 1)).unit()
                if outward.dot(first.normal) < 0:
                    outward = -outward
                if big.hit(Ray(first.point, outward), t_min, math.inf):
                    self_hits += 1
            row.append(self_hits)
        print(f"    {f'x{scale:,}':>14}" + "".join(f"{n:>16}" for n in row))
    print("  A bounce point is computed as origin + t*direction, so its")
    print("  absolute float error grows with the MAGNITUDE of the coordinates.")
    print("  At unit scale almost any epsilon works; at a million units, 1e-9")
    print("  is far below the noise floor and the surface re-hits itself. Each")
    print("  one is a black pixel — the ray bounced off the inside of the thing")
    print("  it started on — and an image full of them is called shadow acne.")
    print("  0.001 is not derived from anything. It is a guess that suits a")
    print("  scene measured in units, which is why renderers that must handle")
    print("  both a teacup and a solar system use a RELATIVE epsilon instead.")

    print("\n4. The window closes as you find closer hits")
    print("-" * 76)
    world = World([Sphere(Vec3(0, 0, -z), 0.5, Fake()) for z in range(2, 12)])
    world.hit(Ray(Vec3(0, 0, 0), Vec3(0, 0, -1)))
    print(f"  10 spheres in a line, one ray: "
          f"{world.stats['intersection_tests']} intersection tests")
    print("  Every shape is still TESTED — that is what brute force means — but")
    print("  each test gets a shorter t window and rejects sooner. Passing the")
    print("  closest hit so far as the new t_max is free and it is the only")
    print("  optimisation available before you build an acceleration structure.")

    print("\n5. Bounding boxes reject in a few comparisons")
    print("-" * 76)
    box = AABB(Vec3(-1, -1, -1), Vec3(1, 1, 1))
    print(f"    {'ray':>26}{'hits box?':>12}")
    for label, origin, direction in (
            ("straight through", Vec3(0, 0, -5), Vec3(0, 0, 1)),
            ("clipping a corner", Vec3(-2, -2, -2), Vec3(1, 1, 1).unit()),
            ("parallel, outside", Vec3(0, 5, 0), Vec3(1, 0, 0)),
            ("parallel, inside", Vec3(0, 0, 0), Vec3(1, 0, 0)),
            ("pointing away", Vec3(0, 0, 5), Vec3(0, 0, 1))):
        print(f"    {label:>26}{str(box.hit(Ray(origin, direction), 0.001, math.inf)):>12}")
    print("  No square roots and no branches worth mentioning: three pairs of")
    print("  divisions and a running max against a running min. That cheapness")
    print("  is the entire reason a bounding volume hierarchy pays for itself.")

    print("\n" + "=" * 76)
    print("Next: bvh.py stops testing every object.")
    print("=" * 76)


if __name__ == "__main__":
    _demo()
