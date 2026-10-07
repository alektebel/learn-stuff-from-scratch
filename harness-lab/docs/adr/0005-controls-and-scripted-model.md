# ADR 0005 — Control agents now, scripted model backend in phase 1

Status: accepted (phase 0)

## Decision
Phase 0 ships two control agents instead of a scripted LLM backend:
- `null`: never acts. Must score 0 % (else a verifier passes on the initial repo).
- `oracle`: writes the reference solution **through the sandbox API**. Must score 100 % (else a
  task is unpassable, or the sandbox write path is broken).

A real agent's rate is only interpretable between these brackets. The original closing criterion
(null = 0 %) alone cannot tell "the agent failed" from "the task is impossible".

## Deviation from amendment 5
Amendment 5 put the scripted model backend in phase 0. It is deferred to phase 1: a scripted
backend has to replay *messages*, and the message and LLM interfaces are the human's design work
in phase 1 (LEARN mode). Defining them here, to serve a test, would decide that design for them.
The phase 1 spec will include the scripted backend's interface and its tests.
