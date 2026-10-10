# Infrastructure as Code and Drift — Solutions

Complete versions of every template in the parent directory. Pure Python 3,
standard library only. Run them from inside this directory (they import each
other by name):

```bash
cd solutions
python3 spec.py      # parse a spec and a state; canonical equality; cycle detection
python3 planner.py   # a real plan: diff, order, idempotence, rename, cycle
```

## Expected output

`python3 spec.py`:

```
parsed 3 resources: ['subnet', 'vpc', 'web']
dependents:
  subnet  <- ['web']
  vpc     <- ['subnet']
  web     <- []
same config written in a different key order: True
cycle in a 3-node graph: a -> b -> c -> a
cycle in an acyclic graph: None
```

`python3 planner.py`:

```
plan for a spec with one create, one update and one delete:
  1. delete legacy
  2. update web (ami)
  3. create cache

idempotent when state == spec: True
stateful rename db -> db-prod: [('create', 'db-prod'), ('delete', 'db')]  create first: True
cycle: dependency cycle: a -> b -> a
```

## What the output means

- **`same config written in a different key order: True`** — the state writes
  `web`'s properties as `{"instance_type": ..., "ami": ...}` while the spec writes
  them as `{"ami": ..., "instance_type": ...}`. They compare equal because
  `canonical()` sorts keys. Without it, every resource would look like drift.
- **`delete legacy` before `update web` before `create cache`** — unrelated
  actions run in the fixed priority (deletes, then updates, then creates). The
  order among unrelated actions does not affect correctness; it is fixed so two
  runs of the planner produce the same plan.
- **`idempotent when state == spec: True`** — the empty plan is the acceptance
  test: a deployment tool whose state already matches must do nothing.
- **`[('create', 'db-prod'), ('delete', 'db')]`** — the database was renamed from
  `db` to `db-prod`. For a stateful resource the create is pinned before the
  delete, so the old database is not destroyed before the new one exists.
- **`cycle: dependency cycle: a -> b -> a`** — a cycle is reported by name. A
  recursive sort that followed it would never terminate; here `find_cycle` finds
  the loop first and `plan` raises `DependencyCycle`.

## Files

- `spec.py` — `Resource`, `SpecError` / `DependencyCycle`, `canonical`,
  `same_config`, `parse_resource`, `parse_document`, `dependents`, `find_cycle`.
- `planner.py` — `Action`, `compute_drift`, `rename_pairs`, `order_actions`,
  `plan`.
