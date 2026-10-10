# trajectory — grade a coding agent's trajectory by invariants (LEARN mode)

## What it is

A small, dependency-free **grader for an agent trajectory**. Given an ordered
list of steps (tool calls and their results) and a policy, it reports which
rules the trajectory broke: schema-invalid calls, a risky action with no
prerequisite before it, an identical-call loop, or an over-long run.

It is the grading half of project #1. The original brief wanted a fixed
expected DAG per task; that penalises the many correct but different paths a
coding agent can take. This module grades **invariants** instead — properties
every acceptable trajectory satisfies — so alternative orders pass and only
real violations are reported. See the correction in
[../README.md](../README.md).

Everything is standard library and deterministic: no numpy, no network, no
model calls, and no dependence on Python's salted `hash()`.

## What it demonstrates

- **Invariants beat a golden path.** A trajectory that reads an extra file, or
  asks its independent questions in a different order, is still correct and must
  not be flagged (L1); one that runs the prerequisite *after* the action it
  guards is not (L2).
- **Ordering is the whole point of a prerequisite.** "The read happened" is not
  enough; it has to happen first.
- **A loop that reaches "success" is still a loop.** Grading only the final
  message, or only the last few steps, misses it (L3).
- **Schema validation is more than the key is present.** Wrong types (L4) and
  forbidden extra properties (L5) are violations a presence-only check misses.
- **A verdict carries a reason.** Every violation names the rule, the step and
  the detail, so a caller can act instead of guessing.

## The interface

Module: `agent-evals/trajectory/trajectory.py`, imported as
`trajectory.trajectory`. Constants: `SCHEMAS`, `RISKY`, `DEFAULT_POLICY`.

```python
Step(tool, arguments={}, result="", exit_code=None, text="")
    # tool is None => a plain assistant message (the usual end of a run)
Policy(schemas, risky, max_identical_repeats=3, max_steps=50)
Violation(rule, step, detail)
Report(ok, violations, counts)

# the default tools the tests and DEFAULT_POLICY use
SCHEMAS = {"read_file": {...}, "write_file": {...},
           "run_tests": {...}, "git_commit": {...}}
RISKY   = {"write_file": ("read_file",), "git_commit": ("run_tests",)}
DEFAULT_POLICY = Policy(schemas=SCHEMAS, risky=RISKY)

# implemented infrastructure (tests may rely on it now)
signature(step) -> tuple | None            # (tool, frozen arguments); key order ignored

# core the learner writes (NotImplementedError until then)
validate_call(schema, arguments) -> list[str]
prerequisite_violations(trajectory, policy=DEFAULT_POLICY) -> list[Violation]
repeat_violations(trajectory, policy=DEFAULT_POLICY) -> list[Violation]
grade(trajectory, policy=DEFAULT_POLICY) -> Report
```

Contracts the stubs must satisfy once implemented:

- `validate_call` — a schema is `{"required": [...], "types": {key: name},
  "additional": bool}`. Problems, in this order: `missing required '<k>'` for
  each required key absent; `'<k>' must be <name>` for each present key whose
  type is wrong (`str`, `int`, `bool`, `number`, `dict`, `list`; a `bool` is not
  an `int` or a `number`); `unexpected '<k>'` (sorted) for each key outside
  `required ∪ types` when `additional` is `False`. Empty list means valid.
- `prerequisite_violations` — one `Violation("missing_prerequisite", i, ...)`
  for a risky call at step `i` iff none of `policy.risky[tool]` appeared at a
  step `< i`. An empty prerequisite tuple imposes nothing; a call never
  satisfies its own prerequisite.
- `repeat_violations` — one `Violation("repeat_loop", i, ...)` for the step
  where a run of consecutive calls with the same `signature` first exceeds
  `policy.max_identical_repeats`. A plain message (`tool is None`) breaks a run;
  a run emits at most one violation.
- `grade` — the union of the above plus one `Violation("schema", i, "; ".join(problems))`
  per step whose tool has a schema and fails `validate_call`, plus one
  `Violation("step_budget", len(trajectory), ...)` when the trajectory is longer
  than `policy.max_steps`. `counts` maps each tool name to its call count;
  violations are sorted by `(step, rule)`; `ok` is true iff there are none.

## Acceptance items

- **A1** `validate_call` accepts a valid call and reports a missing required
  key, a wrong type, and (when `additional` is `False`) an extra key.
- **A2** `prerequisite_violations` is empty when the prerequisite ran earlier
  and non-empty when it did not.
- **A3** `repeat_violations` is empty for a run at the limit and flags a longer
  run once.
- **A4** `grade` flags a trajectory longer than `policy.max_steps`.
- **A5** `grade` returns `ok=True`, no violations and correct `counts` for a
  clean trajectory, and a stable `(step, rule)` order otherwise.

## Limit cases

- **L1** A valid alternative order (an extra read, independent steps swapped)
  passes — a fixed-path grader would reject it.
- **L2** The prerequisite appears, but after the risky action: still a
  violation.
- **L3** An identical-call loop followed by a "done" message is still flagged.
- **L4** A present-but-wrong-typed argument is a schema violation.
- **L5** A forbidden extra property is a schema violation.

## Out of scope

- Grading *semantic* correctness (did the patch fix the bug); that is the
  verifier's job (`harness-lab/eval/verify.py`).
- Emitting trajectories: this reads a list of `Step`s. A `from_record` reader
  for the phase-1 run record or a future span format is a separate change.
- Cost/latency grading; those live in the runner and `eval/stats.py`.
- Detecting non-consecutive cycles (`A,B,A,B,A,B`); only runs of the identical
  call are graded here.
