"""
Cache-Aware Request Routing — Complete Solution

Once each worker has its own prefix cache, the load balancer's choice decides
the hit rate. Round-robin scatters a shared prefix across every worker, so each
one pays for it and each one stores it. Routing by longest prefix match keeps
related requests together — until it overloads one worker.

This is SGLang's cache-aware load balancing, and the interesting part is the
tension between the two objectives, not either one alone.
"""

import random
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from radix_cache import RadixCache


class Worker:
    """One inference replica with its own KV prefix cache."""

    def __init__(self, worker_id: int, cache_capacity: int = 4096,
                 prefill_cost_per_token: float = 1.0,
                 decode_cost_per_token: float = 0.2):
        self.worker_id = worker_id
        self.cache = RadixCache(capacity_tokens=cache_capacity)
        self.prefill_cost_per_token = prefill_cost_per_token
        self.decode_cost_per_token = decode_cost_per_token
        self.queue_depth = 0
        self.total_work = 0.0
        self.requests_handled = 0
        self.tokens_prefilled = 0
        self.tokens_reused = 0

    def estimate(self, tokens: Sequence[int], gen_len: int) -> Tuple[float, int]:
        """Cost of running this request here, and how much prefix it can reuse."""
        matched, _, _ = self.cache.match_prefix(tokens)
        prefill = (len(tokens) - matched) * self.prefill_cost_per_token
        decode = gen_len * self.decode_cost_per_token
        return prefill + decode, matched

    def run(self, tokens: Sequence[int], gen_len: int) -> float:
        matched, _, _ = self.cache.match_prefix(tokens)
        to_prefill = len(tokens) - matched
        cost = to_prefill * self.prefill_cost_per_token + \
            gen_len * self.decode_cost_per_token

        self.cache.insert(tokens, [f"kv{i}" for i in range(len(tokens))])
        self.total_work += cost
        self.requests_handled += 1
        self.tokens_prefilled += to_prefill
        self.tokens_reused += matched
        return cost

    @property
    def hit_rate(self) -> float:
        total = self.tokens_prefilled + self.tokens_reused
        return self.tokens_reused / total if total else 0.0


Policy = Callable[[List[Worker], List[int], int], Worker]


def round_robin() -> Policy:
    state = {"next": 0}

    def choose(workers: List[Worker], tokens: List[int], gen_len: int) -> Worker:
        worker = workers[state["next"] % len(workers)]
        state["next"] += 1
        return worker
    return choose


def least_loaded() -> Policy:
    def choose(workers: List[Worker], tokens: List[int], gen_len: int) -> Worker:
        return min(workers, key=lambda w: w.total_work)
    return choose


def longest_prefix_match() -> Policy:
    """Always send a request where its prefix already lives.

    Maximises the hit rate and, on skewed traffic, concentrates load badly:
    every request sharing the hot system prompt lands on whichever worker saw
    it first.
    """
    def choose(workers: List[Worker], tokens: List[int], gen_len: int) -> Worker:
        scored = [(w.estimate(tokens, gen_len)[1], -w.total_work, w)
                  for w in workers]
        return max(scored, key=lambda item: (item[0], item[1]))[2]
    return choose


def cache_aware(load_weight: float = 1.0) -> Policy:
    """Pick the worker with the lowest estimated cost, plus a load penalty.

    Cost already includes the cache saving, so this naturally prefers a warm
    worker — but a worker that is far ahead in total work gets penalised enough
    to send the request elsewhere. `load_weight` is the dial between the two
    objectives; sweep it in the demo rather than guessing.
    """
    def choose(workers: List[Worker], tokens: List[int], gen_len: int) -> Worker:
        mean_work = sum(w.total_work for w in workers) / len(workers)

        def score(worker: Worker) -> float:
            cost, _ = worker.estimate(tokens, gen_len)
            imbalance = max(0.0, worker.total_work - mean_work)
            return cost + load_weight * imbalance
        return min(workers, key=score)
    return choose


class Router:
    def __init__(self, num_workers: int = 4, policy: Optional[Policy] = None,
                 cache_capacity: int = 4096):
        self.workers = [Worker(i, cache_capacity=cache_capacity)
                        for i in range(num_workers)]
        self.policy = policy or round_robin()

    def dispatch(self, tokens: List[int], gen_len: int = 32) -> Tuple[int, float]:
        worker = self.policy(self.workers, tokens, gen_len)
        return worker.worker_id, worker.run(tokens, gen_len)

    def report(self) -> Dict[str, float]:
        works = [w.total_work for w in self.workers]
        prefilled = sum(w.tokens_prefilled for w in self.workers)
        reused = sum(w.tokens_reused for w in self.workers)
        mean = sum(works) / len(works) if works else 0.0
        return {
            "total_work": sum(works),
            "makespan": max(works) if works else 0.0,   # the slowest worker
            "imbalance": (max(works) / mean) if mean else 0.0,
            "hit_rate": reused / (prefilled + reused) if (prefilled + reused) else 0.0,
        }


# ---------------------------------------------------------------------------
# Traffic generators
# ---------------------------------------------------------------------------

def skewed_traffic(num_requests: int = 400, num_tenants: int = 16,
                   system_len: int = 300, seed: int = 3) -> List[List[int]]:
    """Many tenants, each with a long fixed system prompt, plus a unique tail.

    This is what real serving traffic looks like: a set of applications, each
    with a long fixed preamble, short user turns after it, and a popularity
    distribution that is nowhere near uniform. Tenant choice here is Zipf-like,
    so a few tenants dominate — which is what makes routing decisions matter.
    """
    rng = random.Random(seed)
    systems = [list(range(10_000 * (t + 1), 10_000 * (t + 1) + system_len))
               for t in range(num_tenants)]
    weights = [1.0 / (t + 1) for t in range(num_tenants)]        # Zipf
    requests: List[List[int]] = []
    for _ in range(num_requests):
        tenant = rng.choices(range(num_tenants), weights=weights)[0]
        base = rng.randrange(500_000, 900_000)
        requests.append(systems[tenant] + list(range(base, base + 20)))
    return requests


