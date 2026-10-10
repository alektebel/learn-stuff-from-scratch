"""Agent Harness From Scratch — stage 2: the context window is a budget, not a list

DESIGN DECISION — the estimator is a rule you can RECOMPUTE, not a tokenizer.
    A budget is only a budget if the harness can compute it from the bytes it is
    about to send. A provider tokenizer is not in the stdlib, differs between
    providers, and would make the harness's own arithmetic untestable. So the
    rule is arithmetic on the wire text: `4` characters per token, rounded up,
    plus `4` per message. It over-counts whitespace and under-counts nothing the
    harness can see. The alternative — keep a list and trust the window — is how
    a prompt grows one tool result at a time until the provider rejects it, with
    no number anywhere that could have warned you.

DESIGN DECISION — `tool_calls` is counted, because that is where the payload is.
    An assistant message that asked for `run_sql` carries its SQL statement in
    `tool_calls`, NOT in `content` (which is often empty). An estimator that
    prices only `content` charges that message 4 tokens, so a 2 KB query is free
    and the budget becomes a lie at exactly the moment it matters. The counted
    text is the canonical JSON of `tool_calls` — the same bytes a provider sends.

DESIGN DECISION — JSON, sorted keys, compact; never `repr`.
    `repr` prints Python (`'single quotes'`, `True`, a space after every colon);
    the number the harness reasons about must be a function of the VALUE, not of
    a dict's insertion order or an object's identity habits. `json.dumps(calls,
    sort_keys=True, separators=(",", ":"))` is the one spelling.

DESIGN DECISION — `.budget` is the PROMPT budget, not the window.
    `budget_tokens` is the window the provider enforces; `reserve_tokens` is the
    room the completion will need; the number a context can actually enforce is
    `budget_tokens - reserve_tokens`, and that is what `.budget` exposes. A
    caller who compares `tokens()` to the raw window concludes there is room
    that is not there — the prompt arrives at the window, and the model has no
    tokens left to answer with.

DESIGN DECISION — the system message is PINNED; an impossible context refuses.
    The system message is the harness's own instructions: the same every turn,
    and the last thing that should be traded for a chat message. Dropping it to
    fit one more question is dropping the rules to keep the chatter. So it is
    never a trimming candidate, and when it ALONE does not fit the prompt budget
    the context cannot hold anything useful: `HarnessError`, at construction,
    rather than a silent truncation of everything else.

DESIGN DECISION — trimming walks TURNS, not messages.
    A `tool_call` and the `tool` observation answering it are one exchange. An
    observation with no request above it tells the model nothing about what the
    numbers are, and a provider may reject the request outright. So the unit of
    trimming is the assistant message together with the observations whose
    `tool_call_id` it holds, and a drop takes the whole unit. An observation
    whose assistant is not in the context at all is the same mistake arriving
    through the front door, and `add` refuses it where it enters.

DESIGN DECISION — newest wins, and the newest unit is never dropped.
    The newest turn is the one the model is being asked to continue; a trim that
    keeps the oldest and drops the newest answers a question that is no longer
    open. Trimming therefore drops from the OLDEST end, and when even the newest
    unit does not fit, it stays: `fits()` reports the overflow to the caller
    instead of the context hiding the question it was built around.

DESIGN DECISION — one system message, and `add` owns the invariant.
    A context assembled by throwing a second conversation's system prompt into
    the history would silently have two instructions, in an order nothing
    promises. `role == "system"` is refused by `add`: the system message is the
    one given at construction.

TODO: implement

    estimate_tokens(message) -> int
        The size of one message as the model will read it:

            4 + ceil((len(content) + len(canonical_json(tool_calls))) / 4)

        `content` is the message's `content` (a missing/None content is `""`).
        `canonical_json(tool_calls)` is `""` for a message without tool_calls (a
        missing, None or EMPTY `tool_calls` — the wire shape omits an empty
        list), otherwise `json.dumps(tool_calls, sort_keys=True,
        separators=(",", ":"))` — the compact JSON a provider sends, so a 2 KB
        SQL argument costs ~500 tokens and not zero. The `+4` is the envelope:
        `role`, `tool_call_id` and `is_error` are framing, not payload, and are
        not counted separately. Raises `HarnessError` for a `content` that is not
        a string.

    class Context
        __init__(self, system, *, budget_tokens, reserve_tokens=0)
            `system` is the pinned message: a dict with role "system" and string
            content (anything else -> `HarnessError`). `budget_tokens` is a
            positive int and `reserve_tokens` a non-negative int -> otherwise
            `HarnessError`. `reserve_tokens >= budget_tokens` leaves no prompt
            budget, so construction fails the same way an oversized system
            message does: `HarnessError` naming the system message as the thing
            that does not fit. Constructing a context whose system message alone
            exceeds `.budget` is that same `HarnessError`.

        .messages -> list[dict]
            The messages to send: the system message FIRST, then the kept
            history in its original order — oldest kept first, newest LAST. A
            fresh list on every call, so a caller cannot reach the context's own
            storage through it.

        .budget -> int
            The prompt budget: `budget_tokens - reserve_tokens`.

        .tokens() -> int
            `sum(estimate_tokens(message) for message in .messages)` — the
            context includes the system message, so this is the whole prompt.

        .fits() -> bool
            `tokens() <= .budget`. False is a real answer: the newest unit is
            never dropped, so a context built around one oversized observation
            can be over budget and says so.

        .add(message) -> None
            Appends one message (a dict with a string role) and then drops the
            OLDEST whole units until the context fits or only one unit is left
            (the newest one, which stays). `HarnessError` for a message that is
            not a dict with a role, for role "system" (exactly one system
            message, pinned at construction), and for a role "tool" message
            whose `tool_call_id` no kept assistant message holds (a split pair).

    assemble(system, history, *, budget_tokens, reserve_tokens=0) -> list[dict]
        The same result as building a `Context` and adding `history` in order:
        the system message first, then as much of the newest tail of `history`
        as fits the prompt budget, with every call/observation pair kept or
        dropped together. `history` is the whole conversation oldest-first.
        `HarnessError` for an impossible system message, exactly as `Context`.
"""

def estimate_tokens(message):
    raise NotImplementedError("stage 2: implement estimate_tokens()")


class Context:
    def __init__(self, system, *, budget_tokens, reserve_tokens=0):
        raise NotImplementedError("stage 2: implement Context")

    @property
    def messages(self):
        raise NotImplementedError("stage 2: implement Context.messages")

    @property
    def budget(self):
        raise NotImplementedError("stage 2: implement Context.budget")

    def tokens(self):
        raise NotImplementedError("stage 2: implement Context.tokens()")

    def fits(self):
        raise NotImplementedError("stage 2: implement Context.fits()")

    def add(self, message):
        raise NotImplementedError("stage 2: implement Context.add()")


def assemble(system, history, *, budget_tokens, reserve_tokens=0):
    raise NotImplementedError("stage 2: implement assemble()")
