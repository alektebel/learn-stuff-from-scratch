# harness-lab

A coding-agent harness built from scratch, organised around the seven subsystems of *Harness
Engineering: Anatomy, Architecture, and Evolution of Coding Agents* (arXiv 2609.00006), with the
distinctive mechanism of each harness in the paper as a swappable variant, and a controlled
experiment comparing them. The full plan, rules and phases are in [CLAUDE.md](CLAUDE.md).

**Status: phase 0 closed, phase 1 spec shipped** — evaluation bench plus the
phase-1 contract (message/model interfaces, scripted backend, the learner's loop
stub and its tests). The real baseline is blocked on the model API and cost cap.
See [docs/phase0.md](docs/phase0.md) and [docs/phase1.md](docs/phase1.md).

```
python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m eval.setup                 # build the sandbox image (needs Docker)
.venv/bin/python -m pytest -q                  # Docker tests skip without a daemon
.venv/bin/python -m pytest -q tests/test_llm.py tests/test_loop.py
.venv/bin/python -m eval.runner --agent oracle --tasks all --seeds 0 --out eval/results/x.jsonl
.venv/bin/python -m eval.report eval/results/x.jsonl
.venv/bin/python -m eval.stats power           # what the suite can and cannot detect
```

| Path | What |
|---|---|
| `eval/sandbox.py` | Docker sandbox: no network, uid 1000, no capabilities, copy in/out |
| `eval/verify.py` | hidden tests in a fresh container, hardened against planted files |
| `eval/runner.py` | agent × task × seed, agent in a killable child process, JSONL records |
| `eval/contract.py` | what an agent receives and reports; record schema and validation |
| `eval/stats.py`, `eval/report.py` | Wilson intervals, exact McNemar, power, summaries |
| `eval/agents.py` | control agents `null`/`oracle` and the `mini` adapter to the phase-1 loop |
| `eval/tasks/` | the 20 tasks ([index](eval/tasks/README.md)) |
| `docs/adr/` | decisions 0001–0005 |
| `harness_lab/llm/` | phase 1: message types, model interface, scripted backend |
| `harness_lab/core/` | phase 1: the loop stub (`run_loop`) the learner implements |
| `docs/phase1.md`, `RESOURCES.md` | the phase-1 contract and reading list |
