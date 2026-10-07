# Prefix-caching proxy — solutions

Complete versions of the two templates (`policy.py`, `proxy.py`) plus the provided
infrastructure (`replica.py`, `workload.py`, `check.py` is in the parent). Pure Python 3,
standard library only.

## Verify the solutions

`check.py` imports the files next to it, so run it from a copy that holds the solutions:

```bash
cd inference-lab/prefix-caching-proxy
d=$(mktemp -d) && cp solutions/*.py check.py "$d" && (cd "$d" && python3 check.py --all)
```

Expected:

```
  1. proxy.py     a client gets the right response through the proxy
  2. policy.py    longest shared prefix wins
  3. policy.py    cold request falls back to least loaded
  4. proxy.py     routing follows the prompt, not the last response
  5. policy.py    cache-hit gain over round-robin on the trace

  5/5 passing
```

## Demos

Run from this directory (the files import each other by name).

`python3 replica.py` — reuse on one replica:

```
replica prefix cache — reused vs recomputed on one replica
  request 1 (cold): reused=  0 recomputed= 56
  request 2 (same 48-token prefix): reused= 48 recomputed=  8
  same prompt on a cold replica: reused=  0
  cache holds 80 unique tokens of 200
```

`python3 workload.py` — the traced workload shape:

```
traced_workload: 200 requests, tenants by popularity
  tenant 0:  86 requests
  ...
  two requests of tenant 0 share 48 of 56 prompt tokens
  uniform_workload: longest cross-request shared prefix = 0
```

`python3 policy.py` — decisions and the measured payoff:

```
warm decision: prompt shares 5 tokens with replica 0 and 9 with replica 1 -> chose replica 1
cold decision: no shared prefix, least load -> chose replica 1

traced workload, 4 replicas, in-process replay:
  capacity   100: round-robin   2112/11200 reused, longest-prefix   6432/11200 (3.05x)
  capacity   120: round-robin   2112/11200 reused, longest-prefix   6432/11200 (3.05x)
  capacity   300: round-robin   5856/11200 reused, longest-prefix   9024/11200 (1.54x)
  capacity  2000: round-robin   8112/11200 reused, longest-prefix   9216/11200 (1.14x)
```

The gain is real but capacity-bound: with a cache that holds the whole working set
(2000 tokens over 4 replicas) routing barely matters, which is the condition under which
this whole mechanism is not worth building.

`python3 proxy.py` — the same effect over real HTTP:

```
  first  request -> replica 0: reused=  0 recomputed= 56
  second request -> replica 0: reused= 56 recomputed=  0
  cold   request -> replica 1: reused=  0 (fallback to least loaded)
  proxy handled 3 requests
```

## Design decisions

Each file opens with its `DESIGN DECISION` docstrings; the short version:

- `replica.py`: token trie with per-node refcounts, capacity counted in **unique** stored
  tokens, whole served sequence cached, deterministic replica-independent output.
- `policy.py`: longest cached prefix, ties broken by `(load, id)`, and a **least-loaded
  fallback** when nothing matches. `RoundRobinPolicy` is the baseline.
- `proxy.py`: route on the incoming prompt before forwarding; do not retry or probe.
- `workload.py`: seeded Zipf tenants, disjoint token spaces, and a uniform control where
  every policy scores zero.