def uniform_traffic(num_requests: int = 400, length: int = 320,
                    seed: int = 5) -> List[List[int]]:
    """Every request unique — nothing to share, so caching cannot help."""
    rng = random.Random(seed)
    requests: List[List[int]] = []
    for _ in range(num_requests):
        base = rng.randrange(1_000_000, 9_000_000)
        requests.append(list(range(base, base + length)))
    return requests


def run(policy_name: str, policy: Policy, requests: List[List[int]],
        num_workers: int = 4, cache_capacity: int = 2500) -> Dict[str, float]:
    router = Router(num_workers=num_workers, policy=policy,
                    cache_capacity=cache_capacity)
    for tokens in requests:
        router.dispatch(tokens)
    result = router.report()
    result["policy"] = policy_name
    result["per_worker_hit"] = [round(w.hit_rate, 3) for w in router.workers]
    return result


def _demo() -> None:
    requests = skewed_traffic(num_requests=400, num_tenants=16, system_len=300)
    print("=== Skewed traffic: 16 Zipf-distributed tenants, 300-token system")
    print("    prompts, 4 workers, 2500-token cache each ===")
    print(f"{'policy':<22}{'hit rate':>10}{'total work':>12}"
          f"{'makespan':>11}{'imbalance':>11}")
    policies = [
        ("round robin", round_robin()),
        ("least loaded", least_loaded()),
        ("longest prefix", longest_prefix_match()),
        ("cache-aware w=1.0", cache_aware(load_weight=1.0)),
    ]
    for name, policy in policies:
        result = run(name, policy, requests)
        print(f"{name:<22}{result['hit_rate']:>9.1%}{result['total_work']:>12,.0f}"
              f"{result['makespan']:>11,.0f}{result['imbalance']:>10.2f}x")

    print("\nRound robin sends every tenant to every worker, so each worker")
    print("keeps evicting one tenant's system prompt to make room for another's.")
    print("Cache-aware routing gives each worker a subset it can actually hold,")
    print("cutting total work by more than half on identical traffic.")
    print("The makespan column is what users feel — it is the slowest worker,")
    print("not the total.")

    print("\n=== Sweeping the load weight ===")
    print(f"{'load_weight':>12}{'hit rate':>10}{'total work':>12}"
          f"{'makespan':>11}{'imbalance':>11}")
    for weight in (0.0, 0.05, 0.2, 1.0, 5.0, 100.0):
        result = run(f"w={weight}", cache_aware(load_weight=weight), requests)
        print(f"{weight:>12.2f}{result['hit_rate']:>9.1%}"
              f"{result['total_work']:>12,.0f}{result['makespan']:>11,.0f}"
              f"{result['imbalance']:>10.2f}x")
    print("weight 0 is pure cache affinity; large weights degenerate toward")
    print("least-loaded. Total work and makespan do not minimise at the same")
    print("setting, which is the whole tension: throughput or tail latency.")

    print("\n=== Cache capacity changes which policy matters ===")
    print(f"{'capacity':>10}{'round robin':>14}{'cache-aware':>14}{'gain':>8}")
    for capacity in (600, 1200, 2500, 5000, 40000):
        rr = run("rr", round_robin(), requests, cache_capacity=capacity)
        ca = run("ca", cache_aware(1.0), requests, cache_capacity=capacity)
        gain = rr["total_work"] / ca["total_work"]
        print(f"{capacity:>10}{rr['hit_rate']:>13.1%}{ca['hit_rate']:>13.1%}"
              f"{gain:>7.2f}x")
    print("With a huge cache every worker holds everything and routing stops")
    print("mattering. Cache-aware routing is worth building exactly when your")
    print("working set does not fit — measure that before you build it.")

    print("\n=== Uniform traffic: nothing to share ===")
    uniform = uniform_traffic(num_requests=400)
    print(f"{'policy':<22}{'hit rate':>10}{'total work':>12}{'imbalance':>11}")
    for name, policy in [("round robin", round_robin()),
                         ("longest prefix", longest_prefix_match()),
                         ("cache-aware w=1.0", cache_aware(load_weight=1.0))]:
        result = run(name, policy, uniform)
        print(f"{name:<22}{result['hit_rate']:>9.1%}"
              f"{result['total_work']:>12,.0f}{result['imbalance']:>10.2f}x")
    print("With no shared prefixes there is nothing to exploit and cache-aware")
    print("routing correctly collapses to load balancing. Measure your traffic's")
    print("prefix-sharing rate before building any of this.")

    print("\n=== Scaling out has a cache cost ===")
    print(f"{'workers':>9}{'hit rate':>10}{'total work':>12}{'makespan':>11}")
    for num_workers in (1, 2, 4, 8, 16):
        result = run("ca", cache_aware(1.0), requests, num_workers=num_workers)
        print(f"{num_workers:>9}{result['hit_rate']:>9.1%}"
              f"{result['total_work']:>12,.0f}{result['makespan']:>11,.0f}")
    print("More workers means each sees a thinner slice of the traffic, so the")
    print("per-worker hit rate falls and TOTAL work rises even as makespan")
    print("improves. Raw throughput numbers hide this.")


if __name__ == "__main__":
    _demo()
