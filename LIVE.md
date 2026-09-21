# LIVE — the thing that is running while you learn

A second track that runs **in parallel from week 1**, not a phase at the end.
About **2 hours a week**, standing, like Lean and the AWS drill.

## Why parallel, and not later

I originally put this at week 12. That was wrong, and the arithmetic is the
whole argument:

| Live system starts | 90 days of uptime by |
|---|---|
| **Week 1** — 24 Aug | **22 Nov 2026** |
| Week 12 — 9 Nov | 7 Feb 2027 |

The plan ends 27 Dec (18 weeks) or 21 Feb (26 weeks). Starting at week 12
produces the evidence **after the plan is over**. There is no way to compress
this: ninety days takes ninety days, and it is the only requirement in the whole
project that a burst of effort cannot buy.

Four more reasons, in descending order of how much they matter:

1. **You cannot schedule an incident.** A postmortem is the single most
   convincing artifact you can hold, and the only way to get one is to run
   something long enough for it to break on its own.
2. **The feedback loop runs the right way round.** Building a scheduler in week
   4 is a different experience if you have already watched your own requests
   queue up. The motivation arrives before the mechanism instead of after it.
3. **Cost stops being theoretical.** Week 1 teaches you crossovers; a real
   monthly bill teaches you which line items *you* generate. Those are not the
   same lesson.
4. **It de-risks everything.** If the plan slips — and it will — you still have
   a running system and its artifacts. Evidence that accrues by the calendar
   survives a schedule that does not.

## Week 1 — get *anything* up · ~3 h

**The model does not matter yet.** What has to start is the clock.

- [ ] Phase 0 of [`RUNBOOK.md`](week-12/aws-deploy/RUNBOOK.md) — root MFA, a
      **tested** budget alarm, IAM Identity Center, no long-lived keys.
- [ ] A public URL that returns something. `return {"reply": "hello"}` is fine.
      This is not a cop-out: the operational surface is the subject, and a
      placeholder payload lets you build it before you have a model.
- [ ] A health endpoint that reports **unhealthy**, not merely alive.
- [ ] One dashboard with four numbers: request rate, p99, error rate, cost/day.
- [ ] An alert that reaches your phone.
- [ ] **Write down the date.** It is the start of the uptime record and it is
      the number you will quote in an interview.

**Done means:** a URL a stranger can hit, an alarm you have tested by tripping
it, and a start date.

## Week 3 — swap in your own model · ~2 h

By the end of week 2 you have a transformer you wrote yourself
([`llm-from-scratch/`](week-02/llm-from-scratch/)). Tiny, CPU-only, costs
almost nothing to serve.

- [ ] Replace the placeholder with `sample.py` behind the same endpoint.
- [ ] **Record TTFT and tokens/sec now.** Every later week improves this number
      and you want the before.

There is something worth noticing here: the artifact is a model you wrote from
scratch, on infrastructure you are learning from scratch. Almost nobody applying
for these roles can say that.

## Then each week feeds it

| Wk | What you learn | What it changes in the live system |
|---|---|---|
| 1 | `aws-from-scratch` | IAM roles, artifact bucket, the billing alarm |
| 2–3 | `llm-from-scratch` | your model becomes the payload |
| 3 | `context-caching` | add a KV cache. **Measure TTFT before and after** |
| 4 | `inference-from-scratch` | replace the naive server with your own scheduler; run `traffic.py` against production and find the knee |
| 4 | `deploy-and-debug` | the four-number dashboard becomes a real one; set an error budget |
| 9–11 | `database-engine`, `raft` | persistence, and a considered answer to what happens when it restarts |
| 12 | `aws-deploy` | formalise: IaC, containers, k8s, and the rebuild-from-empty test |
| 16 | `cuda-from-scratch` | only if you ever put it on a GPU |

**Weeks 5–8 and 13–18 feed it very little**, and that is fine — during those it
just runs, accumulating the one thing you cannot buy. Two hours a week of
looking at the dashboard and reading the bill.

## The evidence, with dates

| Artifact | Earliest possible | Notes |
|---|---|---|
| Uptime record | **22 Nov** | 90 days from week 1 |
| Load test with a number | week 4 | against your own stack *and* vLLM later |
| A written postmortem | whenever it breaks | if nothing breaks by week 14, **break it deliberately** — OOM it, exhaust the KV cache, saturate the queue — and write that up instead |
| Cost record | week 4 | monthly, per-request, and the one change that halved it |
| The vLLM comparison | week 12 | owed since week 4 |

## Keep it cheap

- **Small model, CPU, one small always-on instance.** Serverless is cheaper at
  low traffic but the cold start is real and it will show up in every latency
  number you quote — measure it and decide deliberately rather than by default.
- **Check the bill weekly, not monthly.** The free tier expires twelve months
  after you open the account, on a date you will not be watching for.
- Whatever it costs, that number is an artifact too. "I ran this for six months
  for $9 a month, and here is the change that took it from $19" is a better
  answer than most people have.

## The one rule

**If it goes down and you do not notice, the alarm is the thing that is broken.**
Fix that before you touch anything else. An uptime record you are not measuring
is not an uptime record.

---

[Roadmap](ROADMAP.md) · [Runbook](week-12/aws-deploy/RUNBOOK.md) · [TODO §16](TODO.md)
