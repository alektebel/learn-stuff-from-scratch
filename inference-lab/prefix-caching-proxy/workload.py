"""
Traced Workloads for the Prefix-Caching Proxy
=============================================
Provided infrastructure. A *trace* is a fixed, ordered list of requests with no
server attached. Because it is deterministic (seeded) and generated without any
randomness leaking into the servers, the same trace can be replayed against two
different routing policies and the cache-hit numbers compared directly.

The workload models the shape that makes prefix caching matter: many tenants,
each with a long shared system prompt, plus a short unique tail per request.
Tenant popularity is Zipf-ish, so a few prompts are hot and most are cold.

  token spaces:
    system[t] = 1_000_000 + 100_000*t + i     (shared by every request of tenant t)
    tail      = 5_000_000 + 37*k + i         (unique to request k)
  model output tokens are < 50_000, so nothing collides across the three spaces.

`traced_workload` returns dicts {"prompt": [int...], "gen_len": int, "tenant": int}.
`uniform_workload` is the control condition: no two requests share a prefix, so
every policy must score zero reuse.

Run `python3 workload.py` for the demo: the tenant histogram and how much of the
prompt is shared within a tenant.
"""

import random

SYSTEM_BASE = 1_000_000
TAIL_BASE = 5_000_000


def traced_workload(num_requests=200, num_tenants=8, system_len=48,
                    tail_len=8, gen_len=16, seed=7):
    """Skewed, seeded trace: Zipf tenants with a long shared system prompt."""
    rng = random.Random(seed)
    systems = [[SYSTEM_BASE + 100_000 * t + i for i in range(system_len)]
               for t in range(num_tenants)]
    weights = [1.0 / (t + 1) for t in range(num_tenants)]
    cumulative = []
    running = 0.0
    for weight in weights:
        running += weight
        cumulative.append(running)

    requests = []
    for k in range(num_requests):
        draw = rng.random() * running
        tenant = 0
        while tenant < num_tenants - 1 and draw > cumulative[tenant]:
            tenant += 1
        tail = [TAIL_BASE + 37 * k + i for i in range(tail_len)]
        requests.append({"prompt": systems[tenant] + tail,
                         "gen_len": gen_len,
                         "tenant": tenant})
    return requests


def uniform_workload(num_requests=200, length=56, gen_len=16, seed=5):
    """Control: every prompt is a disjoint token range, so reuse is impossible."""
    rng = random.Random(seed)
    requests = []
    for k in range(num_requests):
        start = TAIL_BASE + 100_000 * k
        prompt = [start + i for i in range(length)]
        rng.shuffle(prompt)
        requests.append({"prompt": prompt, "gen_len": gen_len, "tenant": -1})
    return requests


def shared_prefix_len(a, b):
    """Length of the longest common prefix of two token sequences."""
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _demo():
    trace = traced_workload()
    counts = {}
    for request in trace:
        counts[request["tenant"]] = counts.get(request["tenant"], 0) + 1
    print(f"traced_workload: {len(trace)} requests, tenants by popularity")
    for tenant in sorted(counts):
        print(f"  tenant {tenant}: {counts[tenant]:3d} requests")
    first = trace[0]["prompt"]
    same = next(p for p in trace[1:] if p["tenant"] == trace[0]["tenant"])["prompt"]
    print(f"  two requests of tenant {trace[0]['tenant']} share "
          f"{shared_prefix_len(first, same)} of {len(first)} prompt tokens")
    control = uniform_workload()
    cross = max(shared_prefix_len(control[0]["prompt"], r["prompt"])
                for r in control[1:])
    print(f"  uniform_workload: longest cross-request shared prefix = {cross}")


if __name__ == "__main__":
    _demo()
