# 8 — AI fallback & degradation gateway

## What it is

A proxy in front of model providers that keeps answering when the primary model is slow,
rate-limited, or down — by falling back through a chain of progressively cheaper or
weaker options, and by knowing when to stop rather than fall back forever.

## You have already built the reliability core

`system-design/circuit_breaker.py` in this repo is the breaker. `system-design/` also has
bulkheads, backpressure and the cache patterns. Do not rebuild them.

**What is new here is that the fallback targets are not equivalent.** A retry against a
replica returns the same answer. A fallback from a large model to a small one returns a
*different, worse* answer, and the caller usually cannot tell. That asymmetry is the whole
project, and it is why this is not just a circuit breaker with a list.

## What it actually demonstrates

That you protect the customer experience — correct as stated — and, more precisely, that
you understand **silent quality degradation is its own outage**. A gateway that keeps
returning 200s while quietly serving answers from a 7B local model has not preserved the
experience; it has hidden a failure from the only people who could react to it.

## The substrate

Real providers with real failure modes. The Anthropic and OpenAI APIs both return
overload and rate-limit responses under load, with `retry-after` headers you should
respect. **Ollama** gives you a genuinely local tier, on your own hardware, with latency
characteristics that are nothing like the hosted tier — which is the point.

Inject failure properly. `toxiproxy` between your gateway and the provider gets you
latency, bandwidth limits, timeouts and connection resets on demand. Do not simulate
failures with an `if random() < 0.1` — you will only ever produce the failures you thought
of.

## The decisions

**What counts as a failure.** A 5xx is obvious. A response that takes 45 seconds is a
failure for an interactive user and fine for a batch job. A response that arrives but is
empty, or refuses, or is truncated by `max_tokens`, is a failure your status-code check
will not see. Define it per route, and note that `gen_ai.response.finish_reasons` (see
project 5) is where the truncation case shows up.

**Timeout budget, not per-call timeouts.** With a 4-tier chain and a 30-second timeout
each, worst-case latency is two minutes and your caller gave up long ago. The budget is
set by the caller and decremented down the chain; a tier that cannot complete within the
remaining budget must be skipped, not attempted.

**Streaming ruins this.** Fallback after the first token has been sent to the client is
not possible without either buffering the whole response (losing streaming) or emitting a
visible restart. Decide: buffer the first N tokens before committing to a stream, or
accept that streamed requests get no fallback. Most implementations never decide and
therefore have a bug.

**Cache as a tier.** Serving a semantically similar cached answer is the last tier before
failure. It is also the tier most likely to be wrong, because "similar question" is not
"same answer" when the question contains an entity or a date. If you build this,
`context-caching/semantic_cache.py` in this repo is the semantic response cache already.

**Tell somebody.** The response should carry which tier served it — a header, a field in
your API, a span attribute. Otherwise your evaluation numbers silently mix tiers and you
will spend a week investigating a quality regression that was an incident.

## Where it breaks

The fallback path is never exercised, so it is broken when you need it. The local model's
weights were never pulled onto the new node; the secondary provider's key expired four
months ago; the prompt template uses a feature the fallback model does not support.

The fix is not a better gateway. It is deliberately routing a small fraction of traffic
to each tier continuously, so every tier is always warm and always monitored — and that
is the same machinery as project 11.

## Resources

- `system-design/circuit_breaker.py` and the rest of `system-design/` in this repo.
- `context-caching/semantic_cache.py` in this repo, for the cache tier.
- Nygard, *Release It!*, 2nd ed. — the stability patterns (circuit breaker, bulkhead, timeouts, fail fast) in their original framing, including why a timeout without a budget is not a timeout.
- Google SRE Book, ch. 22, *Addressing Cascading Failures* — <https://sre.google/sre-book/addressing-cascading-failures/>. Read it before adding retries anywhere, since retries are how a partial outage becomes a total one.
- Toxiproxy — <https://github.com/Shopify/toxiproxy>
- Ollama — <https://ollama.com/>
