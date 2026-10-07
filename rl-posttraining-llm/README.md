# RL Post-Training for LLMs — Hands-On, from Scratch

A progressive, buildable course on **reinforcement-learning post-training of
LLMs for applications**, using **text-to-SQL and agentic data analysis** as the
running application (in the spirit of MARSQL and the papers below). You start
from the RL fundamentals and end at a multi-turn, schema-discovering data-analytic
agent trained with process-level rewards.

The core machinery (`common/`) is written in **pure Python standard library** —
no numpy, no torch, no model download — so every early phase *runs on a laptop
CPU in seconds* and you can read the GRPO update end to end. Later phases add
templates that scale the exact same ideas onto a real HF model with TRL.

---

## What I think about your reading list (read this first)

Short version: **the concepts are exactly the right ones to learn, and they
form a clean progression** — which is what this course is built around. A few
honest caveats so you spend your time well:

- **Organize by mechanism, not by paper.** Strip the SQL branding and the whole
  list reduces to five reusable ideas, and that's how the phases are structured:
  1. *phased / partial rewards* — don't train on sparse execution accuracy alone;
     layer dense, cheap signals underneath it (Reasoning-SQL, Progress-SQL).
  2. *process / step-wise rewards* — supervise the reasoning trace, not just the
     final answer (Reward-SQL PRM; "Rewarding the Scientific Process").
  3. *execution-free rewards* — score a query without running it against real
     data, e.g. graph/AST matching (Graph-Reward-SQL) — the one that matters most
     for a **regulated** setting.
  4. *tool-integrated multi-turn RL over unknown schemas* — schema discovery is
     part of the agent loop, not a given (TRUST-SQL, MARSQL).
  5. *agentic scaling + self-generated data* — process-reward modeling for
     multi-step analysis, multi-agent table reasoning, self-evolving data
     curation (Scaling Generalist Data-Analytic Agents, Mixture-of-Minds,
     EvoDS/CurateEvo).
  Learn these five and every paper on the list becomes a variation you can read
  in an afternoon. The **survey (2509.02547)** is the right anchor — read it to
  place the rest.

- **Verify the citations yourself before you lean on them.** I could not confirm
  several of the arXiv IDs, and a few (e.g. `2606.06825`, `2603.16448`,
  `2604.24198`) look off. Treat the paper names as *pointers to mechanisms*; the
  mechanisms are real and are what you'll implement here. Where an ID is wrong,
  search the title on arXiv/Semantic Scholar and grab the current version.

- **Your instinct to make schema-linking the first stage is correct.** For a
  real "analyze the data in a database" agent, ungrounded generation is the main
  failure mode. That's why schema-linking gets its own reward from Phase 2 and
  becomes an *action* (schema discovery) in Phase 5.

- **One trap you'll hit immediately, and it's baked into Phase 1 as a lesson:**
  on small data, execution accuracy gives **false positives** — a semantically
  wrong query can return the same result set as the gold query by coincidence.
  In this course's tiny DB, three different `q5` candidates all return
  `furniture`, so execution reward *cannot* tell the correct query from a
  wrong-metric one. This is precisely why process rewards and execution-free
  graph rewards (Phases 3–4) exist. You'll see it happen, not just read about it.

---

## Paper → Phase map

| Phase | Mechanism | Anchor papers |
|-------|-----------|---------------|
| 0 | Policy gradient, baselines, GRPO from scratch | (fundamentals) DeepSeek-R1 / GRPO |
| 1 | Sparse execution-accuracy reward (the baseline to beat) | (all text-to-SQL RL) |
| 2 | Phased / partial rewards + reward curriculum | **Reasoning-SQL** (2503.23157), **Progress-SQL** |
| 3 | Process reward model (step-wise reasoning supervision) | **Reward-SQL**, Rewarding the Scientific Process |
| 4 | Execution-free reward via graph/AST matching | **Graph-Reward-SQL** (2505.12380) |
| 5 | Tool-integrated multi-turn RL over unknown schemas | **TRUST-SQL**, **MARSQL** |
| 6 | Agentic data-analysis post-training beyond SQL | Scaling Generalist Data-Analytic Agents (2509.25084), Mixture-of-Minds, EvoDS/CurateEvo |
| 7 | Capstone: integrate the above into one agent | — |
| — | Taxonomy / vocabulary of the field | **Survey** (2509.02547) |

---

## Directory structure

