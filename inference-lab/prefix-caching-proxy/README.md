# Prefix-caching proxy

A real HTTP reverse proxy (stdlib `http.server` / `http.client`, threads, ephemeral
127.0.0.1 ports) in front of N fake inference replicas. Each replica owns a token-level
prefix cache and reports, per request, how many prompt tokens it **reused** versus
**recomputed**. Your job is the one decision that turns a load balancer into a
*cache-aware* router: which replica receives each prompt.

This is inference-lab project **#4**. It is CPU-real: the prefix matching, the cache
eviction and the routing are the real thing, and the hit-rate numbers are measured on
this machine, not simulated from published hardware numbers.

## Why this, and what it teaches

An inference replica caches the prompt prefixes it has already prefilled. If two requests
share a long prefix and reach the same replica, the second skips that prefill. Round-robin
— the default — scatters a shared system prompt across every replica, so each one keeps
evicting it to make room for someone else's. Routing is a caching decision, not only a
fairness decision. The tension (longest-prefix minimises recomputed tokens but piles work
on hot replicas; least-loaded does the reverse) is the same one `context-caching/`
explores, here against a real proxy and real HTTP.

## Steps

| step | file | check | what you build |
|---|---|---|---|
| 1 | `proxy.py` | a client gets the right response through the proxy | `Proxy.generate`: choose a replica, forward the request, return its reply |
| 2 | `policy.py` | longest shared prefix wins | `LongestPrefixPolicy.choose` |
| 3 | `policy.py` | cold request falls back to least loaded | `least_loaded` + the fallback branch |
| 4 | `proxy.py` | routing follows the prompt, not the last response | route on the incoming prompt |
| 5 | `policy.py` | cache-hit gain over round-robin on the trace | the payoff, measured |

Steps 1 and 4 are HTTP end to end. Steps 2, 3 and 5 drive the policies directly so the
workload can be replayed fast and deterministically (the demo in `policy.py` shows the
same numbers end to end if you want them over sockets).

## How to run

```bash
cd inference-lab/prefix-caching-proxy
python3 check.py            # stop at the first unimplemented step
python3 check.py --all      # every step; TODO is not a failure
```

Provided and not to be edited: `replica.py` (replicas, prefix cache, HTTP plumbing),
`workload.py` (the traced workload). `check.py` and `solutions/` are the grader and the
reference. Start each file's `__main__` demo once it runs.

## Design decisions (named, with the cost)

- **HTTP, not an in-process function.** A proxy you cannot point a client at teaches less
  than one you can. The cost is per-request connection overhead, which is why the graded
  workload runs in-process and only the correctness/routing checks use sockets.
- **Proxy reads replica caches directly** (`replica.cached_prefix_len`) instead of an RPC
  fan-out per request. This stands in for a shared routing table a real scheduler keeps;
  an RPC per request would add a cache-miss-sized round trip to the hot path.
- **Capacity is unique stored tokens**, and the served sequence (prompt + output) is what
  gets cached. Output tokens are exactly the pollution that makes routing matter.
- **Deterministic token spaces** (`workload.py`): system, tail and model output tokens are
  disjoint ranges, so a shared-prefix measurement is not an accident of collisions. The
  trace is seeded, so two policies see the identical request order.
- **The fallback is least-loaded, not replica 0.** A cold request is not a 0-token match;
  sending it to whichever replica happens to be first is how a warm cache gets colonised by
  nobody in particular.

## The trace and the measured payoff

`workload.py` generates 200 requests over 8 tenants with Zipf-ish popularity, a 48-token
shared system prompt per tenant, and a 40-token unique tail. Replaying it against 4
replicas of 120 cached tokens on this machine:

```
round-robin     2112 / 11200 prompt tokens reused
longest-prefix  6432 / 11200   (3.05x)
```

The gain falls as capacity grows (1.54x at 300 tokens, 1.14x at 2000): once every replica
holds the whole working set, placement stops mattering. Build this only when the working
set does not fit. And measure your own traffic's prefix-sharing rate first — on uniform
traffic (`uniform_workload`) every policy is identical and the gain is zero.

## Mutation table

`python3 .claude/skills/graded-module/scripts/mutate.py <this dir> <this dir>/_build/mutations.py`

| planted bug | file | step that catches it |
|---|---|---|
| route by always round-robin (ignore the prompt) | `policy.py` | 2 |
| accept the first replica with any match, not the longest | `policy.py` | 2 |
| drop the cold-start fallback, hand 0-token matches to replica 0 | `policy.py` | 3 |
| route on the previous response's replica, not the prompt | `proxy.py` | 4 |

## Questions (answer them yourself)

1. With 4 replicas and a cache that fits the whole working set, does any routing policy
   beat round-robin? Why or why not?
2. Why does an eviction policy that protects shared prefixes (leaves-only eviction, as in
   `context-caching/radix_cache.py`) change the router's optimum?
3. Your hottest tenant now contributes half the traffic. Longest-prefix concentrates it on
   one replica. What metric breaks first — total tokens recomputed, or tail latency? What
   would you measure to prove it?
4. The trace here caches prompt + output. If only prompts were cached, how would the
   round-robin baseline move, and why?
5. A replica dies mid-run. What should the proxy do with a request that was mid-flight to
   it, and what does that cost the cache?

## Limits

- No real model: `model_output` is a deterministic hash, so "generation" costs nothing.
  The measured quantity is prompt-token reuse, which is the part prefix caching actually
  changes.
- The proxy reads replica caches in-process. A real disaggregated router needs that state
  to be consistent across schedulers, which is a distributed-systems problem this module
  does not take on.
- No retries, timeouts beyond the socket timeout, health checks or rate limits; those are
  projects #13 and #14.
