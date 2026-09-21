# Runbook — the real commands

The exercises teach the *reasoning*. This file is the reference for the tools you'd
actually reach for. It is deliberately not code you run here — it is what the
simulated metrics correspond to in reality.

> Flags and command names drift between versions. Treat this as a map of *what to look
> for*, and check `--help` against the version you are running.

---

## LLM serving (vLLM / SGLang)

### Starting a server

```bash
vllm serve meta-llama/Meta-Llama-3-8B-Instruct \
  --gpu-memory-utilization 0.90 \   # fraction of the card for weights+KV
  --max-model-len 8192 \            # a CAPACITY decision, see capacity.py
  --enable-prefix-caching \         # the thing context-caching/ builds
  --max-num-seqs 256 \              # batch ceiling; KV usually binds first
  --port 8000
```

### The flags that matter, and what breaks

| Flag | Too low | Too high |
|---|---|---|
| `--gpu-memory-utilization` | Tiny KV cache → preemption, awful TTFT | OOM crash under a load spike |
| `--max-model-len` | Long requests rejected | Batch size collapses (16x from 2k→32k) |
| `--max-num-seqs` | Throughput left on the table | No effect; KV binds first |
| `--enable-prefix-caching` | — | Hit rate 0; every request re-prefills |

### Metrics to scrape

vLLM exposes Prometheus metrics at `/metrics`:

```
vllm:time_to_first_token_seconds        # TTFT histogram -> p99
vllm:time_per_output_token_seconds      # ITL -> p99
vllm:num_requests_running               # against your computed max concurrent
vllm:num_requests_waiting               # queue depth: the leading indicator
vllm:gpu_cache_usage_perc               # sustained >90% means preemption is near
vllm:num_preemptions_total              # non-zero = under-provisioned. Full stop.
vllm:prefix_cache_hit_rate              # 0 means caching is off or routing is wrong
```

### Diagnosis quick reference

| Symptom | Check first | Likely cause |
|---|---|---|
| TTFT huge, preemptions high, few running | `num_requests_running` vs computed max | KV budget too small |
| TTFT huge, preemptions high, normal running | arrival rate vs baseline | Overloaded — add replicas |
| TTFT elevated, cache hit rate 0 | `--enable-prefix-caching` set? | Caching disabled |
| Cache hit rate 40–60%, load even | Load balancer policy | Round-robin over shared prefixes |
| One replica's ITL far above peers | `nvidia-smi -q -d PERFORMANCE,ECC` | Throttling / bad host |
| OOM on startup | Weights + activations vs card | `gpu-memory-utilization` too high |

```bash
nvidia-smi --query-gpu=index,clocks_throttle_reasons.active,temperature.gpu,memory.used --format=csv
nvidia-smi -q -d ECC | grep -A2 "Aggregate"     # ECC errors -> replace the host
```

---

## Dynamo-style store (Cassandra / ScyllaDB)

### Health and topology

```bash
nodetool status              # UN = up/normal. DN = down. Check Owns% for skew.
nodetool info                # heap, uptime, cache hit rates
nodetool tpstats             # thread pools; Dropped mutations = you are losing writes
nodetool netstats            # streaming, and pending hinted handoff
nodetool compactionstats     # pending compactions rising = losing to write rate
nodetool tablestats <ks>     # per-table, incl. tombstones and partition sizes
```

### Consistency and quorums

```sql
CONSISTENCY QUORUM;    -- (N/2)+1: N=3 -> 2. Survives one replica loss.
CONSISTENCY ONE;       -- always-writeable, sloppiest reads
CONSISTENCY ALL;       -- zero failure tolerance. Almost never what you want.
```

`R + W > N` is the strict-quorum condition (`quorum.py` in `dynamo-paper/`). With
`N=3`, `QUORUM` reads and writes gives `2 + 2 > 3` — one node may be lost.

### Diagnosis quick reference

| Symptom | Check first | Likely cause |
|---|---|---|
| Reads failing, one node DN | `R + W` vs `N` | Quorum too strict for the fleet |
| Writes failing, all nodes UN | `nodetool tpstats` dropped mutations | Overload, or disk full |
| One node's latency far above peers | `nodetool status` Owns%, partition sizes | Hot partition |
| Sibling/conflict rate spiking | `nodetool gossipinfo` | Network partition |
| Hint queue growing | `nodetool netstats` | A peer is down; restore before the hint window expires |
| Pending compactions climbing | `nodetool compactionstats` | Write rate exceeds compaction throughput |

```bash
nodetool repair -pr <keyspace>       # anti-entropy; the merkle_sync.py mechanism
nodetool drain                       # flush + stop accepting writes, before a restart
nodetool decommission                # remove a node, streaming its data away
```

**Hot partitions are not fixed by adding nodes.** The hot key still hashes to one
node. Salt the key or split the partition.

---

## Kubernetes probes

The distinction that causes the most self-inflicted outages:

```yaml
startupProbe:                 # covers slow model loading
  httpGet: {path: /health, port: 8000}
  periodSeconds: 10
  failureThreshold: 30        # 300s of grace to load weights
readinessProbe:               # controls LOAD BALANCER membership
  httpGet: {path: /health, port: 8000}
  periodSeconds: 5
  failureThreshold: 2         # drain fast
livenessProbe:                # RESTARTS the container
  httpGet: {path: /health, port: 8000}
  periodSeconds: 20
  failureThreshold: 3
```

Without the startup probe, a 100s model load fails a liveness probe, the pod is
killed mid-load, and you get an infinite crash loop that looks exactly like a bad
image. `rollout.py` models this.

```bash
kubectl rollout status deploy/llm --timeout=10m
kubectl rollout undo deploy/llm              # the command you want to have rehearsed
kubectl describe pod <pod> | grep -A5 Events # OOMKilled? probe failures?
kubectl logs <pod> --previous                # the crash before this one
```

---

## The debugging method, independent of tool

1. **What changed?** Deploys, config, traffic, upstream dependencies. Most incidents
   are a change, and the fastest fix is usually reverting it.
2. **Symptom or cause?** "TTFT is 60s" is a symptom. "Only 1 sequence fits in KV" is a
   cause. Keep asking why until you reach something you can act on.
3. **Fleet-wide or one replica?** Compare the *spread* across replicas, not the
   average. An average hides a single bad host completely.
4. **Read the config alongside the metrics.** `node_down` and `quorum_too_strict` have
   identical topology; only `R` and `W` separate them.
5. **Check the confusable pair.** Every runbook reduces to a few "these look alike"
   cases. Know your separator before the incident.
6. **Mitigate, then diagnose.** Roll back or shed load first. Root-cause afterwards,
   with the pressure off.
