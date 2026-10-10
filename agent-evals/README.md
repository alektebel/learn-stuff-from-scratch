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
| 1 | Trajectory grading engine | **spec + tests** ([trajectory/](trajectory/)) | phase 1 trace format | none | LEARN |
| 11 | Counterfactual replay debugger | not started | = harness-lab `openhands` variant (phase 3) + scripted backend (phase 1) | phase 1 | LEARN, inside harness-lab |
| 7 | Statistical significance engine | **spec + tests** ([stats_engine/](stats_engine/)) | `harness-lab/eval/stats.py`; add bootstrap **over tasks** | none | LEARN |
| 13 | Context-window eviction tester | **spec + tests** ([eviction/](eviction/)) | harness-lab tasks t15/t16/t17/t19, phase 4 | phase 1 | LEARN |
| 4 | CI/CD regression gate | **built** ([ci_gate/](ci_gate/)) | runner + stats; gate on low-variance metrics | — | BUILD |
| 14 | Dataset contamination checker | **spec + tests** ([contamination/](contamination/)) | SWE-bench subset (phase 6) | none | LEARN |
| 3 | Calibrated LLM-as-a-judge | not started | — | source of 500 human labels; single annotator cannot measure agreement | LEARN |
| 12 | Synthetic edge-case generator | not started | task format of harness-lab | model + budget | LEARN |
| 5 | RAG adversarial harness | **spec + tests** ([rag_attack/](rag_attack/)) | rag-from-scratch projects 1-7 (SUT) | none | LEARN |
| 2 | Shadow routing comparator | **built** ([shadow_routing/](shadow_routing/)) | simulated service | — | BUILD |
| 9 | Production drift monitor | **built** ([drift_monitor/](drift_monitor/)) | simulated service, project 1 | — | BUILD |
| 10 | Cost-quality Pareto dashboard | **built** ([pareto/](pareto/)) | run records (tokens, cost) | — | BUILD |
| 6 | Automated DPO flywheel | not started | llm-from-scratch post-training | simulated feedback, GPU for LoRA | mixed |
| 15 | Public methodology teardown | — | everything above | results worth publishing | writing, yours |

The three BUILD projects share one dependency, now built:
**[simulated_service/](simulated_service/)** emits synthetic traffic over time and tenants
with injectable drift and a trace store, deterministic and standard-library only. It is
infrastructure, so it is implemented, not a LEARN core. #2, #9 and #10 run against it.

Five projects now carry a LEARN contract instead of a table row: [**#1**](trajectory/),
[**#5**](rag_attack/), [**#7**](stats_engine/), [**#13**](eviction/) and
[**#14**](contamination/). Each is `<name>/SPEC.md` (the guidelines:
what it is, the interface, acceptance items, limit cases, out of scope), `<name>/RESOURCES.md`
(what to read, cited and restated) and `<name>/<module>.py` with the interface as
`NotImplementedError` stubs, plus `tests/test_<module>.py`. The suite is green with the core
unwritten — infrastructure tests pass, core tests `xfail` — and implementing the stubs turns
the `xfail`s into passes. Run one with `cd agent-evals && python3.12 -m pytest -q
tests/test_<module>.py`.

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

Projects #5, reliability #3 and reliability #5 need a RAG system under test, and it now
exists: [rag-from-scratch/](../rag-from-scratch/README.md) ships projects 1-7 — BM25, LSA, an
**HNSW** vector index (layered small-world graphs, greedy search with `ef`, the
recall/latency trade-off measured against brute force), fusion, metadata-filtered retrieval,
reranking, chunking, a knowledge graph and corrective retrieval, on one shared evaluation set
with abstention. That is the target for the evals; citation-bearing generation (project 8
onward) needs a model, which is now available — projects 1-7 are enough for the retrieval
evals.

### Corrections to the original briefs
- **#1:** a coding task has many valid trajectories; a single deterministic DAG penalises correct
  alternatives. A DAG fits constrained API workflows; for coding, grade invariants (schema-valid
  calls, required checks before risky actions) instead of a path.
- **#4:** a 2 % success-rate threshold is below what 20-70 tasks can detect (harness-lab
  ADR 0004); the gate would block PRs at random. Block on low-variance metrics (cost, latency,
  deterministic regressions); report success as a warning with its interval.
- **#7:** bootstrap must resample **tasks**, not runs; seeds of one task are correlated and
  resampling runs gives intervals that are falsely narrow.
- **#5:** an adversarial harness must attack retrieval offline and report the failure recall
  cannot see — a dropped answer **or** a poison ranked above it — as separate counts, and
  score no-answer probes by abstention, not recall.
