# pareto — the cost-quality frontier per tenant (BUILD: eval infrastructure)

Project **#10**. A cheaper model that is only slightly worse is often the right call, but
"cheaper" and "worse" trade off per tenant. This turns run records into the **Pareto
frontier**: the configurations no other beats on *both* cost and quality. An expensive
config stays only while it buys quality; the moment a cheaper one matches it, it belongs off
the chart.

Reads the trace store of the [simulated service](../simulated_service/). Standard library
only.

## What it is

- `points(rows, by="model")` — one `Point(config, cost_eur, success, n, ci)` per config:
  mean cost per request, success rate, and a Wilson interval on the success.
- `dominates(a, b)` — `a` beats `b` iff it is no dearer and no worse and strictly better on
  at least one; `frontier(points)` keeps the non-dominated ones, cheapest first.
- `pareto(rows, by="model", group="tenant")` — the frontier overall or one per tenant.
- `render(result)` — the table; `wilson(successes, n)` — the interval.

The frontier is computed from the records, never eyeballed. The interval is printed because
at these sample sizes half a point of success is noise, and a frontier should say so rather
than crown a config on a rounding error.

## The rules the frontier encodes

- A config that is **dearer and worse** than another is dropped.
- A config that is **dearer and better** is kept — that is the whole trade-off.
- A config that is **cheaper and no worse** stays; a dearer one that matches it does not.
- Equal points both stay (neither dominates).

```sh
python3 -m pareto --per-segment 200 --segments 4
# frontier for acme:
#   small  cost 0.00021/req  success 0.693 [0.635, 0.745]  n=267
#   large  cost 0.00384/req  success 0.869 [0.823, 0.904]  n=267
python3 pareto/check.py     # the runnable check
```

## Out of scope

- The team's cost tolerance or an automatic choice of config; it maps the frontier, a human
  decides where on it to sit.
- Confidence-adjusted dominance (dropping a config only when its interval is clearly worse);
  dominance here is on point estimates, with the intervals shown for the reader.
- Latency or an SLO budget (reliability list #13); only cost and success.
