# Solutions — AI gateway

Complete implementations of `limiter.py`, `circuit.py` and `gateway.py`, plus the provided
`model.py` and `providers.py`. Read them *after* attempting: a solution read cold is just
more prose. Each file opens with its design decisions and has a `__main__` demo that prints a
measurement.

```bash
cd inference-lab/ai-gateway
python3 check.py --all                         # against the templates: every step TODO
cp solutions/*.py . && python3 check.py --all  # 9/9 pass
python3 solutions/gateway.py                   # the demos below
```

To check without touching the templates, copy `solutions/*.py` and `check.py` into an empty
directory and run `python3 check.py --all` there.

## Expected demo output

`python3 solutions/limiter.py` — one tenant at the limit, a second unaffected, and a reset a
window later:

```
tenant   requests -> allowed?
  alice  True
  alice  True
  alice  True
  alice  False
  bob    True
  one window later: alice allowed = True
```

`python3 solutions/circuit.py` — CLOSED → OPEN at the threshold → HALF_OPEN after the fake
timeout → CLOSED on a successful probe:

```
event                     state      allow()
  failure 1               CLOSED     True
  failure 2               CLOSED     True
  failure 3               OPEN       True
  OPEN, next allow          OPEN       False
  30s later (half-open)   HALF_OPEN  True
  probe succeeds            CLOSED     True
```

`python3 solutions/gateway.py` — 1000 requests to a primary that fails every other call, then
an outage. The measured failover counts: **500 primary / 500 fallback**, and 1/1 to the cache
when every provider is down:

```
routing a burst through a primary that fails every other call:
  primary=500 fallback=500 cache=0 (primary calls=1000)
when every provider is down:
  served [cache 0.0ms] (cache) canned answer
  failovers to cache = 1 of 1 requests
```

`python3 solutions/providers.py` — the scripted outcomes and the real wall-clock of a `"slow"`
call (about 30 ms; the exact digit varies):

```
scripted outcomes for primary = [FAIL, FAIL, OK]:
  call 1: ProviderError (provider 'primary' returned an error)
  call 2: ProviderError (provider 'primary' returned an error)
  call 3: [primary 8.0ms] primary: q
  a 'slow' provider took 30.1 ms wall-clock and reports 30.0 ms TTFT
```

`python3 solutions/model.py` — the response's string form:

```
[primary 12.0ms] the answer
[cache 0.0ms] (cache) canned
```

## Reading the solutions

- `limiter.py` — fixed window, one lock, the tenant is the key. The boundary burst is the
  documented cost; the breaker is the second defence.
- `circuit.py` — the split `allow()` / `record_success()` / `record_failure()` state machine,
  with exactly one probe in HALF_OPEN.
- `gateway.py` — the chain walk: rate-limit, then for each provider skip an open breaker, on
  `ProviderError` record and continue, on success record and return only if inside the SLO.
  After the chain, the cache or `ProviderError`.
