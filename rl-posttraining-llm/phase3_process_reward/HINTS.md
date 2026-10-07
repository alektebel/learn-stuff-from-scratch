# Phase 3 — Progressive Hints

---

## `decompose`

<details><summary>Level 1 — nudge</summary>

You need the *positions* where clauses start, then you slice between them. Use
`str.find` in a loop to get every occurrence of each keyword.

The trap that will cost you an hour if you miss it: do **not** return slices of
the lowercased string. `WHERE country='ES'` → `WHERE country='es'` matches zero
rows, so every execution downstream silently returns the wrong answer and your
MC labels become noise.
</details>

<details><summary>Level 2 — structure</summary>

```
orig = sql.strip().rstrip(";")
s    = orig.lower()              # for MATCHING only

points = []
for kw in CLAUSE_KEYWORDS:
    start = 0
    while (i := s.find(kw, start)) >= 0:
        points.append(i)
        start = i + 1

points = sorted(set(points))
if not points: return [orig] if orig else []
if points[0] != 0: points = [0] + points

# slice `orig` between consecutive points
```
</details>

<details><summary>Level 3 — code</summary>

```python
def decompose(sql):
    orig = sql.strip().rstrip(";")
    s = orig.lower()
    points = []
    for kw in CLAUSE_KEYWORDS:
        start = 0
        while True:
            i = s.find(kw, start)
            if i < 0:
                break
            points.append(i)
            start = i + 1
    points = sorted(set(points))
    if not points:
        return [orig] if orig else []
    if points[0] != 0:
        points = [0] + points
    chunks = []
    for a, b in zip(points, points[1:] + [len(s)]):
        chunk = orig[a:b].strip()      # slice the ORIGINAL
        if chunk:
            chunks.append(chunk)
    return chunks
```
</details>

---

## `step_features`

<details><summary>Level 1 — nudge</summary>

Build three identifier sets — the gold set, what the prefix already referenced,
and what this step adds — and the four features fall out of set arithmetic.

For feature 1, intersect with `SCHEMA_TABLES` **before** subtracting the gold
set. Counting all identifiers doesn't work: `id` is a column of every table, so
it shows up everywhere and washes the feature out.
</details>

<details><summary>Level 2 — structure</summary>

```
gold       = gold_tables | gold_columns          (lowercased)
prefix_ids = identifiers in " ".join(prefix)
step_ids   = identifiers in step
seen       = prefix_ids | step_ids

f0 coverage = |gold & seen| / |gold|
f1 spurious = |(seen & SCHEMA_TABLES) - gold_tables| / 3, capped at 1
f2 new_gold = 1.0 if (gold & step_ids) - prefix_ids else 0.0
f3 is_agg   = 1.0 if step mentions group by/order by/sum(/count(/avg( else 0.0
```
Lowercase everything before comparing.
</details>

<details><summary>Level 3 — code</summary>

```python
import re
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

def _idents(s):
    return {t.lower() for t in IDENT.findall(s)}

def step_features(prefix, step, task):
    gold = ({t.lower() for t in task.gold_tables}
            | {c.lower() for c in task.gold_columns})
    prefix_ids, step_ids = _idents(" ".join(prefix)), _idents(step)
    seen = prefix_ids | step_ids

    coverage = len(gold & seen) / len(gold) if gold else 1.0
    gold_tables = {t.lower() for t in task.gold_tables}
    seen_tables = seen & {t.lower() for t in SCHEMA_TABLES}
    spurious = min(len(seen_tables - gold_tables) / 3.0, 1.0)
    new_gold = 1.0 if (gold & step_ids) - prefix_ids else 0.0
    is_agg = 1.0 if any(k in step.lower() for k in
                        ("group by", "order by", "sum(", "count(", "avg(")) else 0.0
    return [coverage, spurious, new_gold, is_agg]
```
</details>

---

## `mc_label`

<details><summary>Level 1 — nudge</summary>

"Complete this prefix `k` times and see how often you land on a correct answer."
On CPU the roll-out policy is: pick a random candidate from the same task's pool
and borrow the clauses it has *after* the prefix's length.
</details>

<details><summary>Level 2 — structure</summary>

```
prefix_clauses = decompose(partial_sql)
hits = 0
repeat k times:
    cand = random candidate from CANDIDATES[task.qid]
    tail = decompose(extract_sql(cand))[len(prefix_clauses):]
    completed = " ".join(prefix_clauses + tail)
    hits += execution_accuracy(f"<sql>{completed}</sql>", task, env)
return hits / k
```
Note `execution_accuracy` expects a *completion* (it looks for `<sql>` tags), so
wrap the query. If the tail is empty you just re-execute the prefix — that's
correct behaviour for an already-complete query.
</details>

<details><summary>Level 3 — code</summary>

```python
def mc_label(partial_sql, task, env, k, rng):
    pool = CANDIDATES[task.qid]
    prefix_clauses = decompose(partial_sql)
    hits = 0.0
    for _ in range(k):
        cand = pool[rng.randrange(len(pool))]
        tail = decompose(extract_sql(cand))[len(prefix_clauses):]
        completed = " ".join(prefix_clauses + tail)
        hits += execution_accuracy(f"<sql>{completed}</sql>", task, env)
    return hits / k
```
</details>

---

## `PRM.score` / `fit_step`

<details><summary>Level 1 — nudge</summary>

`score` is a plain logistic. The only subtlety is that `math.exp(-z)` overflows
for very negative `z` — use the branch trick.

`fit_step` is three lines. For sigmoid + log-loss the gradient collapses to
`error = score - label`; no derivative of the sigmoid appears.
</details>

<details><summary>Level 3 — code</summary>

```python
def score(self, feats):
    z = self.b + sum(w * f for w, f in zip(self.w, feats))
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)              # z < 0, so exp(z) is safe
    return e / (1.0 + e)

def fit_step(self, feats, label, lr=0.1):
    err = self.score(feats) - label
    for i, f in enumerate(feats):
        self.w[i] -= lr * err * f
    self.b -= lr * err
```
</details>

---

## `train_prm` / `prm_trace_score` / `shaped_reward`

<details><summary>Level 2 — structure</summary>

```
train_prm:
  repeat `steps` times:
    task = random task; cand = random candidate for it
    clauses = decompose(extract_sql(cand))
    for i, step in enumerate(clauses):
        prefix = clauses[:i]
        feats  = step_features(prefix, step, task)
        label  = mc_label(" ".join(prefix + [step]), task, env, k=4, rng=rng)
        prm.fit_step(feats, label)

prm_trace_score: mean of prm.score(step_features(clauses[:i], step, task))
                 over the clauses; 0.0 if there are none

shaped_reward:   w_exec * execution_accuracy(...) + w_prm * prm_trace_score(...)
```
Keep `k` small (4) inside training — it's called once per step per clause and
the executor is the slow part.
</details>

---

## Debugging table

| Symptom | Likely cause |
|---------|--------------|
| Every `mc_label` is 0, including for the gold query | `decompose` lowercased the output and broke `'ES'` |
| `test_spurious_feature_discriminates` fails | you counted all identifiers instead of tables only |
| `score` returns `nan` | single-branch sigmoid overflowing on large `-z` |
| Score moves *away* from the label | sign flipped — logistic regression **descends**, so `-=` here (unlike the policy update in Phase 0, which ascends) |
| `train_prm` is very slow | `k` too large, or `steps` too high — 150–400 is plenty |
| PRM weights all ≈ 0 | labels are nearly constant; check `mc_label` varies across prefixes |
