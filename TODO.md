# TODO

The open work in this repository, in order. Each item links to the plan that specifies it.
Update this file in the same commit that finishes or adds an item.

## Blocked on a decision or an input from the owner

- [ ] **A model API for harness-lab phase 1.** An OpenAI-compatible endpoint, its key as an
      environment secret, and a cost cap per evaluation run. Phase 1 has been blocked on
      this since phase 0 closed. → [harness-lab/CLAUDE.md](harness-lab/CLAUDE.md)
- [ ] **GPU access: yes or no.** Decides whether the GPU-required half of
      [inference-lab](inference-lab/README.md) and step A of the
      [CUDA roadmap](cuda-from-scratch/ROADMAP.md) are in the plan, or stay code without
      measurements.
- [ ] **Horizon and goal for harness-lab phase 7** (memory): how many weeks, and whether the
      aim is breadth or a result on correction/forgetting. Decides what is cut.
- [ ] **MCP server:** what it exposes, from scratch or SDK, stdio or HTTP, and where it lives.
      Related: [enterprise-ai-projects/10](enterprise-ai-projects/10-mcp-legacy-erp.md).
- [ ] **Inputs only the owner can provide:** the text of the 149 unread X posts and short links
      ([RESOURCES.md](RESOURCES.md), "Unsorted"); titles for the 60 unverified arXiv IDs;
      the current CV; the updated `harness-lab-prompt.md` (never reached the repo).

## Environment

- [ ] **Session-start hook**: start `dockerd` and build the harness-lab sandbox image
      automatically in cloud sessions (today it is manual, see [CLAUDE.md](CLAUDE.md)).
- [ ] **numpy is not installed** (no pip either). Any module that imports it cannot run
      here: `ml-systems/framework` (parts 2-3), CUDA step C. Either install numpy or keep
      those items out of the environment's build queue.
- [x] **`AGENTS.md` → `CLAUDE.md` symlink**, so harnesses that read `AGENTS.md` find the same
      conventions.

## Ready to build, in priority order

1. [ ] **RAG step 0, the evaluation set**: built in
       [`rag-from-scratch/eval-set/`](rag-from-scratch/eval-set/README.md) and audited.
       Next: project 1 (BM25 → LSA → HNSW → fusion).
       Unblocks agent-evals #5, reliability #3 and #5, interview questions 1 and 11.
       → [rag-from-scratch/README.md](rag-from-scratch/README.md)
2. [ ] **harness-lab phase 1**: message types, model interface, scripted backend (spec and
       tests first; the learner writes the loop), then a baseline on 20 tasks x 3 seeds.
       Needs the model API above. → [harness-lab/docs/phase0.md](harness-lab/docs/phase0.md) §5
3. [x] **CUDA step B**: memory system simulated and graded on CPU (coalescing, bank
       conflicts, occupancy, roofline). Landed as `cuda-from-scratch/memory-system/`
       (16 checks, 4 planted bugs). → [cuda-from-scratch/ROADMAP.md](cuda-from-scratch/ROADMAP.md)
4. [x] **web-launch-checklist observers and check.py**, crawler and exercises 1-3 first.
       The crawler observer, `check.py`, the reference in `solutions/`, a runnable
       broken variant and a mutation test all landed.
       → [web-launch-checklist/README.md](web-launch-checklist/README.md)
5. [ ] **ml-systems framework part 2**: convolutions and a CNN, then a transformer trained on
       the framework. **Blocked in this environment:** the framework imports numpy, which is
       not installed (part 3 needs it too). → [ml-systems/framework/README.md](ml-systems/framework/README.md)
6. [ ] **Skill-tree nodes** (38), one at a time, starting from `tree.py next`.
       → [skill-tree/README.md](skill-tree/README.md)
7. [ ] **inference-lab CPU-real projects**: #4 prefix-caching proxy, #13 gateway with
       fallbacks, #3 KV monitor. → [inference-lab/README.md](inference-lab/README.md)
8. [ ] **agent-evals next**: red-team v2 (tool layer, loops) and trajectory grading, both
       after harness-lab phase 1. → [agent-evals/README.md](agent-evals/README.md)
9. [x] **database-from-scratch extension**: MVCC on top of the B+tree and durability for
       MVCC versions in the WAL — both lands (steps 18-19, audited). The engine's remaining
       limits are in the module README §Limits.
       → [database-from-scratch/README.md](database-from-scratch/README.md)
10. [ ] **web-launch-checklist exercises 4-16** and the remaining observers
        (`unfurl.py`, `reader.py`, `mobile.py`, `visit.py`, `impatient.py`).
        → [web-launch-checklist/README.md](web-launch-checklist/README.md)

## Gaps with no plan yet

- [ ] Microservices, authentication protocols (sessions, JWT, OAuth), leader-follower
      replication with failover (from the 25 system-design concepts).
- [ ] CS249r gaps: data selection, network fabrics, responsible and sustainable AI.
- [ ] A checker for `lean-proofs/` (`lake build`, no `sorry`).

## Splitting the work across models

The rule: **put the strongest (most expensive) model where an error would not be caught by
a test, and cheaper models where a verifier catches it.**

| Work | Who |
|---|---|
| Specs, plans, ADRs, design decisions | strongest model |
| Designing a module's `check.py` and its planted bugs (`_build/mutations.py`) | strongest model |
| Reviewing other models' output (sampled) | strongest model |
| Implementing solutions against an existing, mutation-tested checker (skill-tree nodes, observers, templates) | cheaper models |
| Triage of link dumps with the `repo-intake` skill | cheaper models, spot-checked |
| The core the learner must write in LEARN mode | the learner |
| Tutoring: questions, not answers; reviewing the learner's code | strongest model |

Do not assume the split; measure it. harness-lab phase 1 runs the same agent on the same
tasks with each model. With 20 tasks, success rates will rarely be distinguishable (see
[ADR 0004](harness-lab/docs/adr/0004-statistics.md)); cost per solved task (tokens, turns,
euros) will be, and that is the number that decides the split.
