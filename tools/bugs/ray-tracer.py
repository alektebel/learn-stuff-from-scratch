import pathlib, shutil, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2] / "week-17" / "ray-tracer"
BUGS = [
 (1, "vec.py", "reflect subtracts once instead of twice",
  "    return direction - normal * (2.0 * direction.dot(normal))",
  "    return direction - normal * direction.dot(normal)"),
 (1, "vec.py", "refract returns a value past the critical angle",
  "    if sin_theta_squared > 1.0:\n        return None",
  "    if sin_theta_squared > 1.0:\n        sin_theta_squared = 1.0"),
 (1, "vec.py", "Schlick without the fifth power",
  "    return r0 + (1 - r0) * ((1 - cosine) ** 5)",
  "    return r0"),
 (2, "vec.py", "sampling by uniform angles instead of rejection",
  '''    while True:
        candidate = Vec3(rng.uniform(-1, 1), rng.uniform(-1, 1),
                         rng.uniform(-1, 1))
        squared = candidate.length_squared()
        if 1e-12 < squared <= 1.0:
            return candidate / math.sqrt(squared)''',
  '''    theta = rng.uniform(0, math.pi)
    phi = rng.uniform(0, 2 * math.pi)
    return Vec3(math.sin(theta) * math.cos(phi),
                math.sin(theta) * math.sin(phi), math.cos(theta))'''),
 (3, "shapes.py", "only the near root is checked",
  "        for root in ((-half_b - root_disc) / a, (-half_b + root_disc) / a):",
  "        for root in ((-half_b - root_disc) / a,):"),
 (3, "shapes.py", "the t window is ignored",
  "            if t_min < root < t_max:",
  "            if root > -1e30:"),
 (3, "shapes.py", "World.hit keeps the first hit, not the closest",
  "            hit = shape.hit(ray, t_min, closest)\n            if hit is not None:\n                closest = hit.t\n                best = hit",
  "            hit = shape.hit(ray, t_min, closest)\n            if hit is not None and best is None:\n                best = hit"),
 (3, "shapes.py", "AABB divides by a zero direction component",
  "            if abs(direction) < 1e-12:\n                if not (self.low[axis] <= origin <= self.high[axis]):\n                    return False\n                continue",
  "            if abs(direction) < 1e-300:\n                continue"),
 (4, "bvh.py", "traversal does not shrink t_max",
  "                    hit = shape.hit(ray, t_min, closest)\n                    if hit is not None:\n                        closest, best = hit.t, hit",
  "                    hit = shape.hit(ray, t_min, t_max)\n                    if hit is not None and best is None:\n                        best = hit"),
 (4, "bvh.py", "the box test is skipped",
  "            if not node.box.hit(ray, t_min, closest):\n                continue",
  "            if False:\n                continue"),
 (5, "material.py", "matte samples the hemisphere uniformly",
  "        direction = hit.normal + random_unit_vector(rng)",
  "        direction = random_in_hemisphere(hit.normal, rng)"),
 (5, "material.py", "a metal reflection into the surface is returned anyway",
  "        if reflected.dot(hit.normal) <= 0:\n            return None",
  "        if False:\n            return None"),
 (5, "material.py", "glass ignores Fresnel",
  "        if refracted is None or schlick(cos_theta, ratio) > rng.random():",
  "        if refracted is None:"),
 (6, "render.py", "the pixel is never jittered",
  "                s = (x + rng.random()) / (width - 1)\n                t = (y + rng.random()) / (height - 1)",
  "                s = (x + 0.5) / (width - 1)\n                t = (y + 0.5) / (height - 1)"),
 (6, "render.py", "gamma applied the wrong way round",
  "    inverse = 1.0 / power",
  "    inverse = power"),
 (6, "render.py", "the image is rendered upside down",
  "    for y in range(height - 1, -1, -1):",
  "    for y in range(height):"),
]
failures = []
for step, filename, label, old, new in BUGS:
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "s"
        shutil.copytree(ROOT / "solutions", work, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(ROOT / "check.py", work / "check.py")
        target = work / filename
        text = target.read_text()
        if old not in text:
            print(f"  step {step:>2}  PATCH-FAIL {label}")
            failures.append(f"[{step}] {label}: patch did not apply"); continue
        target.write_text(text.replace(old, new, 1))
        r = subprocess.run([sys.executable, "check.py", str(step)], cwd=work,
                           capture_output=True, text=True, timeout=600)
        caught = "✗" in r.stdout
        print(f"  step {step:>2}  {'caught' if caught else 'MISSED':<7} {label}")
        if not caught: failures.append(f"[{step}] {label}\n{r.stdout[:250]}")
print()
if failures:
    print("PROBLEMS:")
    for f in failures: print(" ", f)
    sys.exit(1)
print(f"all {len(BUGS)} injected bugs were caught")
