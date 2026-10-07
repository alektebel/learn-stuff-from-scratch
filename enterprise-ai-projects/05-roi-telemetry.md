# 5 — ROI & usage telemetry dashboard

## What it is

Instrumentation plus a view that tells a customer what your AI product did for them last
week, in hours and in money.

## What it actually demonstrates

Be clear-eyed about this one: **the dashboard is the easy half**. React and a time-series
database are not what is being tested. What is being tested is whether you can define
"hours saved" in a way that survives someone who does not want to believe it.

The failure mode is specific and common: you measure `requests × assumed_minutes_saved`,
present it as a dollar figure, and the customer's finance function correctly identifies it
as an assumption dressed as a measurement. That destroys trust in every other number you
show them, including the true ones.

So the deliverable that matters here is not the dashboard. It is a written definition of
each metric, its assumptions, its confidence, and what would make it wrong — displayed
next to the number, not buried in a footnote.

## The substrate

**OpenTelemetry**, using the GenAI semantic conventions rather than attribute names you
invented. They are a real, adopted schema: a model call is a span with kind `CLIENT`,
named `{gen_ai.operation.name} {gen_ai.request.model}`, carrying `gen_ai.request.model`,
`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons`
and the rest.

Using the standard names is not pedantry. It means your telemetry composes with the
customer's existing observability stack, which is the difference between a dashboard they
look at once and one that ends up on a wall.

Storage: Prometheus for the metrics, ClickHouse or Postgres for the event-level data you
need to answer "which requests, exactly?" when they ask. They will ask.

## The decisions

**How you establish the counterfactual.** This is the whole project. Options, honestly
costed:

| Method | Cost |
|---|---|
| Assumed minutes per task | Free, and worthless as evidence. Acceptable only if labelled as an assumption with the assumed value visible and editable by the customer. |
| Timed baseline study before rollout | Genuine evidence. Costs you a study, the customer's time, and a delay to launch. |
| Holdout group | The strongest evidence available. Costs you a population of users deliberately not given the product, which someone will object to. |
| Task-level instrumentation (time from open to submit, with and without assistance) | Good, and cheap once the product is instrumented. Confounded by task difficulty selection: people use assistance on the hard ones. |

Whichever you pick, the number on the dashboard should carry its method. "142 hours
(assumed 6 min/task)" and "142 hours (holdout, ±18)" are different claims and should not
look the same.

**Cost attribution.** Token cost is easy and is not the cost. Include the retries, the
requests that failed after burning tokens, the embedding calls, the reranker, the
evaluation traffic and the shadow traffic from project 11. A cost figure that omits
retries is wrong in exactly the direction that flatters you.

**Aggregation and privacy.** Per-user productivity numbers are surveillance, and in some
jurisdictions works-council territory. Decide the minimum aggregation unit before you
build, because retrofitting it means deleting data you already collected.

## Where it breaks

Usage goes up and value goes down. Users discover the product is fun, or they retry
because answers are wrong, and every counter you built rises while the actual outcome
deteriorates. If your dashboard cannot show that, it is a sales tool rather than a
measurement.

Build one metric that can go the wrong way. If every number on the page only ever goes up
and to the right, nobody senior will believe any of them, and they will be right not to.

## Resources

- OpenTelemetry GenAI semantic conventions — <https://github.com/open-telemetry/semantic-conventions-genai> `[v]`; attribute registry <https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/> `[v]`
- OpenTelemetry specification — <https://opentelemetry.io/docs/specs/otel/>
- Kohavi, Tang, Xu, *Trustworthy Online Controlled Experiments*, CUP 2020. If you go the holdout route, this is the book; the chapters on metric design and on twyman's law are directly applicable.
- Forsgren, Humble, Kim, *Accelerate*. Not about AI, but the reference for constructing outcome metrics that a business accepts and that resist gaming.
- `deploy-and-debug/` in this repo — percentiles, error budgets and the arithmetic of aggregating latency. Reuse it rather than averaging averages.
