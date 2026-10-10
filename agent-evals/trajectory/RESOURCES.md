# trajectory — resources

What to read before writing the core, restated here so the module stands alone.
Nothing below is copied; each entry says where it comes from and what it means
for this module. Where a claim is from a description rather than code we read,
it says so.

## The correction that defines the project

`agent-evals/README.md`, "Corrections to the original briefs", **#1**: a coding
task has many valid trajectories, so a single deterministic DAG punishes correct
alternatives; grade invariants instead (schema-valid calls, required checks
before risky actions). This module is that correction made executable. It is the
reason the core produces a list of rule violations, not a path score.

## Tool-call schemas

**JSON Schema, 2020-12 — `type`, `required`, `additionalProperties`**
(<https://json-schema.org/draft/2020-12/json-schema-validation>). A tool's
parameters are described by a schema; a call is valid iff its arguments satisfy
it. This module implements the three keywords that catch the classic agent
mistakes: a missing required argument, an argument of the wrong type, and an
extra property the tool does not accept. Restated for the interface:
`required` → "is the key there?", `type` → "is the value the right kind?", and
`additionalProperties: false` → "is there anything we did not ask for?". The one
trap worth naming: in Python, `bool` is a subclass of `int`, so `True` would pass
a naive integer check — it must not.

## What a trajectory is

**OpenTelemetry traces and spans** (<https://opentelemetry.io/docs/concepts/signals/traces/>).
A run is a tree of spans: each span has a name, attributes and a parent. An LLM
or tool call is one span; the trajectory is the spans in order. This module uses
a flattened model — a `Step` is one span (a tool call with its arguments as
attributes and its result) — because phase 1's trajectory is linear. The
"LLM tracing" project in the reliability list (reliability #12) is where the
richer span model would live; defining the linear steps here does not block it.

**Coding-agent trajectories are a linear message log.** SWE-agent
(<https://github.com/SWE-agent/SWE-agent>) and its minimal successor
mini-SWE-agent describe the agent as a `while` loop that appends an assistant
message and a tool result each turn — the same shape as `harness-lab` phase 1.
The `Step` list is that log with the roles flattened. (From the public
descriptions and repositories; not verified line-by-line.)

## Loop detection in coding agents

**OpenHands StuckDetector** and **Aider's repeated-edit / repeated-error
checks** are the two well-known loop guards in open coding agents. Both watch
for a repeated action (the same edit, the same command, the same error) and
break or warn instead of letting the model spin. The lesson for this module:
detect a *repeated identical action*, not "many steps". Restated, the rule is a
run of calls with the same `(tool, arguments)` longer than a small limit. This
module deliberately limits itself to consecutive identical calls; the general
cycle detector is named as out of scope. (Based on the projects' public
descriptions, not read in code.)

## Preconditions and ordering

**Design by contract** (Bertrand Meyer, *Object-Oriented Software Construction*,
ch. 11): an operation has a precondition that must hold before it, and a
postcondition after. A "risky" tool is one with a precondition — read before
write, test before commit — and the violation is a precondition that did not
hold at the call, regardless of whether it holds later. That is why L2 exists:
ordering is the property, not mere occurrence.

## How to verify the contract

- The provided infrastructure tests (`signature`, the default policy) pass
  today: `cd agent-evals && python3.12 -m pytest -q tests/test_trajectory.py`.
- The core tests carry `xfail(raises=NotImplementedError)`: they should report
  `xfailed` now and turn into `xpassed` once the core is written.
- A correct implementation must make every core test pass; a reference was used
  to confirm the contract is satisfiable and that six classic bugs (presence-not-
  order, an off-by-one in the repeat limit, no type check, `additionalProperties`
  ignored, loop detection disabled, schema checks dropped from `grade`) each fail
  at least one test.
