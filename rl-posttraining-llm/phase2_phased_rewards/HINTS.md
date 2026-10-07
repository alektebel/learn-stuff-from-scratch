# Phase 2 — Progressive Hints

---

## `curriculum_weights`

<details><summary>Level 1 — nudge</summary>

Two scalars drive all five weights: one that falls from 1 to 0 (multiplying the
four shaping components) and one that rises (the `exec` weight). Write those two
first, then scale.

Check your endpoints before anything else: at `progress = 1.0` the shaping
weights must be exactly `0.0`, not merely small.
</details>

<details><summary>Level 2 — structure</summary>

```
shaping = max(0.0, 1.0 - progress)     # 1.0 -> 0.0
exec_w  = 0.5 + 1.5 * progress          # 0.5 -> 2.0

format: 0.3 * shaping
syntax: 0.4 * shaping
schema: 0.6 * shaping
ngram:  0.3 * shaping
exec:   exec_w
```
The per-component constants (0.3/0.4/0.6/0.3) are taste. The tests check the
*shape* — monotone down, monotone up, exec dominant at the end.
</details>

<details><summary>Level 3 — code</summary>

```python
def curriculum_weights(progress):
    shaping = max(0.0, 1.0 - progress)
    exec_w = 0.5 + 1.5 * progress
    return {
        "format": 0.3 * shaping,
        "syntax": 0.4 * shaping,
        "schema": 0.6 * shaping,
        "ngram":  0.3 * shaping,
        "exec":   exec_w,
    }
```
</details>

---

## `greedy_exec_acc`

<details><summary>Level 1 — nudge</summary>

"Greedy" = don't sample, take the most likely action. `max(range(n), key=...)`
gives you an argmax. Score it with `execution_accuracy` — **not** `combine`,
because this is your metric and it must not depend on training weights.
</details>

<details><summary>Level 2 — structure</summary>

```
hits = 0
for p, qid in enumerate(qids):
    probs = policy.probs(p)
    best  = argmax(probs)
    hits += execution_accuracy(CANDIDATES[qid][best], task_by_qid(qid), env)
return hits / len(qids)
```
</details>

<details><summary>Level 3 — code</summary>

```python
def greedy_exec_acc(env, qids, policy):
    hits = 0.0
    for p, qid in enumerate(qids):
        probs = policy.probs(p)
        best = max(range(len(probs)), key=lambda a: probs[a])
        hits += execution_accuracy(CANDIDATES[qid][best], task_by_qid(qid), env)
    return hits / len(qids)
```
</details>

---

## `train`

<details><summary>Level 1 — nudge</summary>

Structurally identical to Phase 1. The one new thing: `weights` changes every
step, so `reward_of` has to be rebuilt every step (it closes over `weights`).

Careful with Python's late-binding closures — if you build the lambda once
outside the loop and mutate a shared `weights` dict, you'll get confusing
results. Simplest fix: create a fresh dict and a fresh lambda each step.
</details>

<details><summary>Level 2 — structure</summary>

```
for step in range(steps):
    progress = step / max(steps - 1, 1)
    if weights_override is not None:
        weights = weights_override
    elif use_curriculum:
        weights = curriculum_weights(progress)
    else:
        weights = PHASED_STATIC

    reward_of = lambda p, a, w=weights: combine(
        CANDIDATES[qids[p]][a], task_by_qid(qids[p]), env, w)[0]

    mean_r = grpo_step(policy, reward_of, None, list(range(len(qids))),
                       group_size=8, rng=rng)
    if verbose and step % 40 == 0:
        print(step, round(mean_r, 3), greedy_exec_acc(env, qids, policy))
```
Note `w=weights` as a default argument — that's the idiomatic guard against
late binding.
</details>

<details><summary>Level 3 — code</summary>

```python
for step in range(steps):
    progress = step / max(steps - 1, 1)
    if weights_override is not None:
        weights = weights_override
    elif use_curriculum:
        weights = curriculum_weights(progress)
    else:
        weights = PHASED_STATIC

    def reward_of(p, a, w=weights):
        qid = qids[p]
        return combine(CANDIDATES[qid][a], task_by_qid(qid), env, w)[0]

    mean_r = grpo_step(policy, reward_of, None, list(range(len(qids))),
                       group_size=8, rng=rng)

    if verbose and (step % 40 == 0 or step == steps - 1):
        acc = greedy_exec_acc(env, qids, policy)
        print(f"{step:>4}  {mean_r:>10.3f}  {acc:>13.2f}")
```
</details>

---

## Debugging table

| Symptom | Likely cause |
|---------|--------------|
| All steps use the same weights | you built `reward_of` once outside the loop (late binding — use `w=weights` as a default arg) |
| `greedy_exec_acc` changes when you change training weights | you used `combine` instead of `execution_accuracy` |
| Shaping weights aren't exactly 0 at the end | you used `1.0 - progress` without `max(0.0, ...)`, or `progress` never reaches 1.0 — check `step / (steps - 1)` |
| `q5` still stuck near 0.28 | your weights dict only has `exec` — the shaping components aren't reaching `combine` |
| Accuracy is high but reward looks low | totally fine: reward scale is arbitrary, only *relative* ordering within a group matters to GRPO |
