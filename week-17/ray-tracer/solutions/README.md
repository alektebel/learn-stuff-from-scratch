# Ray Tracer From Scratch — Solutions

Complete implementations of every template in the parent directory. Pure Python
3 standard library, no dependencies.

```bash
python3 vec.py            # ~1s
python3 shapes.py         # ~2s
python3 bvh.py            # ~15s, builds and traverses several thousand spheres
python3 material.py       # ~2s
python3 render.py         # ~60s, renders the scene at several settings
```

`render.py` also writes `render.ppm`, which any image viewer will open.

## Implementation notes

- **`Vec3` is a `NamedTuple`.** Immutable, cheap to construct, and it compares
  and hashes by value — which the checker leans on when it asks whether 50 lens
  samples produced 50 distinct origins. The alternative, a mutable class with
  in-place operations, is faster in a language with real value types and is a
  trap in Python: one aliased vector mutated in a loop is a rendering bug you
  will spend a day on.
- **`length_squared` exists because a square root is not free.** Measured at
  1.32x on a hot comparison loop. A ray tracer asks "which is closer" hundreds
  of millions of times and never needs the actual distance to answer it.
- **`refract` returns `Optional[Vec3]`, not a NaN.** Past the critical angle
  Snell's law has no solution and the caller must reflect instead. Returning a
  NaN there gives you black pixels that read as a shadow bug; returning `None`
  forces the decision to the one place that can make it.
- **`random_unit_vector` uses rejection sampling** and throws away about 48% of
  its draws. A known constant factor of waste in exchange for provable
  uniformity in *area* — see the Archimedes table in the parent README for what
  the clever alternative costs you.
- **`Sphere.hit` checks the near root, then the far root**, and both against
  `[t_min, t_max]`. Check only the near one and a ray *inside* a sphere never
  escapes, so glass renders solid black. `front_face` is computed once and the
  normal is flipped to face the ray, so no shading code ever has to ask.
- **`World.hit` passes the closest hit so far as the new `t_max`.** Every shape
  is still tested — that is what brute force means — but each test gets a
  shorter window and rejects sooner. It is free, and it is the only optimisation
  available before an acceleration structure.
- **`AABB.hit` is the slab method** and it divides by direction components that
  may be zero. That is deliberate: IEEE 754 gives ±inf, and the min/max
  comparisons handle it correctly. Guarding the division with a branch is
  slower *and* gets the "parallel and inside the slab" case wrong, which the
  demo tests explicitly.
- **`BVH` defaults to `heuristic="sah"`** with 12 buckets. The median split is
  kept as a working alternative because the comparison is the lesson: the SAH
  wins on tests-per-ray with a *deeper, less balanced* tree, which is only
  surprising if you thought balance was the goal.
- **`BVH.hit` shrinks `t_max` during traversal.** Without it the tree is
  correct and most of the benefit is gone — nodes behind an already-found hit
  are still descended into. The checker injects exactly this bug.
- **Materials return `Optional[Scatter]`.** `None` means absorbed, which is how
  a rough metal reflection pointing *into* the surface is handled. Returning it
  anyway sends the ray through the object it just hit.
- **`Dielectric.scatter` makes a weighted random CHOICE**, not a blend. Split
  into a reflected and a refracted ray at every glass surface and you have
  2^depth rays by the fifth bounce; the blend emerges from averaging samples,
  which a path tracer gets for free.
- **`ray_colour` is iterative, not recursive**, carrying a `throughput` that is
  the product of every attenuation so far. Recursion is the textbook form, hits
  Python's stack limit at depths real renders use, and — more importantly —
  hides the thing worth seeing: a path's contribution is a **product**, so one
  dark surface anywhere along it kills the whole path.
- **`render` jitters within the pixel and iterates `y` from `height - 1` down.**
  Both are one-line details that produce a wrong image nobody notices: no jitter
  means `samples` identical rays and no anti-aliasing; the wrong `y` order means
  an upside-down render that looks fine on a symmetric scene. The checker tests
  both against an *empty* world, where the sky is the only thing on screen and
  pixel jitter is the only randomness left in play.
- **`Camera.ray` samples a point on the lens** when `aperture > 0`. Depth of
  field is not a post-process here; it falls out of modelling the lens as having
  a size, which is what a real lens has. `aperture = 0` is a pinhole and
  consumes no randomness at all.

## What the demos measure

`vec.py` — reflection preserving the angle; the critical angle appearing between
41° and 42°; Schlick's reflectance climbing 4% → 92% from normal to grazing; the
Archimedes band table that separates a correct sphere sampler from a plausible
one; and `length_squared` against `length` on a hot loop.

`shapes.py` — a ray as a half-line (aiming behind you *misses*, even though the
line would hit); the far root taken from inside a sphere; the shadow-acne table
swept across three orders of magnitude of **scene scale**, which is the point —
the epsilon that works at unit scale is below the noise floor at a million; and
the five AABB cases including the two parallel ones.

`bvh.py` — brute force against BVH at 400 spheres (136x fewer intersection
tests, 7.6x wall clock); the crossover table from 4 to 1024 objects showing the
win is *asymptotic*; SAH against median on two scenes, including "teapot in a
stadium"; and depth tracking log₂(n) with node count bounded by 2n−1.

`material.py` — cosine weighting against a uniform hemisphere as a histogram;
roughness against mean deviation from the mirror direction, with the absorbed
fraction appearing at roughness 1; the Fresnel reflected/refracted split by
angle; total internal reflection switching on between 41° and 42°; and the sky
as the only light source in the scene.

`render.py` — the image itself; 1 sample against 16, which is the whole of
anti-aliasing; measured noise against the 1/√N prediction (0.1797 / 0.0877 /
0.0440 / 0.0259 against 0.1797 / 0.0899 / 0.0449 / 0.0225); bounce depth
changing brightness 0.31 → 0.56 and then saturating; gamma moving the mean from
0.552 to 0.741; and depth of field at two apertures on the same scene.
