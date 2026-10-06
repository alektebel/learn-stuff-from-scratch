# Phase 0 — closing report

## 1. What was built
- Docker sandbox: no network, uid 1000, no capabilities, copy in/out, per-command kill timeout (ADR 0001).
- Verifier in a fresh container, hardened against planted `sitecustomize.py`, `conftest.py` and
  `pytest.ini`; each of those was checked to fool a naive verifier first (ADR 0002).
- Runner: agent in a killable child process, wall-clock budget, validated JSONL records (ADR 0003).
- Statistics: Wilson intervals, exact McNemar, paired power analysis (ADR 0004).
- 20 tasks across six categories, four with generated repos up to 1.8 MB / 5 MB of log (index: `eval/tasks/README.md`).
- Control agents `null` and `oracle` (ADR 0005). 102 tests, all green.

## 2. Results (git 170b44e, 20 tasks x 3 seeds)

| agent | success | 95% CI (runs) | stop reasons | median wall |
|---|---|---|---|---|
| null | 0/60 = 0.0 % | [0.0, 6.0] | no_op: 60 | 0.73 s |
| oracle | 60/60 = 100.0 % | [94.0, 100.0] | completed: 60 | 0.94 s |

Raw records: `eval/results/phase0-null.jsonl`, `eval/results/phase0-oracle.jsonl`.
Closing criterion met: the null agent scores 0 % with valid records on the whole suite, and the
oracle proves every task passable. There is no previous phase to compare against.

## 3. ADRs
0001 sandbox · 0002 task format and verifier · 0003 run record · 0004 statistics · 0005 controls
and scripted model.

## 4. Open decisions and risks
- **Budget and base model are unset.** Phase 1 cannot run a single real evaluation without them.
- **Statistical power (ADR 0004):** 20 tasks detect no plausible success-rate difference; 70
  tasks detect roughly 15-20 points. Cost metrics have to carry most of phase 6.
- **Mechanism coverage gap (amendment 2):** no task yet triggers concurrency batching
  (claude_code), parallel tools (codex), steer/followUp queues (pi), resume-after-restart
  (opencode), permissions/sandbox policy, subagents, deferred tool loading or prompt caching.
  Most of these move cost, latency or safety rather than success, so they need cost-sensitive or
  adversarial tasks (e.g. a task whose obvious command is destructive), not more bug fixes.
- **Paper unread:** arXiv is unreachable from this environment and the paper is newer than the
  builder's knowledge. Every variant card will say "not verified" until the PDF is provided.
- **Recall tasks deliver earlier turns as data**, not as a live conversation. How an agent replies
  to them is the agent's design; phase 1 has to define it.
- The top-level package is named `eval`, as in the plan; installed outside a venv it would
  collide with any other package of that name.

## 5. Proposal for phase 1 (not started)
Spec and tests first (LEARN mode), human implements:
1. `harness_lab/llm`: the message types and a model interface; a **scripted backend** that
   replays recorded responses with token usage (amendment 5), plus one real transport.
2. `harness_lab/core`: the linear `while` loop with a single bash tool through `DockerSandbox.exec`,
   unpruned history, step and cost limits mapped to `stop_reason`.
3. An `eval` adapter exposing it to the runner as agent `mini`.
4. Closing: baseline `mini` on 20 tasks x 3 seeds with the chosen model, against the null/oracle brackets.
