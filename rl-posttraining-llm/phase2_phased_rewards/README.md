# Phase 2 — Phased / progressive rewards (Reasoning-SQL, Progress-SQL)

**Goal:** fix Phase 1's starvation by layering dense partial rewards under the
sparse execution reward, then turn the weights into a curriculum.

## The two ideas

**1. Partial rewards (Reasoning-SQL).** Score components that are *dense* — they
fire even when the query is wrong on execution — so there is always gradient:

```
total = w_exec·execution + w_syntax·syntax + w_schema·schema_link
      + w_ngram·ngram_sim + w_format·format
```

All five live in `common/rewards.py`. The headline result you're reproducing:
RL with these rewards **generalizes better than SFT**, because SFT imitates one
gold query while RL explores many correct-and-incorrect queries and learns the
*decision boundary* between them.

**2. Reward curriculum (Progress-SQL).** Don't keep the weights fixed. Start
shaping-heavy (dense, easy signal so early training isn't starved) and **anneal**
toward execution accuracy so the *final* objective is correctness, not surface
similarity:

```python
def curriculum_weights(progress):        # progress in [0,1] over training
    shaping = max(0.0, 1.0 - progress)   # 1 -> 0
    exec_w  = 0.5 + 1.5 * progress        # 0.5 -> 2.0
    return {"format":0.3*shaping, "syntax":0.4*shaping, "schema":0.6*shaping,
            "ngram":0.3*shaping, "exec":exec_w}
```

## Exercises

1. **Static phased rewards.** Turn all five components on with fixed weights.
   Compare the learning curve to Phase 1: signal is nonzero from step 0.
2. **Break the q5 tie.** Confirm schema-linking + n-gram rewards make the policy
   prefer the *semantically correct* `q5` query even though execution reward
   can't distinguish it. This is the payoff of dense signal.
3. **Curriculum.** Implement the annealed schedule. Verify greedy execution
   accuracy still reaches 1.0 — i.e. the shaping didn't hijack the true objective.
4. **Reward hacking hunt.** Set `w_ngram` very high and `w_exec` to 0. Watch the
   policy learn to *look like* the gold query without being correct. This is the
   danger of surface-form rewards; write down why the curriculum's anneal-up of
   `exec` prevents it.

```bash
cd ../solutions/phase2_phased_rewards && python partial_rewards.py
```

## Real-model track — TRL adapter

`common/rewards.py` plugs straight into `trl.GRPOTrainer`:

```python
def make_reward_func(env, task_lookup, weights):
    def reward_func(prompts, completions, **kw):
        out = []
        for prompt, comp in zip(prompts, completions):
            task = task_lookup(prompt)          # map prompt -> Task (question+gold)
            total, _ = combine(comp, task, env, weights)
            out.append(total)
        return out
    return reward_func

trainer = GRPOTrainer(model=..., reward_funcs=[make_reward_func(env, lookup, W)], ...)
```

For the curriculum, pass a fresh `weights` dict each epoch via a callback, or
register one reward function per component and schedule their coefficients.

---

## Files in this phase

| File | Use it for |
|------|-----------|
| `guidelines.md` | the full spec: concepts, implementation steps, and the 13 numbered requirements the tests enforce |
| `template_partial_rewards.py` | the file you implement |
| `test_phase2.py` | `python test_phase2.py` — checks your work (13 requirements; unimplemented shows as TODO, not failure) |
| `HINTS.md` | progressive hints (Level 1 nudge → Level 3 code) and a debugging table |

Read `guidelines.md` before you start writing code.

## Done when

Phased rewards learn from step 0, the curriculum still maximizes execution
accuracy, and you can produce a reward-hacked policy on demand (and explain the
fix).
