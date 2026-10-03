# Ray Tracer From Scratch

A path tracer in pure Python: the geometry, an acceleration structure, three
materials, and a Monte Carlo integrator. It produces an image in your terminal
and a `.ppm` you can open.

> **Shirley, "Ray Tracing in One Weekend".** [Book](https://raytracing.github.io/)
> — the structure here follows it; the measurements do not.

## Why this directory exists

Rendering is where a *statistics* problem wears a *graphics* costume. The
rendering equation is an integral over every path light could take, there is no
closed form, and the only workable answer is to average random samples of it.
Everything that makes a renderer hard follows from that one fact:

- The image is noisy, and the noise falls as **1/√N** — so halving it costs
  **four times** the work. That is not a detail, it is the industry's entire
  cost structure.
- Every optimisation is really an attack on the constant in front of that √N,
  or on the cost of a single sample. A BVH does the second; importance sampling
  does the first.
- The bugs are *plausible*. A wrong cosine weighting, a missing Fresnel term, a
  hemisphere sampled by angles instead of area — none of them crash, and all of
  them produce an image that looks fine until you compare it to one that is
  right.

So this directory is deliberately heavy on **measurement**. Almost every claim
below is a number the code prints.

## What you build

| File | The mechanism | Stubs |
|---|---|---|
| `vec.py` | Vectors, rays, reflection, refraction, Fresnel, uniform sampling | 13 |
| `shapes.py` | The ray–sphere quadratic, the t window, AABBs | 8 |
| `bvh.py` | A bounding volume hierarchy, median split and the SAH | 5 |
| `material.py` | Matte, metal, glass — one question, three answers | 7 |
| `render.py` | The camera, the integrator, gamma, and 1/√N | 8 |

```bash
cd ray-tracer
python3 check.py          # 6 graded checks against YOUR code
python3 check.py 3        # just step 3
python3 vec.py            # each file has its own demo
python3 render.py         # ~60s, renders the scene several times
```

`check.py` never imports `solutions/`. It tests what you wrote.

---

## The one idea

> **A pixel's colour is an integral. You cannot evaluate it, so you average
> random guesses at it, and the error falls as 1/√N.**

Read that as a bill:

```
      samples   noise (RMS)   predicted   seconds
            1        0.1797      0.1797      0.01
            4        0.0877      0.0899      0.05
           16        0.0440      0.0449      0.18
           64        0.0259      0.0225      0.74
```

Four times the samples for half the noise. A tenth of the noise costs a
**hundred** times. That is why production frames take hours, why denoisers
exist, and why importance sampling is worth more than any amount of
micro-optimisation — it changes the constant, and nothing else can.

---

## The five ideas, and their measurements

### 1. A correct sampler is uniform in AREA, not in angles

The obvious way to pick a random direction is to pick two random angles. It is
wrong, and it renders:

```
       band of z   rejection sampling   uniform angles
     -1.00..-0.67               16.7%            27.0%
     -0.67..-0.33               16.7%            12.4%
     -0.33..-0.00               16.6%            10.6%
      0.00..0.33                16.7%            10.8%
      0.33..0.67                16.7%            12.6%
      0.67..1.00                16.7%            26.5%
```

Every band of equal **height** on a sphere has equal **area** — Archimedes'
theorem — so a correct sampler puts an equal fraction in each. Uniform angles
cluster at the poles, and the render gets a faint directional tint that is
nearly impossible to attribute after the fact.

Rejection sampling (draw in a cube, throw away anything outside the sphere) is
the fix, and it costs about 48% of its draws. That is the DESIGN DECISION: a
known constant factor of waste in exchange for provable uniformity, rather than
a clever closed form that is easy to get subtly wrong.

### 2. Shadow acne, and why 0.001 is a guess

```
       scene scale         t_min=0     t_min=1e-09     t_min=0.001
                x1              25               0               0
            x1,000              29               0               0
        x1,000,000              16              16               0
```

A bounce point is computed as `origin + t * direction`, so its absolute float
error grows with the **magnitude** of the coordinates. At unit scale almost any
epsilon works. At a million units, `1e-9` is far below the noise floor and the
surface re-hits itself — each one a black pixel where a ray bounced off the
inside of the thing it started on.

**`t_min = 0.001` is not derived from anything.** It is a guess that suits a
scene measured in units, which is exactly why renderers that must handle both a
teacup and a solar system use a *relative* epsilon instead. Worth internalising:
a magic constant in a renderer usually encodes an assumption about scale.

### 3. A BVH is an asymptotic win, which makes it invisible on a test scene

```
      objects   brute tests   BVH tests   brute s    BVH s   speedup
            4         2,400           8     0.005    0.003     1.51x
           16         9,600         351     0.017    0.010     1.74x
           64        38,400         514     0.063    0.021     3.01x
          256       153,600       1,282     0.238    0.041     5.80x
         1024       614,400       3,320     0.937    0.078    11.96x
```

At four objects it barely pays; at a thousand it is an order of magnitude. "We
tried an acceleration structure and it did not help" is usually a statement
about the benchmark.

And the SAH against a median split:

```
    scene                          split   depth   tests/ray   build s
    spread out                    median       9         5.3     0.030
    spread out                       sah      11         3.1     0.532
    teapot in a stadium           median       9         4.3     0.032
    teapot in a stadium              sah      12         2.7     0.585
```

**1.6x fewer tests per ray, for 18x the build time, from a *deeper, less
balanced* tree.** Balance was never the goal. A median split insists on half the
objects each side even when the geometry says otherwise; the surface area
heuristic asks the question that actually predicts cost, since a ray hits a box
with probability proportional to its surface area. A film builds once and
renders for hours and buys the expensive tree; an interactive renderer rebuilds
every frame and does not. That is a real trade, not a question with an answer.

Also: node count is bounded by `2n - 1` because a BVH splits **objects**, not
space. A k-d tree splits space, so an object straddling a plane is referenced
from both sides and has no such bound.

### 4. Materials: three answers to one question

The question is *"a ray arrived — where does it go, and how much of it
survives?"* Everything visual falls out of that.

**Matte** — `normal + random_unit_vector()` biases towards the normal by exactly
cos θ, which is Lambert's cosine law:

```
       cos(theta) band   normal + random   uniform hemisphere
        0.0..0.2                   4.0%                19.7%
        0.6..0.8                  28.1%                19.9%
        0.8..1.0                  36.2%                20.6%
```

Sample the hemisphere uniformly instead and the image still renders, just
flatter. **A bug that produces a plausible picture is the hardest kind to find.**

**Metal** — perturb the mirror direction by a roughness radius, and notice what
happens at the extreme:

```
      roughness    mean angle from the mirror direction   absorbed
            0.0                                    0.0°       0.0%
            0.3                                   13.6°       0.0%
            1.0                                   41.2°      14.3%
```

At roughness 1, a seventh of rays point *into* the surface and must be absorbed.
Return them anyway and light leaks out of solid geometry.

**Glass** — Fresnel, applied as a weighted random **choice**, not a blend:

```
      angle from normal   reflected   refracted
                     0°        4.0%       96.0%
                    60°        7.4%       92.5%
                    89°       91.8%        8.2%
```

Look through a window and you see the street; look along it and you see
yourself. One ray in, one ray out — split into two at every glass surface and
you have 2^depth rays by the fifth bounce. The blend emerges from averaging
samples, which a path tracer does for free.

And past the critical angle Snell's law has **no solution**:

```
      angle from normal   escapes   trapped
                    41°     96.0%      4.0%
                    42°      0.0%    100.0%
```

`refract()` returns `None` there rather than a NaN, so the caller has to decide.
That is why the bottom of a glass sphere looks like a mirror, and why fibre
optics work.

### 5. Depth changes BRIGHTNESS, not sharpness

```
      max depth   mean brightness   seconds
              1            0.3106      0.10
              2            0.4739      0.15
              4            0.5486      0.18
              8            0.5551      0.18
```

Nothing in these scenes emits light except the sky. A ray that bounces until it
**escapes** is coloured by what it escapes into; a ray that runs out of bounces
is **black**. So the bounce limit is an energy budget, and it saturates — which
is why an enclosed scene with no emitter renders black, and why "the image is
too dark" is more often a depth or gamma bug than a lighting one.

Speaking of which: gamma moves the demo scene's mean from **0.552 to 0.741**.
sRGB 0.5 emits about 21% of maximum, light transport *is* linear, so it is
computed in linear space and converted at the very end. Skip that one line and
the whole image is uniformly too dark in a way that looks like a lighting bug.

---

## The two bugs the checker is really there to catch

Both are invisible on a symmetric scene, so `check.py` renders an **empty**
world — where `ray_colour` is a pure function of the ray and the *only*
remaining source of randomness is the pixel jitter.

- **The image rendered upside down.** The sky runs white at the horizon to blue
  overhead, so the top row must be the bluer one. On a scene that is roughly
  symmetric, flipping it looks perfectly fine.
- **The pixel never jittered.** Two renders of an empty scene with different
  seeds must differ. If they do not, every sample fires the same ray —
  `samples` times the work for exactly the same staircase edges, and no
  anti-aliasing at all.

## Where this implementation stops

- **No triangles and no meshes.** Spheres and planes only, so there is no
  loading, no vertex normals, and no interpolation. A triangle intersection
  (Möller–Trumbore) is the obvious first extension.
- **No importance sampling and no next-event estimation.** Every path is
  sampled from the BRDF alone and finds light only by wandering into it. This
  is why a small bright light would be catastrophically noisy here.
- **No textures, no normal maps, no participating media.**
- **Pure Python, single-threaded.** Roughly 24,000 rays/second, which is about
  five orders of magnitude off a GPU renderer. Path tracing is embarrassingly
  parallel — each pixel is independent — which is exactly the shape of problem
  [`cuda-from-scratch/`](../../week-16/cuda-from-scratch/) is about.
- **Russian roulette is not implemented**, so paths are terminated by a hard
  depth limit, which biases the result slightly dark.

## Extensions worth trying

1. **Triangles and an OBJ loader**, then re-measure the BVH — a real mesh is
   where the acceleration structure stops being optional.
2. **Next-event estimation**: at each bounce, also sample a point on a light
   directly. Measure the noise at equal sample counts; this is the single
   biggest variance reduction available.
3. **Russian roulette termination** — unbiased, and it removes the depth knob.
4. **Stratified sampling** within the pixel, and measure whether the 1/√N line
   moves.
5. **Multithreading by tile**, and find out what the actual speedup is against
   the core count.

---

## Where it sits

| | This directory | Neighbour |
|---|---|---|
| the parallelism | one thread, one ray at a time | [`cuda-from-scratch/`](../../week-16/cuda-from-scratch/) — the same loop, 10⁵ at once |
| the execution model | branches are free | [`compiler-and-vgpu/`](../../week-15/compiler-and-vgpu/) — one PC for eight lanes, so they are not |
| the sampling | Monte Carlo over light paths | [`diffusion-models/`](../../reference/diffusion-models/) — Monte Carlo over noise schedules |

**Next:** the demos, in order — `vec.py`, `shapes.py`, `bvh.py`, `material.py`,
`render.py`. Then compare with [`solutions/`](solutions/).

## Sources

- Shirley, **Ray Tracing in One Weekend** — the structure here follows it; the measurements do not.
- Pharr, Jakob & Humphreys, **Physically Based Rendering** (free online) — ch. 4 for BVH and the surface area heuristic.
- Kajiya, **"The Rendering Equation"**, SIGGRAPH 1986 — the integral this whole directory estimates.
- MacDonald & Booth, **"Heuristics for Ray Tracing Using Space Subdivision"**, 1990 — where the SAH comes from.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-17--patterns-light-haskell)
