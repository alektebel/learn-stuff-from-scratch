# 12 — 3 AM incident runbook repo

## What it is

A repository of procedures — rollback, scale, drain, failover, diagnose — that a junior
engineer who did not build the system can execute correctly at 3 AM, and that are
**tested**, so you know they still work.

## Say what this is honestly

This is a documentation and testing project. It does not look like the other eleven and
it should not pretend to. That is not a reason to skip it: untested runbooks are the
normal state of the industry, they fail exactly when needed, and fixing that is real
engineering. But go in knowing the deliverable is prose plus a test harness, not a
service.

## You have a large head start in this repo

`deploy-and-debug/` already contains:

- `RUNBOOK.md` — the real `vllm`, `nodetool`, `nvidia-smi` and `kubectl` commands;
- `rollout.py` — liveness vs readiness, canary analysis, budget-based auto-rollback;
- `diagnose.py` — root-cause diagnosis of **11 injected faults from metrics alone**;
- capacity arithmetic and error-budget/percentile material.

The gap is not content. It is that **the procedures are not executed by a test**, and a
procedure that is not executed regularly is a hypothesis.

## What it actually demonstrates

That you build systems others can recover — correct. More precisely: that you know the
constraint at 3 AM is not knowledge, it is **cognitive load under sleep deprivation on an
unfamiliar system**, and that this constraint has design consequences. A runbook written
for the person who built the system is not a runbook.

## The decisions

**Copy-pasteable or explanatory.** A block the responder pastes is fast and is executed
without understanding, so when it half-works they are stranded. An explanation is
understood and is slow, and at 3 AM slow is a cost paid in customer minutes. The workable
form is: the command first, then one line of what it does and how to tell if it worked,
then what to do if it did not. In that order — the responder needs to act before they read.

**Decision points must be checkable, not judged.** "If the database is under heavy load,
scale up" requires a judgement from someone with no baseline. "If `pg_stat_activity` shows
more than 80 active connections, run X" does not. Every branch in the runbook needs a
command that produces the value the branch depends on.

**Every procedure needs a rollback and a verification.** Not "run this", but "run this,
confirm with that, and if it made things worse, this reverses it". A step with no stated
way to tell whether it worked is not a step, it is a suggestion.

**Escalation is a step, not a failure.** Name the condition under which the responder
stops and wakes someone, explicitly, near the top. Without it the default is to keep
trying for two hours.

**Freshness.** A runbook that references a deleted deployment name is worse than none,
because it costs the responder time to discover it is stale. This is what the test harness
is for.

## The testing harness — the part that makes this a project

This is where it stops being a wiki page:

1. **Fault injection.** Reuse the eleven faults in `deploy-and-debug/diagnose.py`, plus
   the ones from whichever project above you deployed. Inject one, unannounced.
2. **Execute the runbook literally.** Not from memory — a script or a person following
   only the text, with no other knowledge. Every command that fails, every reference that
   does not exist, every branch whose condition cannot be evaluated, is a defect logged
   against the runbook.
3. **Time it.** Detection to mitigation. The number is the runbook's quality metric and
   the only one that resists self-assessment.
4. **Run it in CI.** A stale runbook must break a build. Anything less and it rots, which
   is the failure this project exists to prevent.
5. **Game days.** Someone who did not write the runbook, with no warning, on a schedule.
   The observations from the first one will be more useful than the runbook was.

## Where it breaks

The failure that is not in the book. Runbooks cover what has happened before, and the
outage that pages you is disproportionately likely to be new.

So the repository needs a second kind of document that most do not have: not "if X then Y",
but **how to orient** — where the dashboards are, what normal looks like on each one, what
depends on what, how to safely reduce load, how to get a read-only shell, and who owns
each component. That document is what the responder falls back to when the index has no
entry, and writing it is harder and more valuable than adding a twelfth procedure.

## Resources

- `deploy-and-debug/` in this repo, as above. Start by executing its `RUNBOOK.md` literally against a deployment and logging every defect.
- Google SRE Book, ch. 14 *Managing Incidents* and ch. 15 *Postmortem Culture* — <https://sre.google/sre-book/>; and *The Site Reliability Workbook* ch. 9, which is specifically about on-call and includes runbook practice.
- PagerDuty Incident Response documentation — <https://response.pagerduty.com/>. Free, opinionated, and the clearest public description of roles during an incident.
- Allspaw, *Blameless PostMortems and a Just Culture* — <https://www.etsy.com/codeascraft/blameless-postmortems/>
- Woods & Hollnagel, *Resilience Engineering*, for why "the operator made an error" is where an investigation starts rather than where it ends.
- Chaos engineering tooling — LitmusChaos (<https://litmuschaos.io/>) or Chaos Mesh (<https://chaos-mesh.org/>) — for step 1 of the harness on Kubernetes.
