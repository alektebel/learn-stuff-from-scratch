# Phase 6 — Progressive Hints

---

## `cites_previous_result`

<details><summary>Level 1 — nudge</summary>

Walk every cell of every row in the previous result, turn it into a string, and
check whether it appears in the lowercased reasoning.

The one wrinkle is floats: `str(160.0)` is `"160.0"`, but a human (or a model)
writes "160". Generate both spellings when the float is a whole number.
</details>

<details><summary>Level 3 — code</summary>

```python
def cites_previous_result(reasoning, previous_result):
    if not previous_result:
        return False
    low = reasoning.lower()
    for row in previous_result:
        for cell in row:
            if cell is None:
                continue
            if isinstance(cell, float) and cell.is_integer():
                variants = [str(cell), str(int(cell))]   # "160.0" and "160"
            else:
                variants = [str(cell)]
            if any(v.lower() in low for v in variants if v):
                return True
    return False
```
</details>

---

## `process_reward`

<details><summary>Level 2 — structure</summary>

```
if no steps: return 0.0
for i, step in enumerate(steps):
    ok       = 1.0 if step["ok"] else 0.0
    grounded = 1.0 if i == 0 else cites_previous_result(step["reasoning"],
                                                        steps[i-1]["result"])
    novel    = 0.0 if step["query"] seen in steps[:i] else 1.0
    total += (ok + grounded + novel) / 3
return total / len(steps)
```
Normalize queries (strip + lowercase) before the redundancy check, or trivial
whitespace differences read as "new".
</details>

<details><summary>Level 3 — code</summary>

```python
def process_reward(episode):
    if not episode.steps:
        return 0.0
    total = 0.0
    for i, step in enumerate(episode.steps):
        ok = 1.0 if step["ok"] else 0.0
        if i == 0:
            grounded = 1.0
        else:
            grounded = 1.0 if cites_previous_result(
                step.get("reasoning", ""), episode.steps[i - 1]["result"]) else 0.0
        earlier = {s["query"].strip().lower() for s in episode.steps[:i]}
        novel = 0.0 if step["query"].strip().lower() in earlier else 1.0
        total += (ok + grounded + novel) / 3.0
    return total / len(episode.steps)
```
</details>

---

## `make_verifier`

<details><summary>Level 1 — nudge</summary>

Three jobs: unwrap, compare by type, never raise. Unwrapping is recursive —
`[('furniture',)]` is a list holding a tuple holding a string.
</details>

<details><summary>Level 3 — code</summary>

```python
def make_verifier(gold_answer):
    def _flatten(x):
        while isinstance(x, (list, tuple)) and len(x) == 1:
            x = x[0]
        return x

    def verify(answer):
        try:
            a, g = _flatten(answer), _flatten(gold_answer)
            if isinstance(g, (int, float)) and not isinstance(g, bool):
                return 1.0 if abs(float(a) - float(g)) <= 1e-6 else 0.0
            return 1.0 if str(a).strip().lower() == str(g).strip().lower() else 0.0
        except Exception:
            return 0.0
    return verify
```
The bare `except` is deliberate here: `float(None)`, `float("abc")` and odd
objects must all read as "wrong answer", not as a crash in your training loop.
</details>

---

## `generate_candidate_questions`

<details><summary>Level 1 — nudge</summary>

Sample a template and a table, build the SQL, run it, keep it if it produced a
real answer. Two things to guard:
- templates needing a numeric column can't use `customers` — it has none, so
  skip that combination instead of generating SQL you know will fail;
- loop until you have `n` *valid* tasks, with a guard counter so a bad template
  can't spin forever.
</details>

<details><summary>Level 3 — code</summary>

```python
def generate_candidate_questions(env, n, rng):
    numeric = {"products": ["price"], "orders": ["quantity"], "customers": []}
    out, guard = [], 0
    while len(out) < n and guard < n * 50:
        guard += 1
        q_tpl, sql_tpl = QUESTION_TEMPLATES[rng.randrange(len(QUESTION_TEMPLATES))]
        table = SCHEMA_TABLES[rng.randrange(len(SCHEMA_TABLES))]
        if "{col}" in sql_tpl:
            cols = numeric.get(table, [])
            if not cols:
                continue                      # no numeric column here
            col = cols[rng.randrange(len(cols))]
            question, sql = q_tpl.format(table=table, col=col), sql_tpl.format(table=table, col=col)
        else:
            question, sql = q_tpl.format(table=table), sql_tpl.format(table=table)

        ok, res = env.execute(sql)
        if not ok or not res or res[0][0] is None:
            continue                          # the executor rejected it
        out.append(AnalyticTask(f"gen{len(out)}", question, res[0][0], sql))
    return out
```
</details>

---

## `self_improve_round`

<details><summary>Level 3 — code</summary>

```python
def self_improve_round(env, solver, rng, n_candidates=12):
    tasks = generate_candidate_questions(env, n_candidates, rng)
    kept, failed = [], []
    for task in tasks:
        verify = make_verifier(task.gold_answer)
        (kept if verify(solver(task)) == 1.0 else failed).append(task)
    total = len(tasks)
    return {"generated": total, "kept": kept, "failed": failed,
            "accuracy": (len(kept) / total) if total else 0.0}
```
`failed` is the half that matters — those are next round's curriculum.
</details>

---

## Debugging table

| Symptom | Likely cause |
|---------|--------------|
| Grounded and hallucinated episodes tie | your "ungrounded" test text accidentally mentions a real value from the result |
| `ORDER BY` seems to do nothing | `SQLEnv.execute` **sorts result rows** for order-insensitive comparison — rank in Python instead |
| Verifier fails on correct answers | you compared `[('furniture',)]` to `'furniture'` without unwrapping |
| Verifier raises on a `None` answer | missing the `try/except` |
| Generation hangs | no guard counter, and a template/table combination that can never succeed |
| Generated tasks have `None` answers | you didn't discard rows where `res[0][0] is None` (e.g. `AVG` over no rows) |
| `accuracy` is 1.0 for a broken solver | the verifier is returning 1.0 for mismatches — check the string branch |
