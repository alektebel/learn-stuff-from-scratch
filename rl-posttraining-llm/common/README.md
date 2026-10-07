# `common/` — the zero-dependency core

Everything here is pure Python standard library. It is the shared "gym",
reward library, and RL algorithm that every phase builds on.

| File | What it is | Read it to understand |
|------|------------|-----------------------|
| `tiny_sql_env.py` | In-memory SQLite DB + (question, gold SQL) tasks + executor | how a text-to-SQL RL *environment* and execution reward work |
| `rewards.py` | Composable reward functions in `[0,1]` + `combine()` | the papers as code: format, syntax, schema-linking, n-gram, execution |
| `grpo.py` | Group-relative advantages + tabular softmax policy + `grpo_step` | the actual GRPO update, with no framework in the way |
| `candidates.py` | Fixed candidate-completion pools per task | how we run "real" RL on CPU without a token generator |
| `test_common.py` | Smoke tests | that all of the above works |

## Run it

```bash
python test_common.py     # all smoke tests
python grpo.py            # GRPO learns a toy task; watch reward climb
python rewards.py         # reward breakdown on a good vs bad completion
python tiny_sql_env.py    # print schema + gold result sets
```

## The one function to internalize

```python
def group_relative_advantages(rewards):
    mean = sum(rewards) / len(rewards)
    std  = (sum((r-mean)**2 for r in rewards)/len(rewards)) ** 0.5
    return [(r - mean) / (std + 1e-6) for r in rewards]
```

That is the whole difference between GRPO and vanilla policy gradient: the
baseline is the *group* mean over completions of the same prompt, and the scale
is the group std. No value network. Everything else — token-level vs tabular
policy, SQL vs toy — is just what you plug into `reward_of(prompt, action)`.

## Plugging into a real trainer

`rewards.py` functions have the signature `(completion, task, env) -> float`.
TRL's `GRPOTrainer` wants `reward_funcs(prompts, completions, **kw) -> list[float]`.
The adapter is three lines (shown in `phase2_phased_rewards/README.md`): iterate
the batch, look up each prompt's task, call `combine()`.
