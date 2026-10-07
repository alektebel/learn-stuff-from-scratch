# 3 — PII redaction & unmasking proxy

## What it is

Middleware on the path to an LLM that finds PII in the outbound request, replaces it with
placeholders, forwards the modified request, and substitutes the real values back into the
response before returning it.

## What it actually demonstrates

The original claim is that this shows you understand HIPAA and SOC 2. It does not.
Neither framework contains a control called "redaction proxy", and no auditor will accept
one as evidence of anything by itself.

What building it honestly demonstrates is more useful and harder to fake:

1. **Redaction is lossy in a way that matters.** Replace "Maria Sanchez" with `<PERSON_1>`
   and the model can no longer reason about gender agreement, name-based disambiguation,
   or anything else it would have used the name for. You are trading capability for
   exposure, and the exchange rate is measurable — so measure it.
2. **The unmask map is a PII database.** It holds the original values, keyed by request.
   It needs encryption at rest, a retention policy, access control, and an entry in
   whatever data inventory you maintain. You did not eliminate the PII; you concentrated
   it into a new system with a shorter security review history than the one you were
   protecting.
3. **Detection has false negatives, and you cannot enumerate them.** This is the part that
   separates a demo from an argument.

Say those three things in your README and this project is worth more than the version
that claims compliance.

## The substrate

**Microsoft Presidio**, not a regex file. Presidio splits detection (Analyzer: spans,
entity types, confidence scores) from transformation (Anonymizer: operators such as
`replace`, `mask`, `redact`, `hash`, `encrypt`).

Two things about it worth internalising:

- Presidio does **pseudonymisation**, not anonymisation, in almost every configuration.
  Replacing a name with a stable label is reversible by definition — that is what makes
  your unmasking possible, and it is also what stops the output being anonymous data.
- The `encrypt` operator is reversible with a key, which gives you a round trip without a
  separate mapping store. That moves the problem from "protect a database" to "protect a
  key", which is a better problem but not no problem.

Use real text with real names for testing. Presidio's failure modes on a synthetic
corpus you wrote are not its failure modes.

## The decisions

**Placeholder format.** `<PERSON_1>` versus a plausible fake name ("John Doe"). The
placeholder is unambiguous to unmask and out-of-distribution for the model, which
degrades output quality and sometimes triggers refusals. A fake name keeps the model in
distribution and makes unmasking ambiguous the moment the model generates a *different*
name that collides. Pick one, then measure the quality difference — that measurement is
the most valuable artefact this project produces.

**Consistency scope.** Does the same person get the same placeholder across a
conversation? Within one request is easy. Across a session, you need a per-session map
that lives as long as the session and is itself PII. Across users, never — a shared map
lets one user's placeholder resolve another's data.

**Streaming.** The model streams tokens back. `<PERSON_1>` may arrive split across two
chunks. Either buffer until you can match placeholders (killing time-to-first-token) or
implement a partial-match state machine at the chunk boundary. There is no third option
and most implementations quietly get this wrong.

**Fail-open or fail-closed.** Presidio is down or times out. Do you forward the request
unredacted, or refuse it? Fail-open makes the proxy a suggestion; fail-closed makes your
availability equal to Presidio's. Decide, document, and make it configurable per
entity type if you want the answer to be defensible.

## Where it breaks

PII that is not an entity. "The patient who came in on the 3rd after the bridge closure"
identifies a person in a town of 4,000 and contains no name, no number, no address.
Detection-based redaction cannot see it, and no amount of tuning changes that — it is a
property of the approach, not of the tool.

Write that limitation down and quantify what you can: run your proxy over a corpus,
measure the recall of the detector on the entities it *does* claim, and report it. A
number with a stated scope beats a claim of compliance.

## Resources

- Microsoft Presidio — <https://microsoft.github.io/presidio/> `[v]`, source <https://github.com/microsoft/presidio> `[v]`. Read the FAQ on anonymisation vs pseudonymisation, and the operator reference for `encrypt`.
- HHS guidance on HIPAA de-identification (Safe Harbor's 18 identifiers, and the Expert Determination route) — <https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html>. Note that Safe Harbor is a *list*, and your detector's job is a strict subset of it.
- NIST SP 800-188, *De-Identifying Government Data Sets*. The clearest public treatment of why re-identification risk is not eliminated by removing identifiers.
- Sweeney, *k-anonymity*, IJUFKS 2002 — the original demonstration that quasi-identifiers re-identify people. Directly relevant to the "where it breaks" section.
- `contextcite/` in this repo — if you want to measure how much a redaction changed the model's answer, attribution over ablated context is a ready-made method.
