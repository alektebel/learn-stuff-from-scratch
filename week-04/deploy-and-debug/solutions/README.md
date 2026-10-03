# Deploy & Debug — Solutions

Complete implementations of every template in the parent directory. Pure Python 3
standard library.

```bash
python3 deployment.py     # PROVIDED — the fleets and their fault signatures
python3 capacity.py       # sizing math
python3 metrics.py        # percentiles, queueing, SLOs, burn rate
python3 diagnose.py       # 11 faults diagnosed from metrics alone
python3 rollout.py        # probes, canaries, staged rollout, auto-rollback
```

## `deployment.py` — provided, not an exercise

Two simulated fleets. Faults produce metric signatures that are *computed from a model
of the system*, not hardcoded — so each signature is a consequence, and the confusable
pairs are genuinely confusable.

Serving fault signatures:

```
fault               ttft_p99  itl_p99    hit  preempt  maxseq itlspread    err
healthy                  233     11.4    90%     0.00      10      1.01     0%
undersized_kv          58915     15.9    57%    42.63       1      1.01    18%
prefix_cache_off         351     11.5     0%     0.00      10      1.02     0%
bad_routing              240     11.5    55%     0.00      10      1.01     0%
slow_replica           56229     95.0    90%     0.00      10      2.95     4%
overloaded             57496     15.5    90%    58.94      10      1.05    18%
```

Note `undersized_kv` and `overloaded`: both preempt, both time out at 18%. The only
separator is `maxseq` — 1 vs 10.

For the store, `node_down` and `quorum_too_strict` have **identical** node counts (5/6)
and **identical** hint queues (420). Only R and W differ (2/2 vs 3/3).

## `capacity.py`

```
model              B/token  KiB/token     32k ctx
Llama-3-8B         131,072        128       4.0 GiB
Llama-3-70B        327,680        320      10.0 GiB

Llama-3-8B on A100-80GB:
 gpu_mem_util    KV GiB   @2k ctx    @8k   @32k
         0.90      54.0       216     54     13
```

And the headroom table, which is the point of `replicas_needed`:

```
  headroom  replicas  utilisation  queue factor
       0.7         5         62%          1.6x
       1.0         4         77%          3.3x
```

The queue factor is the multiplier on waiting time. Sizing to 100% is how a fleet that
"has capacity" misses its SLO.

## `metrics.py`

```
mean 158ms, p50 122ms, p99 1217ms  ->  p99 is 7.7x the mean
only 11.1% of requests are above the mean

utilisation   wait (100ms service)
        50%                 100 ms
        90%                 900 ms
        99%                9900 ms
```

`SLO("chat TTFT", 500ms, 0.99)` → 432 minutes of budget per 30 days. Burn rate 14.4x
exhausts a 30-day budget in ~2 days, which is the conventional page threshold.

## `diagnose.py`

6/6 serving faults and 5/5 store faults identified from metrics alone. Every `Diagnosis`
carries evidence and an action — a diagnosis nobody else can check is not much use at
3am.

Rule ordering matters: `SLOW_REPLICA` is checked **first**, because one bad host drags
every fleet average and would make the later fleet-wide rules misfire.

## `rollout.py`

```
startup    period  10s  threshold  16  -> tolerates  160s   (covers a 100s model load)
readiness  period   5s  threshold   2  -> tolerates   10s   (drain fast)
liveness   period  20s  threshold   3  -> tolerates   60s

scenario              p99 ratio   err delta    verdict
identical build            1.00     +0.000%    promote
20% slower p99             1.27     +0.000%   rollback
new error path             1.00     +0.988%   rollback
canary too small           3.08     -0.100%       hold   <- 3x slower, still 'hold'
```

Staged rollout against a build that only fails under real load:

```
     1%  promote
     5%  promote
    25%  rollback   error rate up 1.86%
outcome: rolled_back at 25%
```

A single 1% canary would have passed and shipped it.

## Implementation notes

- **`kv_bytes_per_token` takes `num_kv_heads`.** With GQA the query-head count is often
  4x larger; using it sizes the fleet 4x too large. The checker tests for exactly this.
- **`HealthCheck.record` resets on success.** Probes must fail *consecutively* — without
  the reset, a flaky network eventually restarts every replica.
- **`canary_verdict` checks sample size first.** Otherwise a 3x-slower canary with 90
  requests returns a confident `rollback` that is really a coin flip.
- **`diagnose_serving` checks replica spread before anything fleet-wide.** A single slow
  host drags every average; check the spread first or every later rule misfires.
- **`diagnose_store` reads R and W, not just topology.** Two faults have identical node
  counts and hint queues and differ only in configuration.
- **`rollback_triggers` has three bands, not two.** Above 14.4x auto-revert; 6–14.4x page
  a human but do not revert automatically — an auto-revert there fights the human who is
  already mid-incident.
