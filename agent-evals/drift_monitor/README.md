# drift_monitor — find a quality regression in a trace (BUILD: eval infrastructure)

Project **#9**. A deployed model does not fail loudly; it decays while the average success
rate still looks "fine". This reads a trace and, per time segment, compares the **realised**
success rate to the **predicted** one, alerting only when the shortfall is large and
unlikely to be sampling noise.

Runs against the shared [simulated service](../simulated_service/). Standard library only.

## What it is

- `MonitorConfig(baseline=(lo, hi), min_drop, min_n, z)` — which segments are known-good,
  the smallest gap worth reporting, the smallest segment to judge, and the z threshold.
- `monitor(rows, config)` — overall alerts, one per segment after the baseline.
- `monitor_by(rows, config, key="tenant")` — the same, inside each group (localisation).
- `all_alerts(rows, config)` — overall first, then per group; `render(alerts)` prints them.
- `Alert(segment, group, observed, expected, drop, n, z)`.

The test is a one-sided z on `expected − observed`, with the variance taken from the
per-request predicted probabilities, so a segment is only judged once it is large enough.

## Why a traffic shift is not an alert

Every trace row carries a `quality`: the pass rate the model predicts for that request,
computed **before** any drift (see `simulated_service`). Realised `success` is drawn from the
drift-adjusted rate. So the gap tells the two cases apart without a hand-tuned model:

- a **harder mix** (more difficult requests, a seasonal category shift) lowers `quality` too,
  so `expected − observed` stays near zero — no alert;
- a **regression** leaves `quality` where it was and pulls `success` down — a gap, and an
  alert.

A monitor that chased the raw success rate would fire on every seasonal change; that is the
limit case #9 exists to teach.

```sh
python3 -m drift_monitor --per-segment 120 --segments 7 --drift 4:3.0:acme
# segment 5: success 0.533 vs predicted 0.713 — drop +0.180 (n=120, z=4.5)
# segment 4 [acme]: success 0.150 vs predicted 0.726 — drop +0.576 (n=40, z=8.3)
python3 drift_monitor/check.py     # the runnable check
```

## Out of scope

- Faithfulness or hallucination checks (reliability list #5); this only measures the
  predicted-vs-realised pass rate.
- Paging, deduplication or severity; it emits alerts, it does not route them.
- Re-running offline evals; it trusts the `quality` the trace logged.
