# SPEC — eviction: does the session constraint survive the context window?

agent-evals project #13, "context-window eviction tester" — LEARN mode. This file and
`../tests/test_eviction.py` are the contract; the core you write lives in `eviction.py`
next to this file. Everything is standard-library only and fully deterministic: no
network, no numpy, no model API (the "model" is a scripted test double).

## What it is

A long agent session outruns its context window; something must leave. The dangerous part
is not truncation itself but **silent constraint loss**: "only order from the approved
vendor", "never touch prod" — stated once in an early system message, evicted by turn 30,
and the agent keeps working as if the rule had never existed. This module is a minimal,
deterministic tester for that failure:

- `evict(...)` drops or summarises messages under a hard token budget, with **policies**
  (what leaves first) and **pins** (what must never leave).
- `evict_with_provenance(...)` returns the same result plus an audit trail: every message
  it produces is mapped back to the original message indices it was built from, so a
  summary is checkable instead of trusted.
- `ScriptedModel` answers a question only from what is *retained*, so "did the constraint
  survive?" becomes an assertable boolean (`keeps_constraint`) instead of a judgement call.

## What it demonstrates

1. Session constraints die with their message. Pins are the mechanism that decouples
   *importance* from *recency*: without them, constraint survival is luck — the "newest"
   policy keeps the constraint by accident, "oldest" destroys it.
2. Budget compliance is policy-independent: even a policy that evicts in the wrong
   direction must never return a context over budget.
3. Provenance makes compaction auditable — the same contract harness-lab phase 4 asks for
   when agent memory is compacted: a summary must name the messages it replaced.
4. A scripted test double makes agent behaviour testable with zero model API calls.

## The interface

Implemented here (test infrastructure — already covered by passing tests):

```python
@dataclass
Message(role: str, content: str, tokens: int)     # tokens is given, never measured

@dataclass
Context(budget: int, messages: list[Message])
    .tokens() -> int        # sum of message tokens
    .overflow() -> int      # tokens() - budget; > 0 means over budget

class ScriptedModel(knowledge: dict[str, tuple[str, str]] | None = None)
    .answer(messages, question: str) -> str
    # knowledge maps question -> (needle, value). The needle must appear in the content
    # of some retained message, else the answer is "unknown". Accepts a Context, a list
    # of Message, or plain strings.

def keeps_constraint(result: EvictionResult, constraint: str) -> bool
    # Grader, not mechanism: True iff some retained message still states `constraint`.
    # (Infrastructure by choice — see Design decisions.)

@dataclass
EvictionResult(messages: list[Message], dropped: list[Message],
               provenance: dict[int, list[int]])
    # passive record; the core is the producer below
```

Core — your work, currently stubs raising `NotImplementedError`:

```python
POLICIES = ("oldest", "newest", "middle", "summarise")

def evict(messages, budget, *, policy="oldest", pin=(), summariser=None) -> list[Message]

def evict_with_provenance(messages, budget, *, policy="oldest", pin=(), summariser=None)
    -> EvictionResult
```

Semantics the tests pin (follow these exactly):

- **A policy names what is EVICTED, not what is kept.** `"oldest"` evicts the oldest
  messages first (keeps the recent end) — one unpinned message at a time until the total
  fits. `"newest"` evicts newest-first (keeps the old end — usually the wrong choice, and
  still under the budget). `"middle"` evicts the message closest to the centre first — for
  an even-length list, the left of the two centre positions — recomputing after each
  removal, ties to the lower index. An unknown policy raises `ValueError`.
- **`pin` is a tuple of predicates over `Message`.** A message matching any predicate is
  mandatory under every policy: never dropped, never inside a summarised prefix, never
  truncated. Eviction proceeds as if pinned messages were not candidates (they still occupy
  their positions when the centre is computed).
- **`"summarise"`:** compute the plain `"oldest"` drop set (the minimal prefix whose
  removal fits the budget, ignoring pinned messages), call `summariser(dropped)` once with
  exactly those messages in order, and put the returned `Message` in their place at the
  front. If the summary itself does not fit (it counts against the budget), drop further
  oldest unpinned messages into the summary and retry; if even the summary alone cannot
  fit, degrade gracefully to the plain `"oldest"` result without a summary — the hard
  budget beats the summary.
- **Budget invariant:** `sum(m.tokens for m in result) <= budget` in every admissible case.
- **No-admissible-result → `ValueError`.** Raised when the budget cannot be met without
  violating something mandatory: (a) any policy — the pinned messages alone exceed the
  budget; (b) `"oldest"`/`"newest"`/`"middle"` with nothing pinned — the budget is smaller
  than the smallest single message (the only case where eviction would end at `[]`; that is
  a configuration error, so fail loudly). For `"summarise"`, the degrade path above lands
  on the same rule. Never return an over-budget result; never silently truncate.
- **Provenance** maps each index of `result.messages` to the sorted list of indices in the
  original `messages` it was built from: pass-through messages map to their own single
  index; a summary maps to the indices of the messages it summarised. `dropped` lists the
  removed originals in original order. **Coverage invariant:** the provenance indices and
  the dropped messages partition the original list, with no overlaps.
- **Determinism:** same inputs → identical `messages`, `dropped` and `provenance`. No
  randomness, no dependence on hash order (`PYTHONHASHSEED`) or set iteration.
- `evict` may simply be `evict_with_provenance(...).messages`.

## Acceptance

Each item maps to a named test in `../tests/test_eviction.py` (the A-numbers appear in the
test docstrings).

