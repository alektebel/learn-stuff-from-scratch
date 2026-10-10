# simulated_service — the shared synthetic production double (BUILD: eval infrastructure)

Three projects need production traffic they do not have:

- **#2 Shadow routing comparator** mirrors a slice of traffic to a second model and diffs
  cost and quality.
- **#9 Production drift monitor** samples traffic over time and alerts when quality decays.
- **#10 Cost-quality Pareto dashboard** maps inference cost against task success.

Rather than stub each one, this is a single deterministic service all three run against.
It is *infrastructure*, not a learning core: the projects consume it and add the logic
worth learning. It teaches the **mechanics** — sampling traffic over time and tenants,
mirroring a request, watching a planted regression appear, trading cost for quality — and
**its numbers say nothing about any real system** (see [../README.md](../README.md)).

Standard library only, no numpy, no network, no model calls.

## What it is

- `traffic(n, tenants, categories, segments, per_segment)` — a synthetic request stream
  spread evenly over the time segments and round-robin over tenant and category, each
  request carrying a hidden `difficulty`.
- `serve(request, model)` — one request against a `ModelConfig`: a `success` sampled from a
  latent `quality`, plus `input_tokens`, `output_tokens`, `latency_ms` and `cost_eur`.
- `write_jsonl` / `read_jsonl` — the trace store the projects read, and `success_rate` /
  `totals` — the two aggregations they would otherwise rewrite.

Two properties the projects lean on, both from a per-`(seed, request id, model)` RNG:

- **Reproducible.** The same seed and traffic give byte-identical responses.
- **Neighbour-independent.** Serving a request twice, in any order, or after mirroring it
  to another model, yields the same answer — a shadow can never move the primary (#2).

`ModelConfig.strength` is the base logit; `quality = sigmoid(strength − 1.6·difficulty −
penalty)`. `Drift(after_segment, penalty, tenant, category)` scopes a logit reduction, so a
planted drop is real and a monitor has to find it from success alone: the drift rule is
**not** a field in the trace (`drift_schedule()` returns it for scoring only).

## The models

| model | strength | EUR / 1k in | EUR / 1k out | latency | trades |
|---|---|---|---|---|---|
| `small` | 1.7 | 0.00015 | 0.0006 | ~280 ms | cheap, weaker |
| `large` | 2.7 | 0.0025 | 0.0100 | ~820 ms | dearer, stronger |

The gap is what makes #10's frontier non-trivial and #2's report worth reading.

## Usage

```python
from simulated_service import Drift, SimulatedService, write_jsonl, totals

svc = SimulatedService(seed=0, drift=[Drift(after_segment=7, penalty=1.4, tenant="acme")])
traffic = svc.traffic(per_segment=60, segments=14)
write_jsonl(svc.run(traffic, "small"), "traces/small.jsonl")
print(totals(svc.run(traffic, "small")))
```

Or emit a trace from the shell:

```sh
python3 -m simulated_service --out traces/run.jsonl --seed 0 \
    --per-segment 60 --segments 14 --model small --drift 7:1.4:acme
python3 simulated_service/check.py     # the runnable check
```

## Out of scope

- Any real model, traffic or cost table; there is one cheap and one dear model and nothing
  pretends they are providers.
- Streaming, retries, concurrency or latency *distributions* — latency is a scalar per run.
- The monitor, the shadow comparator and the Pareto dashboard themselves; those are #9,
  #2 and #10, on top of these traces.
