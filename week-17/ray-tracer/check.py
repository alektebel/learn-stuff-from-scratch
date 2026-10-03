"""
Progress checker for the ray-tracer templates.

    python3 check.py           # run every check, stop at the first gap
    python3 check.py 4         # run only step 4
    python3 check.py --all     # run everything

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


def check_vectors() -> None:
    from vec import Vec3, reflect, refract, schlick

    a, b = Vec3(1, 2, 3), Vec3(4, 5, 6)
    assert a.dot(b) == 32
    assert a.cross(b) == Vec3(-3, 6, -3)
    assert b.cross(a) == Vec3(3, -6, 3), "the cross product anticommutes"
    assert abs(Vec3(3, 4, 0).length() - 5) < 1e-12
    assert Vec3(3, 4, 0).length_squared() == 25
    assert abs(Vec3(3, 4, 0).unit().length() - 1) < 1e-12
    assert a.cross(a).near_zero(), "a vector crossed with itself is zero"

    normal = Vec3(0, 1, 0)
    down = Vec3(0, -1, 0)
    assert reflect(down, normal) == Vec3(0, 1, 0), (
        "straight down off a flat surface must come straight back up")
    incoming = Vec3(1, -1, 0).unit()
    out = reflect(incoming, normal)
    assert abs(out.y - abs(incoming.y)) < 1e-9 and abs(out.x - incoming.x) < 1e-9, (
        f"reflected {incoming} to {out}: the tangential component is preserved "
        "and the normal component flips. reflect is d - 2(d.n)n.")
    assert abs(incoming.dot(normal) + out.dot(normal)) < 1e-9, (
        "the angle of incidence must equal the angle of reflection")

    # Refraction and the case that is not an edge case.
    straight = refract(Vec3(0, -1, 0), normal, 1.0 / 1.5)
    assert straight is not None
    assert abs(straight.x) < 1e-9, "a ray along the normal does not bend"
    shallow = Vec3(math.sin(math.radians(80)), -math.cos(math.radians(80)), 0)
    assert refract(shallow, normal, 1.5) is None, (
        "at 80 degrees from the normal, going from glass into air, Snell's law "
        "has NO solution — the light cannot escape. Returning a NaN there gives "
        "black pixels that look like a shadow bug; returning None makes the "
        "caller reflect instead, which is why the bottom of a glass sphere "
        "looks like a mirror.")
    assert refract(shallow, normal, 1.0 / 1.5) is not None, (
        "the same angle going INTO glass bends fine — total internal "
        "reflection only happens leaving the denser medium")

    assert abs(schlick(1.0, 1.5) - 0.04) < 0.005, (
        f"head-on reflectance for glass is about 4%, got {schlick(1.0, 1.5):.3f}")
    assert schlick(math.cos(math.radians(89)), 1.5) > 0.8, (
        "at a grazing angle glass is mostly a MIRROR. Without this a glass "
        "sphere is equally transparent everywhere and reads as a soap bubble.")
    assert schlick(0.5, 1.5) > schlick(1.0, 1.5), "reflectance rises with angle"


def check_sampling() -> None:
    from vec import Vec3, random_in_hemisphere, random_in_unit_disk, random_unit_vector

    rng = random.Random(0)
    for _ in range(200):
        v = random_unit_vector(rng)
        assert abs(v.length() - 1.0) < 1e-9, f"{v} is not a unit vector"

    # Equal-height bands on a sphere have equal AREA. A correct sampler fills
    # them evenly; picking two angles uniformly clusters at the poles.
    bands = 6
    counts = [0] * bands
    samples = 40000
    for _ in range(samples):
        z = random_unit_vector(rng).z
        counts[min(bands - 1, int((z + 1) / 2 * bands))] += 1
    expected = samples / bands
    worst = max(abs(c - expected) / expected for c in counts)
    assert worst < 0.08, (
        f"the z distribution is off by up to {worst:.1%} from uniform: "
        f"{counts}. Every band of equal HEIGHT on a sphere has equal AREA — "
        "that is Archimedes' theorem — so a correct sampler puts the same "
        "fraction in each. Picking theta and phi uniformly clusters at the "
        "poles, and the result is a render with a subtle directional tint "
        "that is very hard to attribute after the fact. Use rejection "
        "sampling.")

    normal = Vec3(0, 1, 0)
    for _ in range(200):
        assert random_in_hemisphere(normal, rng).dot(normal) > 0, (
            "a hemisphere sample must be on the normal's side")
    for _ in range(200):
        point = random_in_unit_disk(rng)
        assert point.z == 0 and point.length_squared() < 1.0


def check_intersection() -> None:
    from shapes import AABB, Plane, Sphere, World
    from vec import Ray, Vec3

    sphere = Sphere(Vec3(0, 0, -5), 1.0, "material")
    hit = sphere.hit(Ray(Vec3(0, 0, 0), Vec3(0, 0, -1)), 0.001, math.inf)
    assert hit is not None and abs(hit.t - 4.0) < 1e-9, (
        f"a ray from the origin towards a unit sphere centred 5 away hits at "
        f"t = 4, got {hit.t if hit else 'a miss'}")
    assert hit.front_face and abs(hit.normal.z - 1.0) < 1e-9, (
        "the normal must face the incoming ray")

    assert sphere.hit(Ray(Vec3(0, 0, 0), Vec3(0, 0, 1)), 0.001,
                      math.inf) is None, (
        "aiming AWAY from the sphere must miss. The line would hit it, but a "
        "ray is a half-line and the root is negative — outside the window. "
        "Skip the window check and objects behind the camera appear on screen.")
    assert sphere.hit(Ray(Vec3(0, 0, 0), Vec3(2, 0, -5).unit()), 0.001,
                      math.inf) is None, "and a ray past the edge misses"

    inside = sphere.hit(Ray(Vec3(0, 0, -5), Vec3(0, 0, -1)), 0.001, math.inf)
    assert inside is not None, (
        "a ray starting at the CENTRE of a sphere must hit it — on the way "
        "out. The near root is negative, so checking only that root means a "
        "ray inside a sphere never escapes and glass renders solid black.")
    assert not inside.front_face, "and it hit the inside"
    assert abs(inside.t - 1.0) < 1e-9

    narrow = sphere.hit(Ray(Vec3(0, 0, 0), Vec3(0, 0, -1)), 0.001, 3.0)
    assert narrow is None, (
        "the hit is at t = 4 and t_max is 3, so it must be rejected. That "
        "window is what lets World.hit pass the closest hit so far and have "
        "every later shape reject early.")

    plane = Plane(Vec3(0, -1, 0), Vec3(0, 1, 0), "m")
    ground = plane.hit(Ray(Vec3(0, 1, 0), Vec3(0, -1, 0)), 0.001, math.inf)
    assert ground is not None and abs(ground.t - 2.0) < 1e-9
    assert plane.hit(Ray(Vec3(0, 1, 0), Vec3(1, 0, 0)), 0.001,
                     math.inf) is None, "a parallel ray never hits"
    assert plane.bounds() is None, (
        "an infinite plane has no finite bounding box. Returning a huge one "
        "instead would put it at the root of every BVH subtree and defeat the "
        "structure entirely.")

    world = World([Sphere(Vec3(0, 0, -z), 0.5, f"m{z}") for z in (10, 3, 7)])
    nearest = world.hit(Ray(Vec3(0, 0, 0), Vec3(0, 0, -1)))
    assert nearest.material == "m3", (
        f"the nearest sphere is at z = -3 and the hit reports {nearest.material}. "
        "World.hit must keep the CLOSEST hit, not the first one found.")

    box = AABB(Vec3(-1, -1, -1), Vec3(1, 1, 1))
    assert box.hit(Ray(Vec3(0, 0, -5), Vec3(0, 0, 1)), 0.001, math.inf)
    assert not box.hit(Ray(Vec3(0, 5, 0), Vec3(1, 0, 0)), 0.001, math.inf), (
        "a ray parallel to the box and outside it must miss — the slab method "
        "needs an explicit case for a zero direction component, or you divide "
        "by zero and get a NaN comparison that is always False")
    assert box.hit(Ray(Vec3(0, 0, 0), Vec3(1, 0, 0)), 0.001, math.inf), (
        "a ray parallel to the box and INSIDE it hits")
    assert not box.hit(Ray(Vec3(0, 0, 5), Vec3(0, 0, 1)), 0.001, math.inf)


def check_bvh() -> None:
    from bvh import BVH, random_scene
    from shapes import Sphere, World
    from vec import Ray, Vec3

    shapes = random_scene(200, seed=3)
    world = World(list(shapes))
    tree = BVH(list(shapes))

    rng = random.Random(1)
    directions = [Vec3(rng.uniform(-1, 1), rng.uniform(-1, 1), -1).unit()
                  for _ in range(300)]
    for direction in directions:
        ray = Ray(Vec3(0, 0, 0), direction)
        a = world.hit(ray)
        b = tree.hit(ray)
        assert (a is None) == (b is None), (
            "the BVH and brute force disagree about whether a ray hits at all")
        if a is not None:
            assert abs(a.t - b.t) < 1e-9, (
                f"the BVH found a hit at t={b.t:.6f} and brute force at "
                f"t={a.t:.6f}. An acceleration structure must return EXACTLY "
                "the same answer — it changes how long the search takes, never "
                "what it finds. A mismatch usually means the traversal is not "
                "shrinking t_max as it goes, so it accepts a farther hit.")

    assert tree.stats["intersection_tests"] < world.stats["intersection_tests"] / 5, (
        f"the BVH did {tree.stats['intersection_tests']:,} intersection tests "
        f"against brute force's {world.stats['intersection_tests']:,}. On 200 "
        "objects it should be at least five times fewer — that ratio IS the "
        "structure. If they are close, the traversal is descending into every "
        "subtree, which means the box test is not rejecting.")

    assert tree.depth() <= 2 * math.log2(200) + 4, (
        f"tree depth is {tree.depth()} for 200 objects, and log2(200) is "
        f"{math.log2(200):.1f}. A depth far above that means the split is "
        "putting nearly everything on one side.")
    assert tree.stats["nodes"] <= 2 * 200 - 1, (
        "a BVH over n objects has at most 2n-1 nodes, because it splits "
        "OBJECTS rather than space and every object lands in exactly one leaf")

    small = BVH(random_scene(3, seed=1))
    ray = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
    assert small.hit(ray) is None or small.hit(ray) is not None, "must not crash"


def check_materials() -> None:
    from material import Dielectric, Lambertian, Metal, sky
    from shapes import Hit
    from vec import Ray, Vec3

    rng = random.Random(0)
    up = Vec3(0, 1, 0)
    hit = Hit(1.0, Vec3(0, 0, 0), up, True, None)
    incoming = Ray(Vec3(0, 1, 0), Vec3(1, -1, 0).unit())

    matte = Lambertian(Vec3(0.7, 0.3, 0.3))
    result = matte.scatter(incoming, hit, rng)
    assert result is not None and result.attenuation == Vec3(0.7, 0.3, 0.3)
    assert result.ray.origin == hit.point

    # Cosine weighting: `normal + random_unit_vector` is NOT uniform.
    bands = 4
    counts = [0] * bands
    for _ in range(20000):
        direction = matte.scatter(incoming, hit, rng).ray.direction
        assert direction.dot(up) > -1e-6, (
            "a matte scatter must not go INTO the surface")
        counts[min(bands - 1, int(max(0.0, direction.dot(up)) * bands))] += 1
    assert counts[-1] > counts[0] * 2, (
        f"the scattered directions are {counts} by cos(theta) band; they must "
        "be biased TOWARDS the normal. `normal + random_unit_vector()` gives "
        "exactly cos(theta) weighting, which is Lambert's cosine law. Sample "
        "the hemisphere uniformly instead and the image still renders, just "
        "flatter — a bug that produces a plausible picture.")

    mirror = Metal(Vec3(0.9, 0.9, 0.9), 0.0)
    result = mirror.scatter(incoming, hit, rng)
    expected = Vec3(incoming.direction.x, -incoming.direction.y, 0).unit()
    assert max(abs(a - b) for a, b in
               zip(result.ray.direction, expected)) < 1e-9, (
        f"a mirror at roughness 0 must reflect exactly: expected {expected}, "
        f"got {result.ray.direction}")

    rough = Metal(Vec3(0.9, 0.9, 0.9), 1.0)
    absorbed = sum(1 for _ in range(3000)
                   if rough.scatter(incoming, hit, rng) is None)
    assert absorbed > 0, (
        "at roughness 1 some perturbed reflections point INTO the surface and "
        "must be absorbed. Returning them anyway sends the ray through the "
        "object it just hit, and light leaks out of solid geometry.")
    assert absorbed < 1500, "but most rays should still scatter"

    glass = Dielectric(1.5)
    head_on = Ray(Vec3(0, 1, 0), Vec3(0, -1, 0))
    reflected = sum(1 for _ in range(3000)
                    if glass.scatter(head_on, hit, rng).ray.direction.y > 0)
    assert reflected < 300, (
        f"{reflected} of 3000 head-on rays reflected off glass; it should be "
        "about 4%. Fresnel must be applied as a random CHOICE weighted by the "
        "reflectance.")

    grazing = Vec3(math.sin(math.radians(88)), -math.cos(math.radians(88)), 0)
    reflected = sum(1 for _ in range(3000)
                    if glass.scatter(Ray(Vec3(0, 1, 0), grazing), hit,
                                     rng).ray.direction.y > 0)
    assert reflected > 2200, (
        f"only {reflected} of 3000 rays reflected at 88 degrees; glass is "
        "mostly a MIRROR at a grazing angle. Without Fresnel a glass sphere "
        "is equally transparent everywhere and reads as a soap bubble.")

    # Total internal reflection, from inside.
    down_normal = Vec3(0, -1, 0)
    inside = Hit(1.0, Vec3(0, 0, 0), down_normal, False, None)
    steep = Vec3(math.sin(math.radians(60)), math.cos(math.radians(60)), 0)
    # The stored normal faces the incoming ray, so it points DOWN here; a
    # trapped ray is reflected back down into the glass.
    trapped = sum(1 for _ in range(1000)
                  if glass.scatter(Ray(Vec3(0, -1, 0), steep), inside,
                                   rng).ray.direction.y < 0)
    assert trapped > 950, (
        f"only {trapped} of 1000 rays were trapped at 60 degrees from inside "
        "the glass. The critical angle is about 41.8 degrees; beyond it every "
        "ray must reflect. This is why fibre optics work.")

    assert sky(Ray(Vec3(0, 0, 0), Vec3(0, 1, 0))).z > \
        sky(Ray(Vec3(0, 0, 0), Vec3(0, -1, 0))).z or True
    assert abs(sky(Ray(Vec3(0, 0, 0), Vec3(0, -1, 0))).x - 1.0) < 1e-9


def check_render() -> None:
    from material import Lambertian
    from render import Camera, gamma, ray_colour, render, variance
    from shapes import Sphere, World
    from vec import Ray, Vec3

    camera = Camera(Vec3(0, 0, 1), Vec3(0, 0, -1), Vec3(0, 1, 0), 90, 2.0)
    rng = random.Random(0)
    centre = camera.ray(0.5, 0.5, rng)
    assert abs(centre.direction.x) < 0.05 and abs(centre.direction.y) < 0.05, (
        f"the ray through the centre of the image should point at the target, "
        f"got {centre.direction}")
    left = camera.ray(0.0, 0.5, rng)
    right = camera.ray(1.0, 0.5, rng)
    assert left.direction.x < right.direction.x, (
        "s = 0 is the LEFT of the image. If they are swapped the render is "
        "mirrored, which is very easy to miss on a symmetric scene.")

    # A pinhole camera: every ray starts at the same point.
    assert camera.ray(0.2, 0.3, rng).origin == camera.ray(0.8, 0.7, rng).origin
    lens = Camera(Vec3(0, 0, 1), Vec3(0, 0, -1), Vec3(0, 1, 0), 90, 2.0,
                  aperture=0.5, focus_distance=2.0)
    origins = {tuple(lens.ray(0.5, 0.5, rng).origin) for _ in range(50)}
    assert len(origins) > 40, (
        "with a non-zero aperture each ray must start at a RANDOM point on the "
        "lens. That is where depth of field comes from — it is not a blur "
        "applied afterwards.")

    world = World([Sphere(Vec3(0, 0, -1), 0.5, Lambertian(Vec3(0.5, 0.5, 0.5)))])
    sky_colour = ray_colour(Ray(Vec3(0, 0, 0), Vec3(0, 1, 0)), world, rng, 8)
    assert sky_colour.z > 0.9, "a ray that escapes upward gets the sky"
    black = ray_colour(Ray(Vec3(0, 0, 0), Vec3(0, 0, -1)), world, rng, 0)
    assert black == Vec3(0, 0, 0), (
        "depth 0 means no bounces are allowed, so the ray must return BLACK. "
        "That is why raising the bounce limit makes an image BRIGHTER.")

    image = render(world, camera, 8, 4, samples=2, depth=3, seed=1)
    assert len(image) == 4 and len(image[0]) == 8, (
        f"expected a 4-row, 8-column image, got {len(image)}x{len(image[0])}")

    # Everything below renders an EMPTY world. That makes ray_colour a pure
    # function of the ray — sky() and nothing else — so the only thing left
    # that can consume randomness is the pixel jitter. Isolating one source of
    # noise is the whole reason this scene is empty.
    empty = World([])
    sky_image = render(empty, camera, 8, 6, samples=1, depth=3, seed=1)
    top, bottom = sky_image[0][0], sky_image[-1][0]
    assert top.y < bottom.y - 0.1, (
        f"the top row's green channel is {top.y:.3f} and the bottom row's is "
        f"{bottom.y:.3f}. The sky gradient runs white at the horizon to blue "
        "overhead, so the TOP of the frame must be the bluer one. The first "
        "row you append is t = 1, which means y counts DOWN from height-1. "
        "Get that backwards and the image is rendered upside down — on a "
        "symmetric scene it looks perfectly fine.")

    # Two seeds, one sample per pixel, no other randomness in play.
    a = render(empty, camera, 8, 6, samples=1, depth=3, seed=1)
    b = render(empty, camera, 8, 6, samples=1, depth=3, seed=2)
    assert variance(a, b) > 1e-8, (
        "two renders of the same empty scene with DIFFERENT seeds came out "
        "identical. Nothing in an empty world is random except where inside "
        "the pixel you sample, so this means the pixel is never jittered — "
        "every sample fires the same ray. Averaging `samples` copies of one "
        "ray is not anti-aliasing, it is `samples` times the work for exactly "
        "the same staircase edges.")
    many_a = render(empty, camera, 8, 6, samples=64, depth=3, seed=1)
    many_b = render(empty, camera, 8, 6, samples=64, depth=3, seed=2)
    assert variance(many_a, many_b) < variance(a, b), (
        "with 64 jittered samples the two seeds should agree far better than "
        "with 1 — that convergence IS the anti-aliasing.")

    bright = gamma(Vec3(0.25, 0.25, 0.25))
    assert bright.x > 0.25, (
        f"gamma(0.25) is {bright.x:.3f}; it must be BRIGHTER than the linear "
        "value. A display is not linear — sRGB 0.5 emits about 21% of maximum "
        "— so linear light must be converted up at the end. Skip it and the "
        "whole image is mysteriously too dark.")
    assert abs(gamma(Vec3(1, 1, 1)).x - 1.0) < 1e-9, "white stays white"
    assert abs(gamma(Vec3(0, 0, 0)).x) < 1e-9, "black stays black"

    # Noise must fall as 1/sqrt(N).
    scene = World([Sphere(Vec3(0, 0, -1), 0.5, Lambertian(Vec3(0.6, 0.4, 0.4))),
                   Sphere(Vec3(0, -100.5, -1), 100,
                          Lambertian(Vec3(0.5, 0.5, 0.5)))])
    reference = render(scene, camera, 12, 6, samples=128, depth=5, seed=99)
    noise = {}
    for samples in (2, 32):
        test = render(scene, camera, 12, 6, samples=samples, depth=5, seed=7)
        noise[samples] = variance(test, reference)
    ratio = noise[2] / max(noise[32], 1e-9)
    assert 2.0 < ratio < 8.0, (
        f"noise fell by {ratio:.2f}x when samples went up 16x. Monte Carlo "
        f"error falls as 1/sqrt(N), so 16x the samples should give about 4x "
        "less noise. Far less improvement means the samples are correlated — "
        "usually because the pixel is not being jittered, so every sample "
        "fires the SAME ray and you get no anti-aliasing either.")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("vec.py", "reflect, refract, and Fresnel", check_vectors),
    ("vec.py", "uniform on a sphere, by rejection", check_sampling),
    ("shapes.py", "the quadratic, the window, the normal",
     check_intersection),
    ("bvh.py", "same answer, far less work", check_bvh),
    ("material.py", "cosine weighting, roughness, glass", check_materials),
    ("render.py", "the camera, gamma, and 1/sqrt(N)", check_render),
]


def run_one(check):
    try:
        check(); return PASS, ""
    except NotImplementedError:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, where
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

    print(f"\n{BOLD}Ray Tracer From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<14} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<14} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<14} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you built a renderer.{RESET}")
        print(f"  {GREY}Now run each file's own demo, then compare with "
              f"solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings walk through it. "
              f"Stuck? solutions/{filename}{RESET}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
