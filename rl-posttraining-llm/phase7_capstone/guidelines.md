# Phase 7 Guidelines — Capstone: the ablation table

## Overview

Integrate the phases into one comparison and answer the two questions that
actually matter for shipping this:

1. **Which mechanism earns its complexity?**
2. **Can you train without ever executing generated SQL against real data — and
   still be accurate?**

**File to implement:** `template_ablation.py`
**Validate with:** `python test_phase7.py`
**Prerequisite:** Phase 4 must be done — this imports your `graph_reward`.

## The table

| config | reward | executes during training? | accuracy | q5 P(correct) |
|---|---|---|---|---|
| `exec_only` | execution accuracy only | yes | 1.00 | **0.28** |
| `phased` | format+syntax+schema+ngram+exec | yes | 1.00 | 0.98 |
| `graph_only` | graph match | **NO** | 1.00 | 0.98 |
| `phased_plus_graph` | shaping + graph | **NO** | 1.00 | 0.98 |

Two columns carry the whole argument:

- **`q5 P(correct)`** — plain accuracy says every config is perfect. It isn't.
  `exec_only` sits at chance on `q5` because execution accuracy cannot see the
  difference between the correct query and a wrong-metric one that happens to
  return the same rows. **A single headline metric hid a broken model.** Always
  carry a diagnostic that measures what your main metric can't.
- **`executes during training?`** — `graph_only` matches the best accuracy while
  never running a generated query against data. In a regulated environment that
  isn't a nice-to-have, it's the difference between a project you can run and one
  you can't.

### One honest caveat about "execution-free"

`graph_only` touches the database **zero** times during training — the test
asserts it. `phased_plus_graph` is subtler: its `syntax` component asks SQLite to
*prepare* the statement (`EXPLAIN`) without reading any rows. Whether that counts
as "touching data" is a question for your compliance reviewer, not for you. If
the answer is no, drop the syntax term. Be precise about this rather than
claiming a blanket "no execution".

## Implementation Steps

1. **`make_reward_fn`** — one closure per config. `graph_only` calls
   `graph_reward(completion, task.gold_sql)` and nothing else. For
   `phased_plus_graph`, use the shaping components *without* `exec`, and add the
   graph reward with a weight that lets it dominate (~1.5).
2. **`train_config`** — the Phase 1/2 loop verbatim.
3. **`evaluate`** — greedy argmax per task, execution accuracy averaged, plus
   `q5`'s `P(correct)`. Execution **is** allowed here: this is measurement, not
   training, and the distinction is exactly the compliance argument.
4. **`run_ablation`** — train and evaluate each config, set
   `executes_during_training` honestly.

## Requirements (what the tests check)

| # | Requirement |
|---|-------------|
| 1 | `run_ablation` returns one row per config in `CONFIGS` |
| 2 | Every row is well-formed (types, `accuracy`/`q5_prob_correct` in `[0,1]`) |
| 3 | `executes_during_training` is `True` for exec/phased, `False` for the graph configs |
| 4 | `exec_only` reproduces the `q5` blind spot (`P(correct) < 0.5`) |
| 5 | `phased` fixes `q5` (`P(correct) > 0.8`) |
| 6 | `graph_only` fixes `q5` (`P(correct) > 0.8`) |
| 7 | **`graph_only` performs ZERO executions during training** (counted with an instrumented executor) |
| 8 | `graph_only` reaches accuracy ≥ the `exec_only` baseline |
| 9 | Every config reaches accuracy `1.0` on this task set |
| 10 | The table demonstrates the headline: an execution-free config matches the best accuracy |

## The write-up (the actual deliverable)

Tests can't grade prose, so this part is on you. Two to three pages:

- **Which mechanism moved the needle**, with the table as evidence. Be honest
  when something didn't help — on a 5-task toy set, `phased_plus_graph` is not
  measurably better than `graph_only`, and saying so is worth more than
  inventing a story.
- **Where reward hacking showed up** and how you caught it (Phase 2, exercise 4).
- **The safety story:** can you train with zero execution against real data and
  still get accuracy? You now have a number, not an opinion.
- **What this toy setup cannot tell you.** Five tasks, four candidates each, a
  tabular policy. It demonstrates mechanisms, it does not measure them. The
  ranking of these methods on Spider/BIRD with a real model is an open question
  your table does not answer.

## Graduating to real benchmarks

- **Spider** — cross-domain text-to-SQL; execution + exact-set match.
- **BIRD** — larger and dirtier; execution accuracy plus efficiency.
- For the analytic-agent extension, build a small internal benchmark of
  multi-step questions with checkable answers over your own schema — Phase 6's
  generator is a starting point.

## Suggested reading order

1. The survey (2509.02547) — taxonomy and vocabulary.
2. Reasoning-SQL (2503.23157) — partial rewards.
3. Graph-Reward-SQL (2505.12380) — execution-free reward.
4. TRUST-SQL / MARSQL — multi-turn schema discovery.
5. Scaling Generalist Data-Analytic Agents (2509.25084).

Confirm each arXiv ID before citing — several in the original list didn't
resolve. See the note in the top-level README.

## Done When

`python test_phase7.py` is all PASS and the write-up exists. You can then defend,
from your own runs, which mechanisms your application needs — and show a
training configuration that never executes generated SQL against real data yet
still reaches full accuracy.
