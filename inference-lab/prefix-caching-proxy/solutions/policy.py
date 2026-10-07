"""
Routing Policies for a Prefix-Caching Proxy — From Scratch
==========================================================
Requires: replica.py (provides the replicas and their prefix caches).

An inference replica caches the prompt prefixes it has already prefilled. If two
requests share a long prefix and reach the *same* replica, the second one skips
that prompt prefill. Round-robin — the default load balancer — scatters a shared
system prompt across every replica, so each one keeps evicting it to make room
for someone else's. Routing is a caching decision, not only a fairness decision.

You implement the two pieces the router needs:

  1. `least_loaded(replicas)` — the fallback used when no replica holds any part
     of the prompt (a cold request, or uniform traffic with no sharing).
  2. `LongestPrefixPolicy.choose(replicas, prompt)` — pick the replica with the
     LONGEST shared prefix; when the best match is zero, fall back to
     `least_loaded`, and break ties between equally good matches by load.

`RoundRobinPolicy` is provided unchanged as the baseline you are measured
against.

Learning path:
 1. Implement `least_loaded`, then `LongestPrefixPolicy.choose`.
 2. Run `python3 check.py`; step 2 should be your first gap after the proxy.
 3. Watch step 5: the same trace through round-robin versus longest-prefix.
 4. Sweep the cache capacity in the demo and find where routing stops mattering.

Background — where the tension lives:
  Longest-prefix routing minimises tokens recomputed (total work) and can
  concentrate load, because every request sharing the hot prompt lands on
  whichever replica saw it first and stays there. Least-loaded does the reverse:
  it balances work but throws the cache away. A production router blends them;
  this module keeps the two ends and asks which one you are paid to optimise.

Run `python3 policy.py` for the demo: a warm/cold decision, then the hit-rate
gain of longest-prefix over round-robin across cache sizes.
"""

from typing import List, Sequence

from replica import Replica


class RoundRobinPolicy:
    """Baseline: cycle through replicas, ignoring the prompt entirely."""

    name = "round_robin"

    def __init__(self):
        self._next = 0

    def choose(self, replicas: List[Replica], prompt: Sequence[int]) -> Replica:
        replica = replicas[self._next % len(replicas)]
        self._next += 1
        return replica

    def reset(self) -> None:
        self._next = 0


def least_loaded(replicas: List[Replica]) -> Replica:
    """The replica with the least accumulated work (`load`), lowest id to break ties.

    TODO:
      `load` is the tokens that replica has had to recompute so far, so it is the
      work-aware part of the decision. Return the unique minimum; do not mutate.
    """
    return min(replicas, key=lambda replica: (replica.load, replica.id))


class LongestPrefixPolicy:
    """Route to the replica holding the longest shared prefix; else least loaded."""

    name = "longest_prefix"

    def choose(self, replicas: List[Replica], prompt: Sequence[int]) -> Replica:
        """TODO: score each replica by `cached_prefix_len(prompt)` and pick the best.

        - Compute the matched prefix length for every replica (each replica owns
          a PrefixCache; call `replica.cached_prefix_len(prompt)`).
        - If the best match is 0 (nothing shared anywhere) this is a cold
          request: return `least_loaded(replicas)`.
        - Otherwise return the replica with the largest match; break ties by the
          same `(load, id)` rule. Do NOT return the first replica with *any*
          match — a shorter match is strictly worse than a longer one.
        """
        best = max(replicas, key=lambda replica: replica.cached_prefix_len(prompt))
        best_len = best.cached_prefix_len(prompt)
        if best_len == 0:
            return least_loaded(replicas)
        tied = [replica for replica in replicas
                if replica.cached_prefix_len(prompt) == best_len]
        return min(tied, key=lambda replica: (replica.load, replica.id))

    def reset(self) -> None:
        pass


def make_policy(name: str):
    """Factory used by the demo and the checks."""
    if name == "round_robin":
        return RoundRobinPolicy()
    if name == "longest_prefix":
        return LongestPrefixPolicy()
    raise ValueError(f"unknown policy: {name!r}")


def _demo():
    from replica import Replica

    replicas = [Replica(i, cache_capacity=400) for i in range(3)]
    replicas[0].cache.insert([1, 2, 3, 4, 5])
    replicas[1].cache.insert([1, 2, 3, 4, 5, 6, 7, 8, 9])
    replicas[2].cache.insert([9, 8, 7])
    policy = LongestPrefixPolicy()
    warm = policy.choose(replicas, [1, 2, 3, 4, 5, 6, 7, 8, 9, 99])
    print("warm decision: prompt shares 5 tokens with replica 0 and 9 with "
          f"replica 1 -> chose replica {warm.id}")
    replicas[0].load = 100
    replicas[1].load = 10
    replicas[2].load = 50
    cold = policy.choose(replicas, [700, 800, 900])
    print(f"cold decision: no shared prefix, least load -> chose replica {cold.id}")

    from workload import traced_workload

    trace = traced_workload()
    print("\ntraced workload, 4 replicas, in-process replay:")
    for capacity in (100, 120, 300, 2000):
        reused = {}
        for name in ("round_robin", "longest_prefix"):
            replicas = [Replica(i, cache_capacity=capacity) for i in range(4)]
            policy = make_policy(name)
            hit = 0
            total = 0
            for request in trace:
                chosen = policy.choose(replicas, request["prompt"])
                reply = chosen.handle(request["prompt"], request["gen_len"])
                hit += reply["reused"]
                total += reply["reused"] + reply["recomputed"]
            reused[name] = (hit, total)
        rr, lp = reused["round_robin"], reused["longest_prefix"]
        print(f"  capacity {capacity:5d}: round-robin {rr[0]:6d}/{rr[1]} reused, "
              f"longest-prefix {lp[0]:6d}/{lp[1]} "
              f"({lp[0] / max(rr[0], 1):.2f}x)")


if __name__ == "__main__":
    _demo()
