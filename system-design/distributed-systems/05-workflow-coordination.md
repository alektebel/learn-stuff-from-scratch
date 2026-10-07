# Category 5: Workflow Coordination

Tracks 18–21. Making multi-step, multi-service work happen exactly once, in
order, and reversibly: transactions, schedulers, DAG pipelines, and the
special case everyone underestimates — schema migrations.

---

## Track 18: Distributed Transactions

### Problem
One logical operation must update **multiple shards/services** (debit account
on shard A, credit on shard B) such that either all updates happen or none do.

### Design 1 — Two-Phase Commit (2PC)
```
coordinator                participants (A, B)
    │── PREPARE ──────────────►│  write undo/redo to WAL, lock rows,
    │◄───── vote yes/no ───────│  promise: "I can commit if asked"
    │   (all yes → log COMMIT decision — the point of no return)
    │── COMMIT ───────────────►│  apply, release locks, ack
```
- Participants that voted yes are **in doubt** until the decision arrives:
  they hold locks and cannot unilaterally abort.
- **The blocking flaw**: coordinator crashes after PREPARE, before broadcasting
  the decision → participants stall, holding locks. Fix: make the
  coordinator's decision log a replicated log (Track 7) — this is exactly
  what Spanner does (Paxos-replicated 2PC coordinators).
- Recovery matrix: coordinator recovers → replays decision; participant
  recovers in-doubt → asks coordinator; both use the WAL from Track 13.

### Design 2 — Sagas (what services actually use)
Break the transaction into local steps, each with a **compensating action**:
```
T1: reserve inventory   →  C1: release inventory
T2: charge card         →  C2: refund
T3: create shipment     →  C3: cancel shipment
failure at T3 ⇒ run C2, C1 (reverse order)
```
- No global locks, no in-doubt state — but **no isolation**: intermediate
  states are visible ("reserved" inventory others can see). Model states
  explicitly (`PENDING`, `CONFIRMED`, `COMPENSATED`) instead of pretending
  atomicity.