```
rl-posttraining-llm/
├── README.md                     # this file
├── run_all_tests.sh              # every phase's tests = your progress dashboard
├── requirements.txt              # only needed for the "real model" (TRL) templates
├── common/                       # zero-dependency, RUNNABLE core
│   ├── tiny_sql_env.py           #   SQLite text-to-SQL "gym"
│   ├── rewards.py                #   composable reward library (the papers, as code)
│   ├── grpo.py                   #   GRPO math + tabular policy, from scratch
│   ├── candidates.py             #   candidate-completion pools for CPU exercises
│   ├── test_harness.py           #   tiny stdlib test runner (PASS/FAIL/TODO)
│   └── test_common.py            #   smoke tests (pure stdlib)
├── phase0_foundations/           # policy gradient, baselines, GRPO
├── phase1_execution_reward/      # sparse reward baseline
├── phase2_phased_rewards/        # Reasoning-SQL / Progress-SQL
├── phase3_process_reward/        # Reward-SQL PRM
├── phase4_execution_free/        # Graph-Reward-SQL
├── phase5_multiturn_schema/      # TRUST-SQL / MARSQL agent loop
├── phase6_agentic_analysis/      # generalist data-analytic agents
├── phase7_capstone/              # integrate everything + ablation table
└── solutions/                    # RUNNABLE reference implementations (phases 0-2)
```

**Every phase directory contains the same four files**, so the workflow never
changes:

| File | What it's for |
|------|---------------|
| `README.md` | concepts, goals, exercises — read first |
| `guidelines.md` | the detailed spec: key concepts, implementation steps, and the numbered **requirements table** the tests enforce |
| `template_*.py` | the file you implement, with TODOs |
| `test_phaseN.py` | run it to check yourself — **this is the spec in executable form** |
| `HINTS.md` | progressive hints: Level 1 nudge → Level 2 structure → Level 3 code, plus a debugging table |

Phases 0–2 also ship runnable solutions. Phases 3–7 deliberately don't — the
guidelines and tests pin down the requirements precisely enough that you don't
need one, and building them yourself is the point.

### The tests are designed to be run from minute one

Unimplemented functions report as **TODO**, not as failures, so the suite works
as a progress dashboard rather than a wall of red:

```
[TODO] advantages are zero-mean
       -> not implemented yet
[PASS] probs() returns a valid distribution
[FAIL] GRPO has lower signal variance
       -> expected GRPO signal^2 (0.79) < REINFORCE (0.79)
```

`run_all_tests.sh` exits non-zero only when something is genuinely broken
(FAIL/ERROR) — never for TODOs.

**A few tests assert that your agent *fails*.** Phase 1 checks that `q5` stays
near chance; Phase 3 checks that the process reward inherits the executor's
blind spot. Those failures are the lessons the later phases exist to fix, so
"passing" means reproducing them faithfully.

---

## Quick start (no installs)

```bash
cd rl-posttraining-llm
./run_all_tests.sh             # see all 104 checks and what's left to do

cd common
python test_common.py          # prove the core works
python grpo.py                 # watch GRPO learn on a toy task
python rewards.py              # see the reward breakdown on good vs bad SQL
```

Then, for each phase in order: read `README.md`, read `guidelines.md`, implement
`template_*.py`, run `test_phaseN.py` until it's green, and reach for `HINTS.md`
only when stuck.

```bash
cd phase0_foundations
python test_phase0.py          # 12 TODOs — your checklist
```

## Two tracks

- **CPU track (default):** the tabular-policy stand-in in `common/grpo.py`
  learns a distribution over a small pool of candidate completions. All the RL
  bookkeeping — group sampling, reward scoring, group-relative advantages,
  KL-to-reference — is *real*; only the token generator is swapped for a
  discrete choice you can inspect. Everything runs in seconds, no GPU.
- **Real-model track (optional):** from Phase 2 onward each README shows how to
  lift the exact same reward functions and loop onto a small HF model
  (e.g. `Qwen2.5-0.5B-Instruct`) using `trl`'s `GRPOTrainer`. See
  `requirements.txt`. The reward functions in `common/rewards.py` are written to
  plug straight into TRL's `reward_funcs` interface.

## Prerequisites

- Python 3.9+ (CPU track needs nothing else).
- For the real-model track: `pip install -r requirements.txt` and ideally a GPU.
- Comfort with softmax, log-probabilities, and the idea of a policy gradient.
  Phase 0 rebuilds the rest.

## A note on scope

These are learning implementations: clarity over performance, tiny data over
benchmarks. The point is that you can read every line of the reward and the
update and know *exactly* what signal is training your policy — then scale the
same code to a real model and a real benchmark (Spider / BIRD) with confidence.
