# harness-lab

A coding-agent harness built from scratch, organised around the seven subsystems of *Harness
Engineering: Anatomy, Architecture, and Evolution of Coding Agents* (arXiv 2609.00006), with the
distinctive mechanism of each harness in the paper as a swappable variant, and a controlled
experiment comparing them. The full plan, rules and phases are in [CLAUDE.md](CLAUDE.md).

**Status: phase 0 closed** — evaluation bench only, no agent yet. See [docs/phase0.md](docs/phase0.md).

```
python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m eval.setup                 # build the sandbox image (needs Docker)
.venv/bin/python -m pytest -q                  # 102 tests; Docker ones skip without a daemon
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
| `eval/agents.py` | control agents: `null` (must be 0 %) and `oracle` (must be 100 %) |
| `eval/tasks/` | the 20 tasks ([index](eval/tasks/README.md)) |
| `docs/adr/` | decisions 0001–0005 |
| `harness_lab/` | empty package skeleton for phases 1–7 |
