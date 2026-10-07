# Solutions

Runnable reference implementations. All pure stdlib — no installs, CPU, seconds.

| Solution | Demonstrates |
|----------|--------------|
| `phase0_foundations/reinforce_vs_grpo.py` | GRPO's group baseline cuts gradient-signal variance vs plain REINFORCE |
| `phase1_execution_reward/grpo_sql.py` | GRPO with sparse execution reward; reproduces the `q5` execution-accuracy false positive |
| `phase2_phased_rewards/partial_rewards.py` | phased rewards learn from step 0; Progress-SQL-style curriculum still maximizes execution accuracy |

```bash
python phase0_foundations/reinforce_vs_grpo.py
python phase1_execution_reward/grpo_sql.py
python phase2_phased_rewards/partial_rewards.py
```

Phases 3–7 intentionally ship **no solution** — that's where the real learning
is. They're not left vague, though: each has a `guidelines.md` with a numbered
requirements table, a `test_phaseN.py` that enforces every requirement, and a
`HINTS.md` with three escalating hint levels per function. The tests *are* the
solution, expressed as behaviour instead of code.

If you want a reference for those phases, the honest answer is: make the tests
pass, then re-read `guidelines.md` and check you can explain *why* each
requirement exists.

**Use these as reference, not a shortcut** — implement the templates yourself
first, then diff.
