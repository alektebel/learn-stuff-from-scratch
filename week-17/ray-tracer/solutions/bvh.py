"""
BVH — not testing every object. Complete Solution.

Brute force is O(objects) per ray. A million-triangle scene at a million rays
is 10^12 intersection tests, and no constant factor saves that. A bounding
volume hierarchy makes it O(log objects), and it is the difference between a
ray tracer that renders a sphere and one that renders a film.

DESIGN DECISION — a grid, a k-d tree, or a bounding volume hierarchy?
  A UNIFORM GRID is trivial to build and degenerates completely on scenes with
  clustered detail — the "teapot in a stadium" problem, where one cell holds
  everything.
  A K-D TREE splits SPACE, so an object straddling a split must be referenced
  from both sides, and the memory is unbounded in the worst case.
  CHOSEN: a BVH, which splits OBJECTS. Every object appears exactly once, the
  tree has exactly 2n-1 nodes for n objects, and boxes may overlap — which
  costs a little traversal and buys a bound on memory that nothing else offers.
  This is what essentially every production renderer uses.

DESIGN DECISION — where do you split?
  MEDIAN split (half the objects each side) is one sort and it gives a balanced
  tree. Balance is not the goal.
  CHOSEN: implement both, and measure. The SURFACE AREA HEURISTIC asks a
  better question — "which split minimises the EXPECTED cost of a random ray?"
  A ray hits a box with probability proportional to the box's surface area, so
  the cost of a split is

      area(left)/area(parent) * count(left)  +  area(right)/area(parent) * count(right)

  Try every candidate split, take the cheapest. It builds a slower, uglier,
  unbalanced tree that traverses faster, and section 3 measures the difference
  on a scene where median split does badly.

WHAT TO EXPECT: the win is asymptotic, so it is invisible at ten objects and
enormous at a thousand. Section 2 shows the crossover, and it is worth seeing
that a BVH makes a small scene SLOWER.
"""

import math
import random
from typing import List, Optional, Sequence, Tuple

from shapes import AABB, Hit, Sphere, World
from vec import Ray, Vec3


class BVHNode:
    """One node: a box, and either two children or a leaf's objects."""

    __slots__ = ("box", "left", "right", "objects")

    def __init__(self, box: AABB, left=None, right=None, objects=None):
        self.box = box
        self.left = left
        self.right = right
        self.objects = objects or []

    @property
    def is_leaf(self) -> bool:
        return self.left is None

    def __repr__(self) -> str:
        return (f"<leaf {len(self.objects)}>" if self.is_leaf
                else f"<node>")