- Orchestration (a saga coordinator state machine, persisted per saga) vs
  choreography (services react to each other's events). Build orchestration —
  it's debuggable.
- Compensations must be idempotent and must *always* eventually succeed
  (retry forever + alert) — there is no "abort the abort".

### The Transactional Outbox (the workhorse pattern)
"Update my DB **and** publish an event" atomically, without 2PC:
```
BEGIN;
  UPDATE orders SET status='paid';
  INSERT INTO outbox(event) VALUES ('order_paid');   -- same local txn
COMMIT;
-- relay process reads outbox → publishes to the broker (Track 12) → marks sent
```
At-least-once publication + consumer idempotency = effectively-once, using
only local transactions.

### Failure Modes
| Failure | Handling |
|---|---|
| Coordinator crash (2PC) | replicated decision log; participants query on recovery |
| Participant crash in doubt | WAL replay → re-ask coordinator |
| Saga step succeeds but response lost | idempotency keys per step; retry safely |
| Compensation fails | retry with backoff forever + human alert; design comps to be un-failable (e.g. append a reversal, not delete) |
| Outbox relay crash | at-least-once redelivery; consumers dedupe |

### Milestones
1. 2PC over two Track 8 KV shards with WAL-backed participants; kill each
   party at each protocol step; verify no mixed outcomes.
2. Replicate the coordinator decision; re-run the kill matrix — no blocking.
3. Saga orchestrator with persisted state machine + compensations.
4. Transactional outbox with a relay into your Track 12 broker; end-to-end
   effectively-once test under crashes.

---

## Track 19: Job Scheduler

### Problem
Run jobs at scheduled times (cron) or on demand, across a worker fleet, such
that each job runs **effectively once** despite scheduler crashes, worker
crashes, and clock skew.

### Architecture
```
   cron defs / enqueue API
          │
   ┌──────▼───────┐   lease/ack    ┌─────────┐
   │  scheduler    │◄──────────────│ workers │  poll or push
   │  (replicated) │──dispatch────►│  pool   │
   └──────┬───────┘                └─────────┘
          │ state: job table (id, state, run_at, attempts, lease_expiry, owner)
          ▼
   durable store (Track 8 KV or SQL)
```

### Core Mechanisms
- **Single active scheduler** via leader election (Track 6) — or skip
  election entirely: make dispatch a **CAS on the job row**
  (`PENDING → LEASED if lease_expiry < now`), so N schedulers race safely.
- **Leases, not locks**: a worker claims a job with a lease
  (`owner=w1, lease_expiry=now+30s`) and must heartbeat to extend. Dead
  worker → lease expires → job re-dispatched. Lease + fencing token
  (monotonic per-job counter) prevents a paused-then-resumed worker from
  double-writing results: downstream rejects stale tokens.
- **Effectively-once**: dispatch is at-least-once by design; job side effects
  carry an idempotency key = `(job_id, scheduled_time)`.
- **Cron semantics**: compute `next_run` from the cron expression; on
  scheduler downtime, decide **catch-up policy** per job: run all missed
  ticks, run once, or skip (most jobs want "run once if missed").
- **Priorities & fairness**: per-tenant queues with weighted dequeue —
  one tenant's 1M jobs must not starve others.
- **Timers at scale**: a hierarchical timing wheel or a `run_at`-ordered
  index polled every second; avoid one goroutine/thread per timer.

### Retry Policy
`attempts++`, backoff `min(cap, base·2^n)+jitter`, retry cap → DLQ state
(`FAILED`) with the error attached. Distinguish *retryable* (network) from
*permanent* (bad input) failures at the job-API level.

### Failure Modes
| Failure | Handling |
|---|---|
| Worker dies mid-job | lease expiry → redispatch; idempotency key protects effects |
| Worker paused (GC/VM migrate), resumes after redispatch | fencing token rejects its late writes |
| Scheduler dies | leader failover or CAS-race design; jobs are in durable store |
| Clock skew between schedulers | use the store's time or logical leases; never compare local clocks across nodes |
| Thundering herd at minute boundary | jitter scheduled times; rate-limit dispatch |
| Missed ticks during downtime | explicit catch-up policy |

### Milestones
1. Durable job table + polling workers with lease + heartbeat.
2. Kill workers mid-job → redispatch with correct effectively-once behavior.
3. Fencing tokens; prove the paused-worker scenario is safe in a test.
4. Cron expressions + catch-up policies; downtime simulation.
5. Per-tenant fairness + priorities; measure dispatch latency p99 at 10k jobs/s.

---

## Track 20: DAG Pipelines

### Problem
Execute a graph of dependent tasks (build systems, data pipelines, Airflow):
run everything as parallel as dependencies allow, resume after failure
without redoing finished work.

### Model
```
        ┌──► B ──┐
   A ───┤        ├──► D ──► E        task states:
        └──► C ──┘                   PENDING → READY → RUNNING
                                       → SUCCEEDED | FAILED | UPSTREAM_FAILED
```
- Validate the DAG up front: cycle detection (topological sort must consume
  all nodes).
- **Scheduling loop**: a task becomes READY when all parents SUCCEEDED;
  READY tasks go to the Track 19 scheduler as jobs. Completion events
  decrement children's unmet-dependency counters — O(edges) total, no
  polling of the whole graph.
- **Run = DAG + parameters + logical date**, persisted. Task instances belong
  to a run; re-running a run reuses SUCCEEDED instances (**resume**) unless
  explicitly cleared (**backfill/rerun**).

### Semantics That Matter
- **Idempotent tasks keyed by (run_id, task_id)** — the scheduler guarantees
  at-least-once execution, tasks make it exactly-once in effect.
- **Failure propagation**: FAILED marks all descendants UPSTREAM_FAILED;
  independent branches keep running. Optional per-task `trigger_rule`
  (all_success / all_done / one_failed) for cleanup tasks.
- **Data passing**: small values inline in the task-instance row (XCom
  style); large artifacts to the object store / DFS (Track 16) with the
  *reference* in the row.
- **Concurrency limits**: per-run, per-task-pool caps; the scheduling loop
  respects pool tokens (a DAG shouldn't be able to seize the whole fleet).
- **Cross-run dependencies**: sensor tasks (wait for partition X to exist)
  with timeouts, so a stuck upstream doesn't hold workers — implement as
  deferred/async checks, not busy workers.

### Failure Modes
| Failure | Handling |
|---|---|
| Task crash | Track 19 lease/retry machinery, per-task retry policy |
| Scheduler crash mid-run | run + instance states are durable; loop resumes from state |
| Diamond dependency double-trigger | dependency counters, not event fan-in races |
| Skew: task reads yesterday's partial data | tasks declare data dependencies; sensors gate on completeness markers (_SUCCESS files) |
| Runaway DAG hogs cluster | pools + per-run parallelism caps |

### Milestones
1. DAG definition + cycle validation + topological execution, single process.
2. Persist run/instance state; kill the orchestrator mid-run → resume correctly.
3. Distribute execution via the Track 19 scheduler; parallel branches on
   separate workers.
4. Retries, trigger rules, UPSTREAM_FAILED propagation; test each rule.
5. Backfill: run 30 daily logical dates with bounded parallelism and
   per-pool limits.

---

## Track 21: Schema Migrations

### Problem
Change a live database's schema and migrate data **without downtime**, with
rollback available at every step, while old and new application code run
side by side during deploys.

### The Iron Rule
During any deploy there is a window where **old code and new code run
simultaneously** against the same database. Every migration must be
compatible with both — which forbids most single-step changes.

### Expand → Migrate → Contract
The universal pattern, e.g. renaming `fullname` → `display_name`:
```
1. EXPAND    add nullable display_name column          (old code ignores it)
2. DUAL-WRITE new code writes both columns             (old rows still stale)
3. BACKFILL  copy fullname → display_name in batches   (throttled, resumable)
4. READ-SWITCH new code reads display_name, falls back  (verify: dark-read compare)
5. CONTRACT  stop writing fullname; later drop column  (after all old code gone)
```
Each step is separately deployable and separately reversible. Rollback of
step N = redeploy step N-1's code; nothing destructive happens until the
final contract, days later.

### Backfill Engine (the part you build)
- Batched: `WHERE id > cursor ORDER BY id LIMIT 1000`, persist the cursor —
  resumable after crash (this is a Track 19 job).
- Throttled: sleep between batches; watch replica lag and abort/slow when it
  grows — backfills have taken down more databases than traffic has.
- Idempotent: `SET display_name = fullname WHERE display_name IS NULL` —
  safe to re-run, safe to race with dual-writes.
- Verified: a checker job samples rows and compares; cutover requires
  0 divergence over a window.

### Dangerous Operations Catalog
| Operation | Why it bites | Safe version |
|---|---|---|
| `ADD COLUMN ... NOT NULL` | table rewrite / lock | add nullable + backfill + add constraint `NOT VALID`, validate later |
| `CREATE INDEX` | blocks writes | `CREATE INDEX CONCURRENTLY` (or build via LSM-style side index) |
| `ALTER TYPE` / rename | breaks old code instantly | expand-contract with a new column |
| Long transaction during migration | lock queue pile-up behind it | `lock_timeout` + retry; migrations take locks briefly or not at all |
| Dropping a column still read by old code | 500s during deploy window | contract only after old code is provably gone |

### Migration Infrastructure
- Versioned, ordered migration files; applied set recorded in a
  `schema_migrations` table; apply is idempotent and **linearized** (one
  migrator at a time — a lease from Track 19).
- Every migration ships with a down-migration *or* an explicit
  `IRREVERSIBLE` marker that requires the expand-contract pattern instead.
- For sharded systems (Track 9): roll the migration shard by shard; the app
  must tolerate mixed schemas across shards → same old/new rule, per shard.

### Failure Modes
| Failure | Handling |
|---|---|
| Backfill crashes | cursor checkpoint → resume |
| Backfill floods replicas | lag-aware throttle |
| Old code writes after read-switch | dual-write stays on until contract |
| Divergent copies (write race during backfill) | idempotent backfill predicate + verifier job |
| Migration applied twice (two deployers) | migrations table + lease |

### Milestones
1. Migration runner: versioned files, state table, lease, up/down.
2. Full expand→contract rename on a live simulated workload (old+new writers
   running); zero errors, zero lost writes.
3. Backfill engine: resumable cursor, throttle hooked to a fake lag metric,
   verifier with sampled comparison.
4. Shard-by-shard rollout across a Track 9 sharded store with mixed-schema
   tolerance tests.

---

## What Carries Forward
- Outbox + broker (18 + 12) is the integration spine of every event-driven
  system you'll design.
- Leases + fencing tokens (19) reappear anywhere "exactly one actor" is
  needed — DFS primaries (16), migration runners (21), stream checkpoints (24).
- Expand→migrate→contract is the same shape as shard moves (9) and index
  builds (17): dual-write, backfill, verify, cut over.
