# Phase 7 — Progressive Hints

---

## `make_reward_fn`

<details><summary>Level 1 — nudge</summary>

Four closures, all with the signature `(prompt_idx, action_idx) -> float`. Three
of them you've already written in earlier phases; only `phased_plus_graph` is new,
and it's just "shaping components, minus `exec`, plus the graph reward".

The one thing to get right: `graph_only` must call **nothing** but
`graph_reward`. No `combine`, no `execution_accuracy` — the test counts database
calls and fails if there are any.
</details>

<details><summary>Level 2 — structure</summary>

```
PHASED  = {"format":0.2,"syntax":0.3,"schema":0.5,"ngram":0.3,"exec":1.0}
SHAPING = {"format":0.2,"syntax":0.3,"schema":0.5,"ngram":0.3}   # note: no exec

exec_only         -> combine(cand, task, env, {"exec": 1.0})[0]
phased            -> combine(cand, task, env, PHASED)[0]
graph_only        -> graph_reward(cand, task.gold_sql)
phased_plus_graph -> combine(cand, task, env, SHAPING)[0] + 1.5 * graph_reward(...)
```
The `1.5` matters: the graph term has to outweigh the shaping sum, or you're
mostly optimizing surface form again (the Phase 2 reward-hacking lesson).
</details>

<details><summary>Level 3 — code</summary>

```python
def make_reward_fn(config, env, qids):
    PHASED = {"format": 0.2, "syntax": 0.3, "schema": 0.5, "ngram": 0.3, "exec": 1.0}
    SHAPING = {"format": 0.2, "syntax": 0.3, "schema": 0.5, "ngram": 0.3}

    if config == "exec_only":
        def reward_of(p, a):
            qid = qids[p]
            return combine(CANDIDATES[qid][a], task_by_qid(qid), env, {"exec": 1.0})[0]
    elif config == "phased":
        def reward_of(p, a):
            qid = qids[p]
            return combine(CANDIDATES[qid][a], task_by_qid(qid), env, PHASED)[0]
    elif config == "graph_only":
        gr = load_graph_reward()
        def reward_of(p, a):
            qid = qids[p]
            return gr(CANDIDATES[qid][a], task_by_qid(qid).gold_sql)
    elif config == "phased_plus_graph":
        gr = load_graph_reward()
        def reward_of(p, a):
            qid = qids[p]
            task = task_by_qid(qid)
            return (combine(CANDIDATES[qid][a], task, env, SHAPING)[0]
                    + 1.5 * gr(CANDIDATES[qid][a], task.gold_sql))
    else:
        raise ValueError(f"unknown config {config}")
    return reward_of
```
Call `load_graph_reward()` **once** per config, outside the closure — importing a
module on every reward evaluation is needlessly slow.
</details>

---

## `train_config` / `evaluate` / `run_ablation`

<details><summary>Level 2 — structure</summary>

`train_config` is the Phase 1 loop unchanged:
```
for _ in range(steps):
    grpo_step(policy, reward_of, None, list(range(len(qids))), group_size=8, rng=rng)
return policy, qids, env
```

`evaluate` is Phase 2's `greedy_exec_acc` plus one extra number:
```
hits = sum(execution_accuracy(argmax candidate) for each task) / n_tasks
q5p  = policy.probs(qids.index("q5"))[CORRECT_INDEX["q5"]]
return hits, q5p
```

`run_ablation` loops the configs, trains, evaluates, builds rows. Set
`executes_during_training = config in ("exec_only", "phased")`.
</details>

---

## Reading your own table

<details><summary>What should I actually conclude?</summary>

Three things, and one non-conclusion:

1. **Accuracy alone is useless here.** All four configs hit 1.00. If that were
   your only column you'd ship `exec_only` and never learn it is at chance on
   `q5`. Carry a diagnostic your headline metric structurally cannot capture.
2. **`exec_only`'s q5 number is the whole course in one cell.** ~0.28 — the
   reward could not see the difference, so the policy never learned it.
3. **Execution-free training is viable.** `graph_only` matches the best accuracy
   and fixes `q5` while never touching data during training. That's a real,
   defensible engineering claim for a regulated setting.

The non-conclusion: **this does not tell you graph reward beats phased rewards in
general.** Five tasks, four hand-written candidates, a tabular policy. You have
demonstrated that the mechanisms work and how they fail — not measured their
relative value. Say that plainly in the write-up; it is the difference between a
useful report and an overclaim.
</details>

---

## Debugging table

| Symptom | Likely cause |
|---------|--------------|
| `NotImplementedError` from `load_graph_reward` | Phase 4 isn't finished — the capstone depends on it |
| "graph_only executed SQL N times" | your `graph_only` closure calls `combine` or `execution_accuracy` |
| `graph_only` accuracy is low | `graph_reward` argument order — it takes `(completion, gold_sql)` |
| `phased_plus_graph` behaves like `phased` | you left `exec` in the shaping dict, or the graph weight is too small |
| `exec_only` q5 is high | you're not actually training with `{"exec": 1.0}` alone |
| Ablation is slow | it trains four configs; drop `steps` while iterating |
