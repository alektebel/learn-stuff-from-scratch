# RESOURCES — context-window eviction & compaction

Read with a purpose: each entry says why it matters here. Everything is restated in our
own words — cited, never copied. `[v]` = confident it exists as described; `[verify]` =
written from memory, confirm before relying on it.

## Compaction in practice

- **"Effective context engineering for AI agents"** — Anthropic engineering blog (2025).
  [v] <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
  Why: it frames the context window as a *finite resource with a budget* (the idea behind
  `Context.budget`) and names **compaction** — summarise the older part of the session and
  restart from the summary — as the standard answer, which is exactly the `"summarise"`
  policy implemented here.

- **Provider docs on context editing / memory tools.** [verify]
  Why: production agents do not only summarise — they *clear* old tool results and keep a
  persistent note outside the window. That note is a constraint that survives every
  eviction; our `pin=` predicates are the deterministic stand-in for it.

- **"Context rot" / long-context degradation measurements.** [verify]
  Why: eviction is dangerous not only because tokens vanish but because recall degrades
  for what remains near the edges; this motivates testing *what survives* (via
  `keeps_constraint` and the scripted model) rather than only the byte count.

## The audit trail (provenance)

- **harness-lab's compaction-targeted tasks: `t15-session-constraint`,
  `t16-superseded-instruction`, `t17-large-repo`, `t19-huge-log`**, tabled in
  `../../harness-lab/eval/tasks/README.md`; compaction-with-provenance is enmienda 4 of
  `../../harness-lab/CLAUDE.md` (fases 2 y 4). [v]
  Why: t15 is this project's question verbatim — recalling a session constraint across a
  long session under compaction — and t19 forces truncation of huge tool output; the
  enmienda requires every summary to record which messages and facts it came from, which
  is exactly the contract `evict_with_provenance` implements in miniature.

- **Data lineage / provenance tracking in data systems** (any solid survey or chapter on
  lineage). [verify]
  Why: the pattern "each output record records which input records produced it" is old and
  well understood; we reuse it for conversation summaries so an auditor can re-check what
  a summary was allowed to claim.

## Alternatives to eviction (context for the design decisions)

- **Prompt compression** (the LLMLingua line of work). [verify]
  Why: compress message *text* instead of dropping *messages* — same budget, different
  failure mode (a garbled constraint vs a missing one). This module tests only
  drop/summarise; compression is a listed non-goal in SPEC.md.

- **Hierarchical / reflective agent memory** (generative-agents style summarisation).
  [verify]
  Why: summaries of summaries — the reason `provenance` maps to a *list* of source indices
  rather than a single one.

## Not needed here

- Real tokenisers (tiktoken and friends): `tokens` is a declared field; counting tokens is
  out of scope (SPEC.md).
- Any model API: the `ScriptedModel` double makes the whole suite deterministic and
  offline. Real-model measurement waits on harness-lab phase 1's trace format.
