# 11 — Shadow traffic evaluator

## What it is

A fraction of live production traffic duplicated to a candidate model, with the candidate's
responses recorded and compared against the incumbent's, and no effect whatsoever on what
users receive.

## What it actually demonstrates

That you can upgrade models in production safely — correct. The mirroring itself is not
the demonstration; Envoy and Istio do it in a few lines of configuration. The
demonstration is in the three things around it: **what you compare**, **what you do about
the data**, and **what you do when the candidate is different but not worse**.

## The substrate

Mirroring at the proxy, not in your application:

- **Envoy** — `request_mirror_policies` on a route, with a mirror fraction. Envoy sends
  the mirrored request fire-and-forget and discards the response, and appends `-shadow` to
  the `Host` header so the shadow target can tell. That header suffix is useful: make your
  candidate service reject anything without it, and a misconfiguration becomes an error
  rather than a silent double-charge.
- **Istio** — `VirtualService` with `mirror` and `mirrorPercentage: value: 5.0`. If the
  field is absent, **all** traffic is mirrored, which is a footgun worth knowing about
  before you deploy it.

For scoring, an LLM judge plus deterministic checks. Do not use only a judge.

## The decisions

**This is a data-processing change, and the guide the project came from does not say so.**
You are sending customer data to a model that was not covered when the customer signed.
In a real enterprise that is a DPA question, possibly a sub-processor notification, and in
some sectors a blocker. Options: mirror only from consenting tenants, mirror only
synthetic or already-public traffic, or get the paperwork. Pick one deliberately — this is
the difference between the project as an exercise and the project as something you could
actually run.

**Fire-and-forget means the shadow can lie.** The mirrored request has no response path,
so a shadow service that is silently erroring produces no signal — it just produces fewer
records. Instrument the *ratio* of shadow responses to shadow requests, and alert when it
drops. Otherwise your "the candidate looks fine" conclusion is drawn from the requests it
happened to survive.

**Side effects.** If the mirrored path writes to a database, sends an email, charges a
card, or calls a tool, you have duplicated the side effect on 5% of production. The
candidate must run against isolated state, with every outbound integration stubbed. This
is the single most dangerous part of the project and the reason mirroring is usually
limited to read paths.

**What you compare.** Exact-match is nearly always 0% and tells you nothing. The useful
comparisons, in increasing cost:

| Comparison | What it catches |
|---|---|
| Latency, token count, error rate, refusal rate | Regressions that are not about quality at all, and most real ones |
| Deterministic assertions (valid JSON, schema conformance, tool-call validity) | Structural breakage — the cheapest high-value signal |
| Embedding similarity to the incumbent | Drift, but "different" is not "worse" and this cannot tell them apart |
| Pairwise LLM judge | Actual preference, with position bias, verbosity bias, and self-preference to control for |
| Human review of a sample | The ground truth you calibrate the judge against |

Build in that order. Most decisions are made correctly on the first two rows and people
skip straight to the fifth.

**Cost.** 5% mirroring costs 5% more inference, on the model you have not committed to.
For a large candidate that is not negligible, and someone will ask.

## Where it breaks

The candidate is better on your metrics and worse in production, because your traffic
sample is not representative. You mirrored 5% uniformly at random, and the cases that
matter — the long tail, the enterprise tenant with the unusual schema, the 2 AM batch —
are a much smaller fraction of requests than they are of value.

Stratify the sample by tenant, by request type, and by whatever dimension your business
cares about, and report per-stratum. A single aggregate number over mirrored traffic is
the failure mode this project exists to avoid.

## Resources

- Envoy route configuration, `request_mirror_policies` — <https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/route/v3/route_components.proto> `[v]`
- Istio traffic mirroring task — <https://istio.io/latest/docs/tasks/traffic-management/mirroring/> `[v]`
- Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*, NeurIPS 2023 — [2306.05685](https://arxiv.org/abs/2306.05685). The source for position and verbosity bias in judges, and for how to correct them. Read it before you trust a judge score.
- Kohavi, Tang, Xu, *Trustworthy Online Controlled Experiments*, CUP 2020 — for what shadowing can and cannot substitute for an experiment.
- `deploy-and-debug/rollout.py` in this repo — canary analysis and budget-based auto-rollback, which is the step after this one.
