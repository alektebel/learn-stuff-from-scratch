# agent-evals

Evaluation, safety and operations tooling for agents, built as a layer **on top of
[harness-lab](../harness-lab/)**: projects consume its sandbox, runner, statistics and (from
phase 1 on) its trajectories, instead of rebuilding them. Projects that need production traffic
run against a simulated service with synthetic traffic and deliberately injected drift: they
teach the mechanics, and their numbers say nothing about real production.

## The fifteen projects

Mode is decided per project (LEARN: spec and tests by Claude, core by you; BUILD: Claude
implements). The column below is a **proposal to confirm** project by project.

| # | Project | Status | Builds on / overlaps | Blocked by | Proposed mode |
|---|---|---|---|---|---|
| 8 | Agent red-team fuzzer | **v1 done** ([redteam/](redteam/)) | harness-lab sandbox, verifier | v2 needs tools + loop (phase 1-2) | BUILD (eval infra) |
| 1 | Trajectory grading engine | not started | phase 1 trace format | harness-lab phase 1 | LEARN |
| 11 | Counterfactual replay debugger | not started | = harness-lab `openhands` variant (phase 3) + scripted backend (phase 1) | phase 1 | LEARN, inside harness-lab |
| 7 | Statistical significance engine | partly exists | `harness-lab/eval/stats.py`; add bootstrap **over tasks** | none | LEARN |
| 13 | Context-window eviction tester | partly exists | harness-lab tasks t15/t16/t17/t19, phase 4 | phase 1 | LEARN |
| 4 | CI/CD regression gate | not started | runner + stats; gate on low-variance metrics | a baseline to regress from | BUILD |
| 14 | Dataset contamination checker | not started | SWE-bench subset (phase 6) | none | LEARN |
| 3 | Calibrated LLM-as-a-judge | not started | — | source of 500 human labels; single annotator cannot measure agreement | LEARN |
| 12 | Synthetic edge-case generator | not started | task format of harness-lab | model + budget | LEARN |
| 5 | RAG adversarial harness | not started | needs a RAG system under test; none exists in the repo | a RAG target | LEARN |
| 2 | Shadow routing comparator | not started | simulated service | simulated service | BUILD |
| 9 | Production drift monitor | not started | simulated service, project 1 | simulated service | BUILD |
| 10 | Cost-quality Pareto dashboard | not started | run records (tokens, cost) | real runs with cost | BUILD |
| 6 | Automated DPO flywheel | not started | llm-from-scratch post-training | simulated feedback, GPU for LoRA | mixed |
| 15 | Public methodology teardown | — | everything above | results worth publishing | writing, yours |

### Corrections to the original briefs
- **#1:** a coding task has many valid trajectories; a single deterministic DAG penalises correct
  alternatives. A DAG fits constrained API workflows; for coding, grade invariants (schema-valid
  calls, required checks before risky actions) instead of a path.
- **#4:** a 2 % success-rate threshold is below what 20-70 tasks can detect (harness-lab
  ADR 0004); the gate would block PRs at random. Block on low-variance metrics (cost, latency,
  deterministic regressions); report success as a warning with its interval.
- **#7:** bootstrap must resample **tasks**, not runs; seeds of one task are correlated and
  resampling runs gives intervals that are falsely narrow.
