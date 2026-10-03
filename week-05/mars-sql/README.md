# MARS-SQL From Scratch

Replicate **MARS-SQL** — a three-agent Text-to-SQL system — on a tiny in-memory
database, then **cite** the generated SQL back to the schema sentences that
justified it, using ContextCite.

> **Yang, Zhang, He, Fung. "MARS-SQL: A Multi-Agent Reinforcement Learning
> Framework For Text-to-SQL." arXiv:2511.01008.**
> [paper](https://arxiv.org/abs/2511.01008) ·
> [code](https://github.com/YangHaolin0526/MARS-SQL)

Do [`../contextcite/`](../contextcite/) first. The last check here imports it.

## What the paper does

One-shot Text-to-SQL treats `Y = f(Q, S)` as a translation. MARS-SQL treats it
as an interactive policy. Three agents:

| Agent | Job | Training signal in the paper |
|---|---|---|
| **Grounding** | Keep the tables and columns the question needs | GRPO, graded schema reward |
| **Generation** | ReAct Think-Act-Observe against a live database | GRPO on trajectory reward |
| **Validation** | Pick the best of N trajectories by P("Yes") | Next-token generative verification |

You will not train GRPO. You will implement the *decision procedures* the
trained agents are executing, on a database small enough that the right
decision is unique and checkable.

## Why it sits next to ContextCite

The Grounding Agent is already a form of attribution: which schema sources
matter. ContextCite asks the same question of the *finished SQL*. If they
disagree, one of them is wrong — and the last check makes you look at that.

```bash
cd week-05/mars-sql
python3 check.py          # 8 graded checks against YOUR code
```

Checks only. Templates raise `NotImplementedError`. `db.py` is provided.

## The files

| File | What it is |
|---|---|
| `db.py` | **Provided** — two tables, a tiny SQL executor, the running question |
| `grounding.py` | Schema linking + the paper's graded reward |
| `generation.py` | ReAct loop, typo recovery, multiple trajectories |
| `validation.py` | Generative selection: score P("Yes"), not majority vote |
| `cite.py` | Attribute the SQL to schema sources via ContextCite |
