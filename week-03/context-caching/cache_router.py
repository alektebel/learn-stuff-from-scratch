"""
Cache-Aware Request Routing — From Scratch
===========================================
Requires: radix_cache.py.

Once each worker has its own prefix cache, the load balancer's choice decides
the hit rate. Round-robin scatters a shared prefix across every worker; routing
by longest prefix match keeps related requests together — until it overloads
one worker.

Build it to understand:
- That a load balancer is a caching decision, not just a fairness decision
- The real tension between cache affinity and load balance
- Why total work and tail latency do not minimise at the same setting
- When this is worth building at all (and when it provably is not)

Learning Path:
1. Implement Worker.estimate and run over a RadixCache
2. Implement the round_robin, least_loaded and longest_prefix_match policies
3. Implement cache_aware with a load penalty
4. Sweep the load weight and explain the shape of both curves
5. Sweep cache capacity and find where routing stops mattering

Background:
  Each worker holds its own KV prefix cache. The router's job is to place a
  request where its prefix already lives — without piling every request onto
  one machine.

  Two metrics, and they disagree:
    total work  — sum over workers; a throughput/cost measure
    makespan    — the slowest worker; what users actually feel

  Longest-prefix routing minimises total work and can wreck makespan. Pure
  least-loaded does the reverse. The useful policies are in between, and where
  exactly depends on which metric you are paid to optimise.
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
        self.total_work = 0.0
        self.requests_handled = 0
        self.tokens_prefilled = 0
        self.tokens_reused = 0

    def estimate(self, tokens: Sequence[int], gen_len: int) -> Tuple[float, int]:
        """TODO: match the prefix, then return
        ((len(tokens) - matched) * prefill_cost + gen_len * decode_cost, matched).

        Decode cost per token is lower than prefill here because decode is
        memory-bound: it moves the whole KV cache per step but does far less
        arithmetic.
        """
        raise NotImplementedError

    def run(self, tokens: Sequence[int], gen_len: int) -> float:
        """TODO: same cost calculation, then INSERT the sequence into the cache
        and accumulate the stats. Returns the cost."""
        raise NotImplementedError

    @property
    def hit_rate(self) -> float:
        raise NotImplementedError


Policy = Callable[[List[Worker], List[int], int], Worker]


def round_robin() -> Policy:
    """TODO: return a closure cycling through workers, ignoring the tokens."""
    raise NotImplementedError


def least_loaded() -> Policy:
    """TODO: the worker with the least total_work."""
    raise NotImplementedError


def longest_prefix_match() -> Policy:
    """TODO: the worker with the largest matched prefix, breaking ties by load.

    Maximises hit rate, and on skewed traffic concentrates load badly: every
    request sharing the hot system prompt lands on whichever worker saw it
    first, and stays there.
    """
    raise NotImplementedError


def cache_aware(load_weight: float = 1.0) -> Policy:
    """TODO: minimise estimated_cost + load_weight * max(0, work - mean_work).

    The cost term already contains the cache saving, so this naturally prefers
    a warm worker; the penalty pushes work away from a worker that is running
    ahead. Sweep `load_weight` in the demo rather than picking a value and
    calling it tuned.
    """
    raise NotImplementedError


class Router:
    def __init__(self, num_workers: int = 4, policy: Optional[Policy] = None,
                 cache_capacity: int = 4096):
        self.workers = [Worker(i, cache_capacity=cache_capacity)
                        for i in range(num_workers)]
        self.policy = policy or round_robin()

    def dispatch(self, tokens: List[int], gen_len: int = 32) -> Tuple[int, float]:
        """TODO: ask the policy, run on that worker, return (worker id, cost)."""
        raise NotImplementedError

    def report(self) -> Dict[str, float]:
        """TODO: total_work, makespan (the max), imbalance (max/mean), and the
        overall token hit rate."""
        raise NotImplementedError


def skewed_traffic(num_requests: int = 400, num_tenants: int = 16,
                   system_len: int = 300, seed: int = 3) -> List[List[int]]:
    """Many tenants, each with a long system prompt, plus a unique tail.

    TODO: build one system prompt per tenant, pick tenants with Zipf-ish weights
    (1/(t+1)), and append ~20 unique tokens per request.

    Use random.Random, NOT a hand-rolled linear congruential generator. The low
    bits of an LCG have a short period, so `state % num_tenants` produces a
    perfectly cyclic tenant order — which round-robin then lines up with, and
    every policy looks identical. That is a real trap and it cost this file one
    debugging round.
    """
    raise NotImplementedError


def uniform_traffic(num_requests: int = 400, length: int = 320,
                    seed: int = 5) -> List[List[int]]:
    """TODO: every request a unique token range — the control condition."""
    raise NotImplementedError


def run(policy_name: str, policy: Policy, requests: List[List[int]],
        num_workers: int = 4, cache_capacity: int = 2500) -> Dict[str, float]:
    """TODO: build a Router, dispatch everything, return report() plus the name."""
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, produce and explain these five results:

    1. Four policies on skewed traffic (16 tenants, 300-token prompts, 4
       workers, 2500-token caches). Expect roughly:
           round robin       61% hit,  52,000 work,  makespan 14,900
           longest prefix    90% hit,  15,400 work,  makespan  4,400
           cache-aware w=1   89% hit,  16,900 work,  makespan  4,400
       Round robin loses because every worker keeps evicting one tenant's
       system prompt to fit another's.

    2. A load-weight sweep from 0 to 100. At 0 the imbalance is 4.00x on four
       workers — every request goes to one machine. Total work minimises around
       0.05 and makespan around 1.0. They do not coincide; that is the point.

    3. A cache-capacity sweep. Cache-aware routing beats round robin by ~3x at
       2500 tokens and by much less at 40,000, because once every worker holds
       the entire working set, placement stops mattering. Build this only when
       your working set does not fit.

    4. Uniform traffic: every policy identical, 0% hit rate. Measure your real
       traffic's prefix-sharing rate before writing any of this code.

    5. A worker-count sweep. More workers means each sees a thinner slice, so
       per-worker hit rate falls and TOTAL work rises even as makespan improves.
       Scaling out has a cache cost that throughput numbers hide.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
