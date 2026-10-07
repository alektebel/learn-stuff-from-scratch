# Phase 5 — Progressive Hints

---

## `policy_index`

<details><summary>Level 3 — code</summary>

```python
def policy_index(task_idx, turn, max_turns=MAX_TURNS):
    return task_idx * max_turns + turn
```
Standard row-major flattening of a (task, turn) grid. The policy was allocated
with `n_tasks * MAX_TURNS` rows to match.
</details>

---

## `rollout`

<details><summary>Level 1 — nudge</summary>

A loop over turns. Each iteration: pick an action, then either stop (`final`) or
call a tool and record what you learned. The one thing people forget: set
`final_sql` on **both** exit paths — calling `final` *and* running out of turns.
</details>

<details><summary>Level 2 — structure</summary>

```
for turn in range(max_turns):
    a = policy.sample(policy_index(task_idx, turn), rng)
    if a == FINAL_ACTION:
        traj.finished = True
        break
    table = ACTIONS[a].replace("describe_", "")     # "describe_orders" -> "orders"
    traj.steps.append((ACTIONS[a], env.describe(table)))
    traj.discovered.add(table)

traj.final_sql = write_sql(traj.discovered, task)   # AFTER the loop
return traj
```
</details>

<details><summary>Level 3 — code</summary>

```python
def rollout(policy, task_idx, task, env, rng, max_turns=MAX_TURNS):
    traj = Trajectory(task_qid=task.qid)
    for turn in range(max_turns):
        a = policy.sample(policy_index(task_idx, turn), rng)
        if a == FINAL_ACTION:
            traj.finished = True
            break
        table = ACTIONS[a].replace("describe_", "")
        traj.steps.append((ACTIONS[a], env.describe(table)))
        traj.discovered.add(table)
    traj.final_sql = write_sql(traj.discovered, task)
    return traj
```
</details>

---

## `turn_shaping` / `trajectory_reward`

<details><summary>Level 1 — nudge</summary>

Shaping is two terms: a bonus for each gold table you found, a charge for each
call you made. `discovered` is a **set**, so the "don't double-count" requirement
is already handled — describing the same table twice adds one discovery and two
charges, which is exactly the incentive you want.
</details>

<details><summary>Level 3 — code</summary>

```python
def turn_shaping(traj, task):
    gold = {t.lower() for t in task.gold_tables}
    found = len(gold & {d.lower() for d in traj.discovered})
    return found * 1.0 - STEP_COST * len(traj.steps)


def trajectory_reward(traj, task, env, w_shaping=0.0):
    exec_r = execution_accuracy(traj.final_sql, task, env.db)
    return exec_r + w_shaping * turn_shaping(traj, task)
```
</details>

---

## `train` — trajectory-level GRPO

<details><summary>Level 1 — nudge</summary>

This is Phase 0's update with one difference: the thing you compute an advantage
for is an entire episode, and that single advantage is applied to **every turn**
of the episode.

The practical catch: you need the `(policy_row, action)` pairs the episode
actually took. `rollout` doesn't return them, so inside `train` you either
re-implement the loop while recording them, or extend `Trajectory` to carry
them. Recording inline is simplest.
</details>

<details><summary>Level 2 — structure</summary>

```
grad = zeros[n_prompts][n_actions]; n_updates = 0

for task_idx, task in enumerate(TASKS):
    trajs, rewards = [], []
    for _ in range(group_size):
        env = ToolEnv()                 # FRESH env per rollout
        traj, taken = rollout_recording_actions(...)
        trajs.append((traj, taken))
        rewards.append(trajectory_reward(traj, task, env, w_shaping))

    advantages = group_relative_advantages(rewards)

    for (traj, taken), adv in zip(trajs, advantages):
        for row, a in taken:
            probs = policy.probs(row)
            for j in range(n_actions):
                grad[row][j] += adv * ((1.0 if j == a else 0.0) - probs[j])
            n_updates += 1

# ascent, normalized
scale = policy.lr / max(n_updates, 1)
for p, j: policy.logits[p][j] += scale * grad[p][j]
```
</details>

<details><summary>Level 3 — code</summary>

```python
for step in range(steps):
    grad = [[0.0] * len(ACTIONS) for _ in range(policy.n_prompts)]
    n_updates, total_r = 0, 0.0

    for task_idx, task in enumerate(TASKS):
        trajs, rewards = [], []
        for _ in range(group_size):
            env = ToolEnv()
            traj, taken = Trajectory(task_qid=task.qid), []
            for turn in range(MAX_TURNS):
                row = policy_index(task_idx, turn)
                a = policy.sample(row, rng)
                taken.append((row, a))
                if a == FINAL_ACTION:
                    traj.finished = True
                    break
                table = ACTIONS[a].replace("describe_", "")
                traj.steps.append((ACTIONS[a], env.describe(table)))
                traj.discovered.add(table)
            traj.final_sql = write_sql(traj.discovered, task)
            trajs.append((traj, taken))
            rewards.append(trajectory_reward(traj, task, env, w_shaping))

        advs = group_relative_advantages(rewards)
        total_r += sum(rewards)
        for (traj, taken), adv in zip(trajs, advs):
            for row, a in taken:
                probs = policy.probs(row)
                for j in range(len(ACTIONS)):
                    grad[row][j] += adv * ((1.0 if j == a else 0.0) - probs[j])
                n_updates += 1

    scale = policy.lr / max(n_updates, 1)
    for p in range(policy.n_prompts):
        for j in range(len(ACTIONS)):
            policy.logits[p][j] += scale * grad[p][j]
    last_mean = total_r / (len(TASKS) * group_size)
```
</details>

---

## Debugging table

| Symptom | Likely cause |
|---------|--------------|
| Agent solves nothing | `final_sql` never set on the timeout path, or `write_sql` called before the loop finished |
| Agent describes every table always | `w_shaping=0` (expected!) — that's what shaping is for |
| `final` action seems ignored | you `continue`d instead of `break`ing, or checked the wrong index |
| Reward looks right but nothing learns | you didn't record `(row, action)` per turn, so the gradient lands on the wrong rows |
| Wildly unstable training | forgot to normalize by `n_updates`, so longer episodes get bigger steps |
| Tool-call counts look impossible | reused one `ToolEnv` across rollouts instead of making a fresh one |
| Shaping test fails on double-counting | you counted discoveries from `steps` (a list) instead of `discovered` (a set) |
