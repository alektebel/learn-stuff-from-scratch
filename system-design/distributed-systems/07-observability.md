# Category 7: Observability

Track 26. You cannot operate what you cannot see: distributed tracing,
metrics, structured logs, and the pipeline that carries them — built from
scratch.

---

## Track 26: Distributed Tracing & Observability

### Problem
A request touches 12 services and is slow. Which hop? Whose retry? What was
the queue depth at that moment? Observability answers questions you didn't
know you'd need to ask, from the outside, without redeploying.

### The Three Signals, One Correlation Key
```
TRACE   the request's tree of spans across services      "where did 900ms go?"
METRICS aggregated numbers over time                     "is p99 up fleet-wide?"
LOGS    discrete structured events                       "what exactly happened?"

correlation: every log line and span carries trace_id — jump between signals
```

### Part 1 — Tracing (the core build)

**Data model**
```
trace_id (128-bit)                       one per request
 └─ span: {span_id, parent_span_id, name, start, duration,
           attributes{...}, status, events[...]}

trace = tree of spans:
  [ gateway ───────────────────────────── 900ms ]
    [ auth ── 40ms ]
    [ orders ────────────────── 820ms ]
      [ db.query ── 35ms ]
      [ payments ───────── 760ms ]        ← found it
        [ retry#1 ── 250ms timeout ]
        [ retry#2 ── 500ms ok ]
```

**Context propagation** (the actually-hard part)
- In-process: the current span lives in task-local/thread-local storage;
  every async hop (thread pool, callback, coroutine) must carry it —
  instrument executors once, centrally.
- Cross-process: inject headers on every RPC (W3C `traceparent`:
  `version-trace_id-parent_span_id-flags`), extract on the server side.
  Add this to your Track 4 RPC framework so **every** later track is traced
  for free.
- Through queues (Track 12): stash the context in message headers; the
  consumer span *links* to the producer span (async causality, not
  parent-child).

**Sampling** — tracing everything is unaffordable at scale:
- Head-based: decide at the root (e.g. 1%), propagate the decision in the
  flags bit — cheap, but drops the interesting rare failures.
- Tail-based: buffer spans briefly, keep traces that turned out slow or
  errored — expensive collector, catches what you care about. Build head
  first, add a tail-keep rule for `status=error`.

**Collection pipeline**
```
app ──(async, batched, bounded queue)──► local agent ──► collector ──► store
```
Instrumentation must never block or break the app: bounded buffers, drop-on
overflow (count the drops!), fire-and-forget export.

### Part 2 — Metrics

- Types: **counter** (monotonic; rate() at query time), **gauge** (current
  value), **histogram** (latency: bucketed counts → p50/p95/p99).
- **Percentiles don't average**: store histograms per instance, merge
  buckets, *then* compute percentiles. Never average p99s.
- Cardinality is the killer: `http_requests{path=...}` with raw URLs =
  millions of series. Bound label values (route templates, not URLs; no
  user ids in labels).
- Pull (scrape /metrics) vs push (statsd): build pull — it also gives you
  up/down monitoring for free.
- The four golden signals per service: latency, traffic, errors,
  saturation — plus USE (utilization/saturation/errors) per resource.

### Part 3 — Structured Logs

- JSON lines with a schema: `ts, level, service, trace_id, span_id, msg,
  fields{...}`. The `trace_id` is what turns logs from grep-fodder into a
  navigable system.
- Levels are a contract: ERROR = a human should look, WARN = degraded but
  handled, INFO = state changes, DEBUG = off in prod.
- Pipeline: stdout → shipper → the Track 12 broker → indexer (a small
  Track 23 index over recent logs!) → retention tiers (hot 7d, cold object
  store).
- Log once per failure at the outermost handler with full context — not at
  every layer (12 stack traces for one failure is noise, not signal).

### Part 4 — Alerting & SLOs

- **SLI**: measured indicator (fraction of requests < 200ms and non-5xx).
- **SLO**: target (99.9% over 30d) → **error budget** (0.1% ≈ 43 min/month).
- Alert on **burn rate**, not point-in-time: page when
  `error_rate > 14.4 × budget_rate` over 1h (would exhaust the month's
  budget in ~2 days) — multi-window burn alerts kill both flapping and
  slow-bleed misses.
- Page on symptoms (SLO burn), ticket on causes (disk 80%). Every page must
  be actionable; anything else trains humans to ignore pages.

### Failure Modes (of the observability system itself)
| Failure | Handling |
|---|---|
| Telemetry pipeline outage takes down the app | bounded queues, drop + count, never block request path |
| Metrics cardinality explosion | label allow-lists; per-service series budgets + limits at the collector |
| Trace context lost at an async hop | instrument executors/queues centrally; test: every span must have a root |
| Sampling hides the incident | tail-based keep on error/slow; logs remain unsampled |
| Observability store slow during incident (everyone querying) | it must be a separate failure domain from prod, always |
| Clock skew makes child spans start before parents | record durations locally; render by tree, not by absolute time |

### Milestones
1. Tracing SDK: spans, task-local context, `traceparent` inject/extract in
   the Track 4 RPC layer; render a trace tree as ASCII/HTML from exported spans.
2. Propagate through the Track 12 broker with span links.
3. Metrics library (counter/gauge/histogram) + /metrics endpoint + a tiny
   scraper that stores series and computes rate() and merged percentiles.
4. Structured logger with trace correlation; pipeline into a searchable index;
   demo the workflow: alert → dashboard → trace → logs, on an injected fault.
5. Head sampling + tail keep-on-error; SLO burn-rate alerts; run a chaos day
   against your Track 8/12 systems and debug it *only* through this tooling.

---

## What Carries Forward
Everything. Retrofit tracing and metrics into every earlier track — the
gossip convergence times (3), Raft election storms (6), cache hit ratios
(10), consumer lag (12), compaction debt (14), checkpoint durations (24) all
become dashboards. The final exam of this track is debugging the other 27
without print statements.
