# ADR 0001 — Sandbox: Docker container per run, copy in / copy out

Status: accepted (phase 0)

## Context
Every command an agent runs must execute outside the host (non-negotiable rule). Phase 0 also
needs the verifier to be immune to whatever the agent leaves behind.

## Decision
- One container per run from `harness-lab-sandbox:0` (`sandbox/Dockerfile`): `--network none`,
  `--user agent` (uid 1000), `--cap-drop ALL --cap-add CHOWN`, `no-new-privileges`, memory 2 GB,
  1 CPU, 512 pids.
- The task repo is **copied** in (`docker cp`) and copied out at the end. No bind mounts.
- Every command is wrapped in `timeout -s KILL <t>` inside the container, plus a host-side
  timeout as backstop. Output is capped at 1 MB per stream, with a `truncated` flag.

## Alternatives rejected
- **Bind mount:** faster, but agent writes land on the host and planted symlinks can redirect a
  later host-side step. Rejected for safety; cost is ~1 s per run.
- **bubblewrap now:** lighter, but phase 5 is where it belongs as a *variant* (codex). Using it
  as the base sandbox would make that variant indistinguishable from the baseline.

## Consequences
- `CHOWN` exists only so root can hand `/work` to uid 1000; the agent never holds capabilities.
  Verified by `tests/test_docker.py::test_cannot_escalate`.
- No network means agents cannot `pip install`. Any task needing a dependency must have it baked
  into the image. This is a deliberate restriction of the task space.
- Behind a TLS-intercepting proxy the image build needs the proxy CA (`eval.setup --ca`); runs do not.
