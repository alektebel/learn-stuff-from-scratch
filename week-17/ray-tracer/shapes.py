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

Learning Path:
1. Sphere.hit — the quadratic, and take the NEAREST root inside the window
2. The front_face flag, so refraction knows which side it is on
3. Plane.hit, and why its bounds() returns None
4. World.hit, passing the closest hit so far as the new t_max
5. AABB.hit — the slab method, needed by bvh.py
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
        raise NotImplementedError

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
        raise NotImplementedError

    def bounds(self) -> AABB:
        raise NotImplementedError


class Plane:
    """An infinite plane. One division, no roots to choose between."""

    def __init__(self, point: Vec3, normal: Vec3, material: object):
        self.point = point
        self.normal = normal.unit()
        self.material = material

    def __repr__(self) -> str:
        return f"Plane(through {self.point}, normal {self.normal})"

    def hit(self, ray: Ray, t_min: float, t_max: float) -> Optional[Hit]:
        raise NotImplementedError

    def bounds(self) -> Optional[AABB]:
        """An infinite plane has no finite bounding box.

        Returning None rather than a huge box is deliberate: a box spanning the
        universe would sit at the root of every BVH subtree and defeat the whole
        structure. Unbounded objects are tested separately, which is what real
        renderers do.
        """
        raise NotImplementedError


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
        raise NotImplementedError

    def bounds(self) -> Optional[AABB]:
        raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. A ray against a sphere aimed dead centre, at the edge, just past it,
       and behind the camera. The last one misses even though the LINE would
       hit: a ray is a half-line.
    2. A ray starting INSIDE a sphere, which needs the far root and reports
       front_face False.
    3. Shadow acne. Bounce off a real intersection point — one that carries
       genuine float error — at several scene scales, counting self-hits at
       several values of t_min. The bounce point is origin + t*direction, so
       its absolute error grows with the MAGNITUDE of the coordinates: at unit
       scale almost any epsilon works, at a million units 1e-9 is below the
       noise floor. That is why 0.001 is a guess about scene size and why some
       renderers use a relative epsilon.
    4. Ten spheres and one ray, showing every shape is still tested.
    5. AABB hits and misses, including a ray parallel to a slab.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
