# learn-stuff-from-scratch

From-scratch implementations for learning. Read `PHILOSOPHY.md` first: name design
decisions, build the MVP and then the limit cases that break it, verify with checks
you can run.

## Conventions

- A graded module is templates + `check.py` + `solutions/` + `_build/` (hints and planted
  bugs). How to build one: `.claude/skills/graded-module/SKILL.md`. Canonical examples:
  `database-from-scratch/`, `ml-systems/framework/`.
- New material (links, project lists, books, courses) and "does the repo cover X?":
  `.claude/skills/repo-intake/SKILL.md` (coverage script included).
- The math / pattern-recognition curriculum is a dependency graph in `skill-tree/`; work on
  it with `.claude/skills/skill-tree-worker/SKILL.md`. Modules land in `math/`.
- `harness-lab/` has its own `CLAUDE.md` (LEARN mode: Claude writes specs, tests and
  infrastructure; the learner writes the core).
- Learning content is never copied from books or courses: cite and restate.
- No model identifiers in commits, code or docs.

## Running things

- Most modules: `cd <module> && python3 check.py`. numpy is available to `python3`.
- `harness-lab/` and `agent-evals/` need Docker. In a cloud session start the daemon with
  `dockerd &`, then build the sandbox image with
  `harness-lab/.venv/bin/python -m eval.setup` (add `--ca /root/.ccr/ca-bundle.crt` behind
  the session proxy). Each has its own `.venv` (Python 3.12).
- Skill tree: `python3 skill-tree/tree.py check` / `next`.