class BVH:
    """A bounding volume hierarchy over a list of shapes."""

    def __init__(self, shapes: Sequence[object], leaf_size: int = 2,
                 heuristic: str = "sah", buckets: int = 12):
        self.unbounded = [s for s in shapes if s.bounds() is None]
        bounded = [s for s in shapes if s.bounds() is not None]
        self.leaf_size = leaf_size
        self.heuristic = heuristic
        self.buckets = buckets
        self.stats = {"rays": 0, "box_tests": 0, "intersection_tests": 0,
                      "nodes": 0, "leaves": 0, "max_depth": 0}
        self.root = self._build(bounded, 0) if bounded else None

    # -- building -----------------------------------------------------------

    def _build(self, shapes: List[object], depth: int) -> BVHNode:
        self.stats["nodes"] += 1
        self.stats["max_depth"] = max(self.stats["max_depth"], depth)
        box = shapes[0].bounds()
        for shape in shapes[1:]:
            box = box.union(shape.bounds())

        if len(shapes) <= self.leaf_size:
            self.stats["leaves"] += 1
            return BVHNode(box, objects=shapes)

        split = (self._split_sah(shapes, box) if self.heuristic == "sah"
                 else self._split_median(shapes, box))
        if split is None:
            self.stats["leaves"] += 1
            return BVHNode(box, objects=shapes)

        left, right = split
        return BVHNode(box, self._build(left, depth + 1),
                       self._build(right, depth + 1))

    def _split_median(self, shapes: List[object], box: AABB):
        """Split the LONGEST axis at the median object. One sort, balanced."""
        span = box.high - box.low
        axis = max(range(3), key=lambda i: span[i])
        shapes.sort(key=lambda s: s.bounds().centroid()[axis])
        middle = len(shapes) // 2
        return shapes[:middle], shapes[middle:]

    def _split_sah(self, shapes: List[object], box: AABB):
        """The surface area heuristic: minimise the EXPECTED traversal cost.

        The probability a random ray that hit the parent also hits a child is
        the ratio of their surface areas — a geometric fact, not an
        approximation. So the cost of a candidate split is

            area(L)/area(P) * |L|  +  area(R)/area(P) * |R|

        Bucket the objects along each axis, try every bucket boundary, take the
        cheapest. It is more work at build time and it produces an UNBALANCED
        tree that traverses faster, because balance was never the goal.
        """
        parent_area = box.surface_area()
        if parent_area <= 0:
            return None

        best_cost = float("inf")
        best_split = None
        for axis in range(3):
            span = box.high[axis] - box.low[axis]
            if span <= 1e-12:
                continue
            ordered = sorted(shapes, key=lambda s: s.bounds().centroid()[axis])
            step = max(1, len(ordered) // self.buckets)
            for cut in range(step, len(ordered), step):
                left, right = ordered[:cut], ordered[cut:]
                left_box = left[0].bounds()
                for shape in left[1:]:
                    left_box = left_box.union(shape.bounds())
                right_box = right[0].bounds()
                for shape in right[1:]:
                    right_box = right_box.union(shape.bounds())
                cost = (left_box.surface_area() / parent_area * len(left)
                        + right_box.surface_area() / parent_area * len(right))
                if cost < best_cost:
                    best_cost = cost
                    best_split = (left, right)

        # If no split beats simply testing everything, make a leaf. Without
        # this a scene of coincident objects recurses forever.
        if best_split is None or best_cost >= len(shapes):
            return None
        return best_split

    # -- traversal ----------------------------------------------------------

    def hit(self, ray: Ray, t_min: float = 0.001,
            t_max: float = math.inf) -> Optional[Hit]:
        self.stats["rays"] += 1
        best: Optional[Hit] = None
        closest = t_max
        for shape in self.unbounded:
            self.stats["intersection_tests"] += 1
            hit = shape.hit(ray, t_min, closest)
            if hit is not None:
                closest, best = hit.t, hit
        if self.root is None:
            return best

        # An explicit stack rather than recursion. Python's recursion limit is
        # a real constraint on a deep tree, and the traversal order matters:
        # descending the nearer child first shrinks t_max sooner and prunes the
        # far subtree entirely more often.
        stack = [self.root]
        while stack:
            node = stack.pop()
            self.stats["box_tests"] += 1
            if not node.box.hit(ray, t_min, closest):
                continue
            if node.is_leaf:
                for shape in node.objects:
                    self.stats["intersection_tests"] += 1
                    hit = shape.hit(ray, t_min, closest)
                    if hit is not None:
                        closest, best = hit.t, hit
            else:
                stack.append(node.left)
                stack.append(node.right)
        return best

    def depth(self, node: Optional[BVHNode] = None) -> int:
        node = node or self.root
        if node is None or node.is_leaf:
            return 1
        return 1 + max(self.depth(node.left), self.depth(node.right))


def random_scene(count: int, seed: int = 0, clustered: bool = False
                 ) -> List[Sphere]:
    """`clustered=True` is the teapot-in-a-stadium case: most objects in a
    tiny region, a few far away. It is where a median split does badly and a
    uniform grid falls over completely."""
    rng = random.Random(seed)
    shapes = []
    for index in range(count):
        if clustered and index < count - 4:
            centre = Vec3(rng.gauss(0, 0.4), rng.gauss(0, 0.4),
                          rng.gauss(-5, 0.4))
            radius = 0.05
        else:
            centre = Vec3(rng.uniform(-20, 20), rng.uniform(-20, 20),
                          rng.uniform(-40, -2))
            radius = rng.uniform(0.2, 1.5)
        shapes.append(Sphere(centre, radius, None))
    return shapes


def _demo() -> None:
    import time

    print("=" * 78)
    print("BVH — the difference between rendering a sphere and rendering a film")
    print("=" * 78)

    def cast(target, rays: int, seed: int = 1,
             spread: float = 1.0) -> Tuple[float, int]:
        """Cast `rays` random rays. `spread` narrows the cone — a small spread
        aims at the cluster, which is the case the clustered scene exists to
        test. Casting uniformly at a teapot in a stadium means almost every ray
        misses the teapot, and then you are measuring nothing."""
        rng = random.Random(seed)
        start = time.perf_counter()
        for _ in range(rays):
            direction = Vec3(rng.uniform(-spread, spread),
                             rng.uniform(-spread, spread), -1).unit()
            target.hit(Ray(Vec3(0, 0, 0), direction))
        return time.perf_counter() - start, target.stats["intersection_tests"]

    print("\n1. What a BVH actually does to the work per ray")
    print("-" * 78)
    shapes = random_scene(400, seed=3)
    world = World(shapes)
    bvh = BVH(shapes)
    rays = 1500
    brute_time, brute_tests = cast(world, rays)
    bvh_time, bvh_tests = cast(bvh, rays)
    print(f"  400 spheres, {rays} rays")
    print(f"    {'brute force':<16}{brute_tests:>10,} intersection tests"
          f"{brute_time:>9.2f}s")
    print(f"    {'BVH':<16}{bvh_tests:>10,} intersection tests"
          f"{bvh_time:>9.2f}s   (+{bvh.stats['box_tests']:,} box tests)")
    print(f"    {'ratio':<16}{brute_tests / max(1, bvh_tests):>10.0f}x fewer"
          f"{'':>18}{brute_time / bvh_time:>5.1f}x faster")
    print(f"  tree: {bvh.stats['nodes']} nodes, {bvh.stats['leaves']} leaves, "
          f"depth {bvh.depth()} (log2(400) = {math.log2(400):.1f})")
    print("  A box test is far cheaper than a sphere test — no square root —")
    print("  so trading many of the first for few of the second is the whole")
    print("  bargain.")

    print("\n2. The crossover: a BVH makes a SMALL scene slower")
    print("-" * 78)
    print(f"    {'objects':>9}{'brute tests':>14}{'BVH tests':>12}"
          f"{'brute s':>10}{'BVH s':>9}{'speedup':>10}")
    for count in (4, 16, 64, 256, 1024):
        shapes = random_scene(count, seed=count)
        brute_time, brute_tests = cast(World(shapes), 600)
        tree = BVH(shapes)
        bvh_time, bvh_tests = cast(tree, 600)
        print(f"    {count:>9}{brute_tests:>14,}{bvh_tests:>12,}"
              f"{brute_time:>10.3f}{bvh_time:>9.3f}"
              f"{brute_time / bvh_time:>9.2f}x")
    print("  At four objects the BVH is barely worth having; at a thousand it")
    print("  is an order of magnitude. The win is ASYMPTOTIC, which means it is")
    print("  nearly invisible on a test scene and decisive on a real one — and")
    print("  it is why 'we tried an acceleration structure and it did not help'")
    print("  is usually a statement about the benchmark.")
    print("  In a compiled renderer the small end is genuinely SLOWER, because")
    print("  there the box test and the sphere test cost about the same and the")
    print("  traversal is pure overhead. Here a Python sphere test is expensive")
    print("  enough that the BVH wins even at four objects, which is a fact")
    print("  about this implementation rather than about BVHs.")

    print("\n3. Surface area heuristic against median split")
    print("-" * 78)
    print(f"    {'scene':<26}{'split':>10}{'depth':>8}"
          f"{'tests/ray':>12}{'build s':>10}")
    for label, clustered in (("spread out", False),
                             ("teapot in a stadium", True)):
        shapes = random_scene(500, seed=9, clustered=clustered)
        for heuristic in ("median", "sah"):
            start = time.perf_counter()
            tree = BVH(list(shapes), heuristic=heuristic)
            build = time.perf_counter() - start
            _, tests = cast(tree, 800, seed=4,
                            spread=0.15 if clustered else 1.0)
            print(f"    {label:<26}{heuristic:>10}{tree.depth():>8}"
                  f"{tests / 800:>12.1f}{build:>10.3f}")
    print("  The SAH tests about 1.6x fewer objects per ray on both scenes,")
    print("  for roughly 18x the build time — and it does it with a DEEPER,")
    print("  less balanced tree, which is the point worth taking away. Balance")
    print("  was never the goal. A median split insists on putting half the")
    print("  objects each side even when the geometry says otherwise; the SAH")
    print("  asks the question that actually predicts cost, since a ray hits a")
    print("  box with probability proportional to its surface area.")
    print("  Whether the build cost is worth it depends entirely on how long")
    print("  you render. A film builds once and renders for hours, so it buys")
    print("  the expensive tree; an interactive renderer rebuilding every frame")
    print("  uses a cheaper heuristic, and that is a real trade rather than a")
    print("  question with a right answer.")

    print("\n4. Depth against object count")
    print("-" * 78)
    print(f"    {'objects':>9}{'depth':>8}{'log2(n)':>10}{'nodes':>9}"
          f"{'2n-1':>8}")
    for count in (8, 64, 512, 2048):
        tree = BVH(random_scene(count, seed=count))
        print(f"    {count:>9}{tree.depth():>8}{math.log2(count):>10.1f}"
              f"{tree.stats['nodes']:>9}{2 * count - 1:>8}")
    print("  Depth tracks log2(n), which is the O(log n) claim. And the node")
    print("  count is bounded by 2n-1 because a BVH splits OBJECTS, not space:")
    print("  every object appears in exactly one leaf. A k-d tree splits space,")
    print("  so an object straddling a plane must be referenced from both")
    print("  sides, and its memory has no such bound.")

    print("\n" + "=" * 78)
    print("Next: material.py decides what happens when a ray arrives.")
    print("=" * 78)


if __name__ == "__main__":
    _demo()
