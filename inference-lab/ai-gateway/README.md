# AI gateway — a graded module

`inference-lab` project **#13** (CPU-real). A gateway sits in front of several fake model
providers. It routes each request to a provider and, on failure or an SLO breach, degrades
down a chain: **primary → fallback → static cache**.

You build the routing and degradation policy; the providers, the request/response model and
the plumbing are given. Everything is standard-library only and runs **in-process** (no
sockets, no sleeps needed for the checks): the provider reports its own time-to-first-token
so SLO breaches are deterministic, and the gateway's clock is injected so no test waits.

## Run it

```bash
cd inference-lab/ai-gateway
python3 check.py            # stop at the first step you have not written
python3 check.py --all      # run every check, report every TODO
python3 check.py 5 7        # only steps 5..7
```

`solutions/` holds complete implementations and `_build/` the hints and planted bugs.

## What you write, what is given

| File | Who | What |
|---|---|---|
| `model.py` | given | `Request`/`Response`, the error taxonomy (`ProviderError`, `RateLimitedError`, …) |
| `providers.py` | given | `Provider` with a cycling latency/error script, `StaticCache` |
| `limiter.py` | **you** | per-tenant fixed-window rate limiting |
| `circuit.py` | **you** | per-provider circuit breaker (CLOSED → OPEN → HALF-OPEN) |
| `gateway.py` | **you** | the routing/degradation policy that joins them |

## The steps

| # | File | The check proves |
|---|---|---|
| 1 | `limiter.py` | a tenant's third request in the window is denied, a second tenant is unaffected |
| 2 | `limiter.py` | the counter resets once a full window has passed |
| 3 | `circuit.py` | the breaker opens at the failure threshold and refuses calls |
| 4 | `circuit.py` | after `recovery_timeout` it half-opens; a successful probe closes it |
| 5 | `gateway.py` | a healthy primary serves the request, undegraded |
| 6 | `gateway.py` | a primary failure advances to the fallback |
| 7 | `gateway.py` | with every provider down the static cache answers; with no cache, `ProviderError` |
| 8 | `gateway.py` | a TTFT breach degrades, an in-budget success does not |
| 9 | `gateway.py` | the gateway consults the tenant quota before calling any provider |

## Design decisions

They are argued in the file docstrings; the short list:

- **In-process, injected clock.** The policy is under test, not HTTP framing; `FakeClock`
  makes window resets and breaker recovery deterministic without sleeping.
- **One error class per failure mode.** A quota violation (429) and a provider failure
  (route onward) must not be confused; `except GatewayError` cannot swallow a rate limit.
- **A TTFT breach is healthy-slow, not a breaker failure.** The provider answered, so its
  breaker records success and the router simply tries the next link.
- **A per-provider breaker.** One failing link must not eject a healthy replica.
- **The chain is exhausted → cache or `ProviderError`.** The gateway never invents an answer.

## Questions (answer them yourself before reading `solutions/`)

1. You rate-limit in front of the chain. Where should the limiter sit so a degraded request
   to the cache still costs the tenant a token — or should it?
2. The breaker's OPEN → HALF_OPEN transition happens inside `allow()`. What changes if a
   background thread does it instead? When would you prefer each?
3. A tenant over quota gets `RateLimitedError`. Should the gateway try the fallback for that
   tenant anyway? What does the answer depend on?
4. The SLO is per request. What goes wrong if it is per provider instead?
5. When all providers are down, the cache answers. What stops the cache from answering
   forever after the providers recover? (Reproduce it; then decide.)

## Limit cases the checks pin down

- A tenant at exactly `limit` is admitted; one more is denied — off-by-one at the boundary.
- A window reset at `clock == k * window_seconds` (integer division).
- One probe at a time in HALF_OPEN (a failing probe returns the breaker to OPEN).
- A fast provider must **not** degrade; only a breach does.
- An over-quota request never reaches a provider.

## Mutation table

`_build/mutations.py`, run with
`python3 .claude/skills/graded-module/scripts/mutate.py inference-lab/ai-gateway inference-lab/ai-gateway/_build/mutations.py`:

| Bug | File | Caught by |
|---|---|---|
| rate limiter shared across tenants | `limiter.py` | step 1 |
| rate limiter never resets its window | `limiter.py` | step 2 |
| circuit breaker never opens | `circuit.py` | step 3 |
| half-open probe success does not close the circuit | `circuit.py` | step 4 |
| half-open admits every caller (one-probe guard deleted) | `circuit.py` | step 4 |
| a failing half-open probe does not return to OPEN | `circuit.py` | step 4 |
| fallback chain never advances past a failure | `gateway.py` | step 6 |
| SLO degradation triggers on an in-budget success | `gateway.py` | step 8 |
| static cache never used when every provider fails | `gateway.py` | step 7 |

## Limits

- **A simulation, not a proxy.** No HTTP, no streaming sockets. A real gateway wraps a
  streaming client and stamps the first content chunk; that is what `Provider.complete()`
  stands in for. Project #14 (chaos suite) and #4 (prefix-caching proxy) are where real
  transport lives.
- **The failure model is a short script**, not a distribution. It makes limit cases exact;
  it cannot tell you a tail latency.
- **The quota is per process.** Distributed rate limiting (Redis + Lua, or sticky routing)
  is discussed in `system-design/rate_limiter.py`, not implemented here.
- **No cost or token accounting**, so no per-tenant $/token view (that is project #12).
