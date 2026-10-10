# ci_gate — a regression gate that blocks on signal, not on noise (BUILD: eval infrastructure)

Project **#4**. Run evaluations on every change and block the ones that break something —
without blocking on noise. That contrast is the whole design, and it comes from the
[correction to the original brief](../README.md): a success-rate threshold as small as 2 %
is below what 20-70 tasks can detect, so gating on success blocks pull requests at random.

Standard library only.

## What it blocks, and what it only warns about

The gate splits what it sees into low-variance signal and high-variance noise:

**Blocks** (exit code 1):

- a **deterministic regression** — the same `(task, seed)` that passed now fails;
- a **cost** median that regresses past `max_cost_regression`;
- a **latency** median that regresses past `max_latency_regression`.

**Warns** (exit code 0):

- the **success rate**, always with a Newcombe interval on the difference, so the reader
  sees whether the drop clears the noise or is "within noise, not a block".

## What it is

- `GateConfig(max_cost_regression, max_latency_regression, cost_key, latency_key)`.
- `evaluate(baseline, candidate, config) -> Verdict` — pairs records by `(task_id, seed)`,
  classifies, and summarises; `Verdict.render()` prints the block/warn lines and metrics.
- `newcombe(b_wins, b_n, c_wins, c_n)` / `wilson(...)` — the intervals; `median(...)`.
- `read_jsonl(path)` — read run records; `main` is the CLI.

Records are the harness-lab run shape: `task_id`, `seed`, `success`, `cost_eur`,
`wall_time_s`.

```sh
python3 -m ci_gate --baseline results/base.jsonl --candidate results/pr.jsonl
# ci gate: BLOCKED
#   block: 1 deterministic regression(s): t14-propagate-field#0
#   warn:  success 0.950 -> 0.933 (-0.017); within noise, not a block
python3 ci_gate/check.py     # the runnable check
```

## Out of scope

- Deciding the thresholds; they are `GateConfig` inputs, not magic.
- Flakiness detection or quarantine; a pass→fail flip is reported, not retried.
- The success-rate *value* as a gate; deliberately demoted to a warning with its interval.
