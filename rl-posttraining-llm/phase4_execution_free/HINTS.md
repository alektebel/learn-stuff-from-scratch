# Phase 4 — Progressive Hints

---

## `canonicalize`

<details><summary>Level 3 — code</summary>

```python
def canonicalize(sql):
    s = sql.strip().rstrip(";")
    return re.sub(r"\s+", " ", s)
```
</details>

---

## `to_graph` — tables

<details><summary>Level 1 — nudge</summary>

`TABLE_RE` matches what follows `FROM` and `JOIN` — but `FROM orders o` also
makes `o` a candidate on the next match. You know the real table names; use them
as a filter.
</details>

<details><summary>Level 3 — code</summary>

```python
tables = {t.lower() for t in TABLE_RE.findall(s)}
tables &= {t.lower() for t in SCHEMA_TABLES}
```
</details>

---

## `to_graph` — aggregates

<details><summary>Level 1 — nudge</summary>

`AGG_RE` returns `(function, argument)` pairs. The argument is where all the
noise lives: spaces and alias prefixes. Both must go, or
`SUM(p.price * o.quantity)` and `sum(price*quantity)` won't match.

Be careful **not** to use "take everything after the last dot" — on
`p.price*o.quantity` that leaves you with `quantity`, silently dropping half the
expression. (This exact bug survives most tests; the `aggregates normalize` test
exists to catch it.)
</details>

<details><summary>Level 3 — code</summary>

```python
aggs = set()
for fn, arg in AGG_RE.findall(s):
    arg_norm = re.sub(r"\s+", "", arg).lower()          # drop spaces
    arg_norm = re.sub(r"\b[a-z_][a-z0-9_]*\.", "", arg_norm)  # drop `p.` prefixes
    aggs.add(f"{fn.lower()}({arg_norm})")
```
The second regex removes *every* `identifier.` prefix wherever it appears in the
expression — which is what you want for a compound expression.
</details>

---

## `to_graph` — filters vs joins

<details><summary>Level 1 — nudge</summary>

Both come from the same `FILTER_RE` matches. The distinguishing question is what
sits on the right-hand side: a **literal** (`'ES'`, `5`) means filter; another
**qualified column** (`p.id`) means join.
</details>

<details><summary>Level 3 — code</summary>

```python
filters, joins = set(), set()
for col, op, val in FILTER_RE.findall(s):
    col_n = col.split(".")[-1].lower()
    val_n = re.sub(r"\s+", "", val)
    is_literal = val_n.startswith("'") or val_n.startswith('"')
    if is_literal or col_n not in {"id", "customer_id", "product_id"}:
        filters.add(f"{col_n}{op}{val_n.lower()}")
    if op == "=" and not is_literal and "." in col and "." in val:
        joins.add("|".join(sorted([col_n, val.split(".")[-1].lower()])))
```
Sorting the join pair makes `a=b` and `b=a` produce the same edge.
</details>

---

## `to_graph` — modifiers

<details><summary>Level 1 — nudge</summary>

Substring search over `MODIFIER_MARKERS` on the lowercased query. The only
subtlety: `"not in"` contains `"in"`, so a naive scan records both and `IN` /
`NOT IN` stop being distinguishable — which defeats the entire purpose.
</details>

<details><summary>Level 3 — code</summary>

```python
modifiers = set()
low = s.lower()
for marker in MODIFIER_MARKERS:
    idx = low.find(marker)
    while idx >= 0:
        preceded_by_not = low[max(0, idx - 4):idx].strip().endswith("not")
        if not (marker == "in" and preceded_by_not):
            modifiers.add(marker)
        idx = low.find(marker, idx + 1)
```
</details>

---

## `jaccard` / `weighted_jaccard` / `graph_reward`

<details><summary>Level 2 — structure</summary>

```
jaccard(a, b):
    if not a and not b: return 1.0        # both agree there's nothing here
    union = a | b
    return len(a & b) / len(union) if union else 1.0

weighted_jaccard(a, b, weights):
    total = sum(weights.values())
    return sum(w * jaccard(a[n], b[n]) for n, w in weights.items()) / total

graph_reward(completion, gold_sql, weights):
    return weighted_jaccard(to_graph(extract_sql(completion)),
                            to_graph(gold_sql), weights)
```
Dividing by `sum(weights)` is what keeps the result in `[0,1]` even if someone
passes weights that don't sum to 1.
</details>

---

## Debugging table

| Symptom | Likely cause |
|---------|--------------|
| `graph_reward(gold, gold) != 1.0` | a component is nondeterministic, or you compared a canonicalized graph to a raw one |
| Aggregates never match | you took `split(".")[-1]` on the whole expression instead of regex-stripping each prefix |
| `q3` correct and inverted queries tie | `modifiers` missing, or the `not in` guard isn't working |
| Tables include `o`, `p`, `c` | forgot to intersect with `SCHEMA_TABLES` |
| Every simple query scores low | `jaccard(set(), set())` returns 0 instead of 1.0 |
| The poisoned-executor test fails | something in your path calls `execution_accuracy` or `env.execute` |
| Scores are all 0.0 or 1.0 | you're comparing whole query strings, not component sets |