- **A1 — Budget always holds.** Under every policy the result fits
  (`sum(tokens) <= budget`), and retained messages keep their order and identity.
  → `test_oldest_within_budget`, `test_newest_respects_budget`.
- **A2 — Pinning survives eviction.** With a predicate matching the constraint message,
  the constraint is still in the result after `"oldest"` eviction is forced.
  → `test_pin_survives_oldest_eviction`.
- **A3 — The point of the project (limit).** WITHOUT the pin, `"oldest"` eviction drops
  the constraint message and the `ScriptedModel` — which answered fine before eviction —
  answers `"unknown"` afterwards.
  → `test_unpinned_constraint_is_lost_and_model_answers_unknown`.
- **A4 — Provenance is real.** `"summarise"` produces a message whose provenance names
  exactly the dropped source indices; pass-through messages map to themselves; the
  coverage invariant holds. → `test_summarise_provenance_names_dropped_sources`,
  `test_provenance_passthrough_and_coverage`.
- **A5 — Determinism.** Repeated calls with the same inputs give identical results.
  → `test_deterministic_repeat_calls`.
- **A6 — Impossible budgets are loud.** A budget that cannot hold the mandatory messages
  raises `ValueError` (both entry points). → `test_budget_too_small_raises`,
  `test_pinned_over_budget_raises`.
- **A7 — A wrong-direction policy still respects the budget.** `"newest"` keeps the old
  end and fits. → `test_newest_respects_budget`.

## Limit cases (each one a test a naive implementation fails)

- **L1 — `"middle"` is not `"oldest"`.** The centre message goes first; a front-dropper
  that merely satisfies the budget fails. → `test_middle_evicts_centre_first`.
- **L2 — `"newest"` is not `"oldest"`.** The retained set is pinned to the old end.
  → `test_newest_respects_budget`.
- **L3 — Impossible is loud, not silent.** Returning `[]` (or a truncated message) where
  nothing fits must fail; `ValueError` is the stated outcome.
  → `test_budget_too_small_raises`.
- **L4 — Pins are immovable.** A pinned message at the front survives `"oldest"`, and a
  pinned set larger than the budget raises instead of being quietly trimmed.
  → `test_pin_survives_oldest_eviction`, `test_pinned_over_budget_raises`.
- **L5 — The summary loses to the budget.** An oversized summary must neither produce an
  over-budget context nor an error: the result degrades to plain `"oldest"` eviction.
  → `test_summary_that_cannot_fit_degrades`.

## Out of scope / blocked

- **Real-model measurement.** Running live agent sessions and measuring how often
  constraints are lost is this project's end goal, but it is blocked on harness-lab
  phase 1's trace format (real trajectories to replay) and on the harness's
  compaction-targeted tasks (`t15-session-constraint`, `t16-superseded-instruction`,
  `t17-large-repo`, `t19-huge-log`) plus the phase 4 context variants, which is where
  eviction under a real loop gets exercised. Until then the `ScriptedModel` double is the
  stand-in: this module tests the *mechanism* (what survives eviction), not model
  behaviour.
- **Token counting.** `tokens` is a field on the message; no tokenizer is embedded and
  none may be added (stdlib-only environment).
- **Compression and retrieval.** Rewriting message text (prompt compression) and storing
  evicted content in a retrievable side-store are alternatives, not part of this module:
  the failure mode tested here is deletion, where the content is simply gone.
- **Concurrency, streaming, per-turn incremental re-eviction.** The entry points are pure
  functions over a message list.

## How to run

    cd agent-evals
    /tmp/opencode/venv/bin/python -m pytest -q tests/test_eviction.py
    # or: python3.12 -m pytest -q tests/test_eviction.py

Expected today: the 5 infrastructure tests pass; the 11 core tests report xfailed (they
call the stubs, which raise `NotImplementedError`). Zero failed, zero error. Once the core
is implemented, all 16 should pass. The test file puts `agent-evals/` on `sys.path`
itself, so no conftest wiring is needed.

## Design decisions

- **Policy names the victim, not the survivor.** `"oldest"` = oldest is evicted. Cost: the
  natural misread ("keep oldest") inverts the behaviour; the tests pin the direction.
- **Impossible budgets raise `ValueError` instead of returning `[]` or a placeholder.** An
  eval harness must not sail on with a misconfigured budget (classically: budget given in
  the wrong unit). The line drawn: if no single message can fit, nothing valid could ever
  run — raise. If something fits, eviction runs and may legitimately shrink the window to
  one message; silent *total* loss is a finding (A3), not an exception. Cost: callers must
  handle an exception where an empty list would also have been defensible.
- **Provenance is index-based, not id-based.** Messages carry no identity field; indices
  are stable within one call. Cost: indices mean nothing across calls, and summarising a
  summary needs recursive index lists — which is why the value is a list.
- **Summaries compete for the same budget and degrade to plain eviction when they do not
  fit.** Cost: an oversized summariser silently loses its summary — visible only as a
  missing provenance entry, which is why the coverage invariant exists (A4).
- **`keeps_constraint` is infrastructure, not core.** The mechanism under test is
  eviction; the grader is a one-line existence check, provided so the acceptance tests read
  plainly. (It could have been learner work; keeping it here keeps project #13 focused.)
- **`ScriptedModel` is substring retrieval, not generation.** Deterministic and
  dependency-free, and honest about what it checks: that the statement is *present* in the
  retained window, not that it is *understood*. Cost: a summary that garbles a constraint
  while keeping the exact words would fool it.
- **Identity assertions (`is`) where survival matters.** Dataclass equality would also
  pass for a faithful copy; the tests demand the original objects survive, because
  quietly re-creating messages is exactly the kind of rewriting this project is about.
