# Phase 5 — Tool-integrated multi-turn RL over unknown schemas (TRUST-SQL / MARSQL)

**Goal:** stop assuming the schema is handed to the model. Make **schema
discovery an action**. The agent interacts with the database over multiple turns
— listing tables, inspecting columns, sampling values — before (and while)
writing SQL. This is the phase most aligned with your next step: multi-table
grounding / schema linking as a first *stage of the agent loop*.

## From single-shot to an agent loop

Phases 1–4 were single-shot: prompt in, query out, reward. Now the episode is a
**trajectory** of tool calls:

```
observe(question)                       # schema is NOT in the prompt
  -> list_tables()            -> [customers, products, orders]
  -> describe(orders)         -> columns + types + sample rows
  -> describe(customers)      -> ...
  -> propose_sql(...)         -> executor result or error
  -> (maybe) revise           -> ...
  -> final_answer
```

The tools are the action space. The reward is (mostly) at the end
(execution/graph reward on the final query), so you now have a **credit
assignment** problem across turns — GRPO still works, but the "completion" is the
whole trajectory, and you can add **turn-level shaping** (did this tool call
reveal a gold table? did the revision fix a syntax error?).

## Concepts

- **Tool schema.** Define `list_tables`, `describe(table)`, `sample(table)`,
  `run(sql)`, `final(sql)`. Each returns a text observation appended to context.
- **Trajectory-level GRPO.** Sample G *trajectories* per question; reward each by
  its final query; standardize within the group. Same math as Phase 0, longer
  "action".
- **Turn/step shaping (MARSQL flavor).** Reward information gain: `+` for
  describing a gold table, `+` for a revision that turns an execution error into
  a valid result, `−` small step penalty to discourage aimless probing.
- **Schema-linking as first stage.** Score how well the discovered schema subset
  matches the gold link set *before* the final query — this is your schema
  reward from Phase 2, now applied to the agent's *exploration*.

## Exercises

1. **Build the tool-augmented env.** Wrap `common/tiny_sql_env.py`: hide the
   schema from the prompt; expose `list_tables/describe/sample/run/final` that
   return string observations.
2. **Define a trajectory policy.** On CPU, a policy over tool choices per turn
   (extend the tabular policy to condition on turn state). Real-model track: the
   LLM emits tool calls; parse and execute them.
3. **Trajectory GRPO.** Reward = final-query execution/graph reward. Confirm the
   agent learns to *describe the right tables first* for multi-join `q4`/`q5`.
4. **Add turn-level shaping** and measure: fewer wasted tool calls, faster
   convergence, better grounding on unseen schemas.
5. **Generalization test.** Add a *new* table/schema at eval time the agent never
   trained on; a well-shaped schema-discovery policy should still ground itself.

## `template_agent_loop.py`

Skeleton: tool-augmented env, a turn-conditioned policy, a trajectory sampler,
and trajectory-level GRPO with optional turn shaping.

## Real-model track

Standard tool-use loop: system prompt describes the tools, model emits a tool
call, you execute and append the observation, repeat to a turn budget, grade the
final query. Train with `trl` GRPO over trajectories (reward on the last step).
This is essentially a compact MARSQL.

---

## Files in this phase

| File | Use it for |
|------|-----------|
| `guidelines.md` | the full spec: concepts, implementation steps, and the 14 numbered requirements the tests enforce |
| `template_agent_loop.py` | the file you implement |
| `test_phase5.py` | `python test_phase5.py` — checks your work (14 requirements; unimplemented shows as TODO, not failure) |
| `HINTS.md` | progressive hints (Level 1 nudge → Level 3 code) and a debugging table |

Read `guidelines.md` before you start writing code.

## Done when

The agent discovers the schema it needs (not the whole schema) and grounds
multi-join queries on a schema it never saw during training.
