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

## Second list (LLM reliability), merged

A second fifteen-project list overlaps the first almost entirely. Mapping, so nothing is built twice:

| Reliability list | Same as | Notes |
|---|---|---|
| 1 LLM regression test suite (blocks CI) | #4 CI gate | same caveat: gate on low-variance metrics |
| 2 Trajectory grading engine | #1 | |
| 3 RAG retrieval benchmark (hit rate, MRR, NDCG, no-answer queries) | extends #5 | needs a RAG system: see below |
| 4 Judge calibration | #3 | |
| 5 Hallucination spike monitor | #9 drift monitor + faithfulness | needs RAG citations to check |
| 6 Shadow traffic comparator | #2 | |
| 7 Chaos suite for agents (timeouts, malformed tool outputs, overflow) | #8 v2 | needs harness-lab tool layer |
| 8 **Cost and latency guardrail middleware** | new | per-request token budgets, kill switch, anomaly alerts; harness-lab already enforces wall/step budgets per run |
| 9 Golden dataset flywheel | capture half of #6 | without the fine-tune |
| 10 Fallback chain validator | inference-lab #13 | |
| 11 Prompt and config regression gate | #4 | prompts versioned as config |
| 12 **Distributed tracing for LLM hops** | new, base of #1 and #11 | OpenTelemetry-style spans; define it with harness-lab phase 1's trace format, not after |
| 13 **SLO and error-budget dashboard** | new | error-budget math exists in `deploy-and-debug/` |
| 14 Injection and jailbreak fuzzer | #8 (v1 done) | |
| 15 Public reliability report | #15 | |

Net new: three projects (cost guardrail middleware, LLM tracing, SLO dashboard) and one dependency.

## The RAG dependency

Projects #5, reliability #3 and reliability #5 need a RAG system under test, and the repo has
none. Planned in [rag-from-scratch/](../rag-from-scratch/README.md), built before them: chunking; BM25; an **HNSW** vector index
from scratch (layered small-world graphs, greedy search with `ef`, the recall/latency trade-off
measured against brute force); hybrid retrieval; citation-bearing answers; abstention. It is a
target for the evals and a learning project on its own.

### Corrections to the original briefs
- **#1:** a coding task has many valid trajectories; a single deterministic DAG penalises correct
  alternatives. A DAG fits constrained API workflows; for coding, grade invariants (schema-valid
  calls, required checks before risky actions) instead of a path.
- **#4:** a 2 % success-rate threshold is below what 20-70 tasks can detect (harness-lab
  ADR 0004); the gate would block PRs at random. Block on low-variance metrics (cost, latency,
  deterministic regressions); report success as a warning with its interval.
- **#7:** bootstrap must resample **tasks**, not runs; seeds of one task are correlated and
  resampling runs gives intervals that are falsely narrow.
