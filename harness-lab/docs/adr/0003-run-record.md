# ADR 0003 — Run record and who measures what

Status: accepted (phase 0)

## Decision
One JSON line per (agent, task, seed), schema in `eval/contract.py`, validated before it is
written and again when read. `SCHEMA_VERSION` bumps on any field change.

- **The agent reports** what only it can see: turns, input/output/cached tokens, cost, tool
  calls, stop reason, free-form `extra`.
- **The runner measures** what the agent must not be trusted with: wall time and success.
- `cached_tokens` is a subset of `input_tokens` (validated), so cache hit rate = cached / input.
- `stop_reason` is a closed set. `wall_timeout` and `crash` are set only by the runner.

## Agent process
Each run's agent executes in a child process (spawn). Python cannot kill a thread blocked in an
HTTP call or a student's infinite loop; it can kill a process. Tested by
`test_wall_timeout_kills_agent` and `test_crash_is_recorded`.

## Consequences
- Agents and their results must be picklable.
- An infrastructure failure (Docker down, image missing) produces **no record** and a non-zero
  exit, never a fake "fail" record that would bias success rates downwards.
- Records carry `git_sha` with a `-dirty` suffix. Results from a dirty tree are not citable.
