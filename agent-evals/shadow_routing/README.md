# shadow_routing — mirror a slice of traffic and diff two models (BUILD: eval infrastructure)

Project **#2**. The safe way to try a new model on real traffic is to *shadow* it: answer
the request from the incumbent, send the same request to the candidate off to the side, and
compare. The incumbent must never notice.

Runs against the shared [simulated service](../simulated_service/). It produces one report
that keeps **cost and quality apart** — a candidate that is better *and* dearer is not the
same as one that is better and cheaper, and a single "score" would hide the trade.

Standard library only.

## What it is

- `ShadowConfig(primary, shadow, fraction, seed)` — which models, and what share of traffic
  to mirror.
- `is_sampled(request_id, fraction, seed)` — deterministic, order-independent membership: a
  stable hash of `seed:request_id` compared to `fraction`.
- `shadow_run(service, requests, config)` — the primary for **every** request, the shadow
  for the mirrored sample. Returns `(primary, shadow, mirrored_ids)`.
- `compare(service, requests, config) -> Comparison` — the mirrored subset diffed into
  `primary`/`shadow` `totals`, `delta_*` properties, and the `disagreements` (with `fixed`
  and `broke` counts); `Comparison.report()` renders the table.

## Why the primary is safe

The guarantee is structural, not a promise: the primary is served for all requests before
the shadow runs, and the service answers a request the same way whatever ran before it
(`simulated_service`), so the primary path is **byte-identical with or without shadowing**.
A slow shadow adds to the shadow's own latency column and to nothing else. Both are checked
in `check.py`.

```python
from simulated_service import SimulatedService
from shadow_routing import ShadowConfig, compare

svc = SimulatedService(seed=0)
traffic = svc.traffic(per_segment=60, segments=7)
print(compare(svc, traffic, ShadowConfig(fraction=0.1)).report())
```

```sh
python3 -m shadow_routing --per-segment 60 --segments 7 --fraction 0.1
python3 shadow_routing/check.py     # the runnable check
```

## Out of scope

- Actually routing traffic; this decides *whether* to, from a report.
- Guardrails on the shadow's own budget or a kill switch (reliability list #8).
- Real latency distributions; latency is a scalar per run, not a histogram.
