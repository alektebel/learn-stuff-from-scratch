# Phase 7 — Capstone: one agent, all the mechanisms

**Goal:** integrate everything into a single trainable text-to-SQL / data-analysis
agent, and write it up like a paper. This is where the five mechanisms stop being
separate exercises and become one system.

## The system to build

A multi-turn agent that:

1. **Discovers the schema** it needs via tools (Phase 5), scored by a
   schema-linking reward on its *exploration* (Phase 2).
2. **Writes SQL** trained with **phased rewards on a curriculum** (Phase 2),
   with an **execution-free graph reward** as the inner-loop signal so no
   sensitive data is executed during training (Phase 4).
3. **Reasons over returned tables** across multiple steps, supervised by a
   **process reward model** (Phases 3 & 6).
4. **Improves its own training set** with an EvoDS-style self-generation loop
   (Phase 6).
5. Trained end to end with **trajectory-level GRPO** (Phase 0).

## Deliverables

- **Code:** the integrated agent + training script (real-model track: `trl`).
- **Ablation table** — the single most useful thing you can produce. Vary one
  mechanism at a time and report held-out execution accuracy + a
  data-safety flag:

  | Config | Reward | Schema | Exec in loop? | Held-out acc |
  |--------|--------|--------|---------------|--------------|
  | Baseline | exec only | given | yes | … |
  | + phased | phased+curriculum | given | yes | … |
  | + graph reward | phased+graph | given | **no** | … |
  | + PRM | phased+graph+PRM | given | no | … |
  | + schema discovery | " | discovered | no | … |
  | + EvoDS | " | discovered | no | … |

- **Write-up** (2–3 pages): which mechanism moved the needle, where reward
  hacking showed up and how you caught it, and the safety story (can you train
  with **zero** execution against real data and still get accuracy?).

## Benchmarks to graduate to

Once the CPU version works, move the real-model track to a standard benchmark:

- **Spider** (cross-domain text-to-SQL, execution + exact-match).
- **BIRD** (larger, dirtier, execution accuracy + efficiency).
- For the analytic-agent extension, build a small internal benchmark of
  multi-step questions with checkable answers over your own schema.

## Suggested reading order (the survey first)

1. The survey (2509.02547) — the vocabulary and taxonomy.
2. Reasoning-SQL (2503.23157) — partial rewards.
3. Graph-Reward-SQL (2505.12380) — execution-free reward.
4. TRUST-SQL / MARSQL — multi-turn schema discovery.
5. Scaling Generalist Data-Analytic Agents (2509.25084) — the general capability.

(Confirm each arXiv ID before citing — see the note in the top-level README.)

---

## Files in this phase

| File | Use it for |
|------|-----------|
| `guidelines.md` | the full spec: concepts, implementation steps, and the 10 numbered requirements the tests enforce |
| `template_ablation.py` | the file you implement |
| `test_phase7.py` | `python test_phase7.py` — checks your work (10 requirements; unimplemented shows as TODO, not failure) |
| `HINTS.md` | progressive hints (Level 1 nudge → Level 3 code) and a debugging table |

Read `guidelines.md` before you start writing code.

## Done when

You can hand someone the ablation table and defend, from your own runs, which of
the five mechanisms your application actually needs — and show a training
configuration that never executes generated SQL against real data yet still
reaches competitive accuracy.
