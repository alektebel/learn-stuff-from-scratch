# Phase 1 — Progressive Hints

Open one level at a time.

---

## `reward_of_factory`

<details><summary>Level 1 — nudge</summary>

This is pure plumbing: two lookups and one function call. The only thing that
trips people up is that `combine()` doesn't return a number — check its return
type in `common/rewards.py`.
</details>

<details><summary>Level 2 — structure</summary>

```
qid        = qids[prompt]                # int -> task id
completion = CANDIDATES[qid][action]     # int -> completion string
task       = task_by_qid(qid)            # task id -> Task object
total, breakdown = combine(completion, task, env, weights)
return total
```
`weights` is `{"exec": 1.0}` in this phase — nothing else, or you'll accidentally
solve `q5` and fail the test that expects you not to.
</details>

<details><summary>Level 3 — code</summary>

```python
def reward_of(prompt: int, action: int) -> float:
    qid = qids[prompt]
    completion = CANDIDATES[qid][action]
    total, _ = combine(completion, task_by_qid(qid), env, weights)
    return total
```
</details>

---

## `train`

<details><summary>Level 1 — nudge</summary>

`grpo_step` in `common/grpo.py` already does everything you wrote by hand in
Phase 0 — sampling the group, computing advantages, applying the update. You
just call it once per step and print occasionally. Read its signature.
</details>

<details><summary>Level 2 — structure</summary>

```
for step in range(steps):
    mean_r = grpo_step(policy, reward_of, None, list(range(len(qids))),
                       group_size=8, rng=rng)
    if verbose and (step % 40 == 0 or step == steps - 1):
        pc = [policy.probs(p)[CORRECT_INDEX[qids[p]]] for p in range(len(qids))]
        print(step, round(mean_r, 3), [round(x, 2) for x in pc])
return policy, qids, env
```
The `None` is the reference policy — no KL regularization in this phase.
Respect the `verbose` flag: the tests call `train` many times and don't want
hundreds of lines of output.
</details>

<details><summary>Level 3 — code</summary>

```python
for step in range(steps):
    mean_r = grpo_step(policy, reward_of, None, list(range(len(qids))),
                       group_size=8, rng=rng)
    if verbose and (step % 40 == 0 or step == steps - 1):
        pc = [round(policy.probs(p)[CORRECT_INDEX[qids[p]]], 2)
              for p in range(len(qids))]
        print(f"{step:>4}  {mean_r:>10.3f}  {pc}")

return policy, qids, env
```
</details>

---

## `prob_correct`

<details><summary>Level 1 — nudge</summary>

One list comprehension. `CORRECT_INDEX[qid]` gives the index of the intended
candidate; `policy.probs(p)` gives the distribution.
</details>

<details><summary>Level 3 — code</summary>

```python
def prob_correct(policy, qids):
    return [policy.probs(p)[CORRECT_INDEX[qids[p]]] for p in range(len(qids))]
```
</details>

---

## Understanding the q5 result

<details><summary>Why is my q5 probability stuck around 0.28?</summary>

**That's the correct outcome.** Run this to see it directly:

```bash
cd ../common && python3 -c "
from tiny_sql_env import SQLEnv, TASKS
from candidates import CANDIDATES
from rewards import extract_sql
env = SQLEnv()
for i, c in enumerate(CANDIDATES['q5']):
    ok, res = env.execute(extract_sql(c))
    print(i, res if ok else 'ERROR')
"
```

Three candidates return `[('furniture',)]`. Execution accuracy gives all three
`1.0`. Since GRPO's advantage is `(r - group_mean) / std`, three equally-rewarded
actions produce **identical advantages** — there is no signal favouring the
semantically correct one, so its probability drifts around chance.

The mean reward still climbs to 1.0, because the agent *is* maximizing the
reward it was given. It's just the wrong reward. This is reward misspecification
in miniature, and it's why Phases 3 and 4 exist.
</details>

---

## Debugging table

| Symptom | Likely cause |
|---------|--------------|
| `TypeError: unsupported operand ... tuple` | `combine()` returns `(total, breakdown)` — unpack it |
| Every reward is `0.0` | you're passing the raw completion where a Task is expected, or your qid lookup is off |
| Rewards aren't binary | you passed weights beyond `{"exec": 1.0}` |
| `q5` test fails because P(correct) is *high* | same cause — extra reward components leaked in |
| Tests are slow / spam output | `train` is ignoring `verbose=False` |
| Nothing learns | you forgot to actually call `grpo_step` (it updates the policy in place) |
