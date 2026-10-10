"""Agent Harness From Scratch — stage 7: compaction, summarize the middle

DESIGN DECISION — the unit of compaction is the TURN, not the message.
    A tool message is meaningless without the assistant message that asked for
    it: a provider rejects the pair with a 400, and a context that keeps the
    observation while dropping the call is a context the API refuses to read. So
    `compact` never indexes messages. It groups them first — an assistant
    message opens a turn, every `tool` message that answers it belongs to that
    turn, anything else is a turn of its own — and then keeps or replaces WHOLE
    turns. A cut is therefore pair-safe by construction, not by a check after
    the fact. The alternative (slice `messages[i:]`, or "keep the last five
    messages") is one line shorter and splits a call from its result the first
    time a turn has two tool calls in it.

DESIGN DECISION — the system prompt and the newest turn are not history.
    The system prompt is the instruction the harness was configured with; it is
    never summarized (a summary of instructions is not instructions) and never
    dropped (the model would answer a different question). The newest turn is
    what the model JUST did — the tool result it is reasoning about right now.
    Summarizing it makes the harness forget the work in flight, which reads as
    the model asking the same question twice. Everything older than the newest
    assistant turn becomes ONE message
    `{"role": "user", "content": SUMMARY_PREFIX + summarize(middle)}`: the
    summary is the model's OWN reading of its earlier history, and it arrives
    the way history arrives, as a user message. The alternative — a long tail
    kept verbatim plus a shrinking summary — makes the prompt bigger every round
    while pretending to make it smaller.

DESIGN DECISION — already-fits is a no-op, and it returns the SAME list.
    A harness that compacts on every step compacts a context that has already
    been compacted: round two summarizes the summary, round three summarizes
    that, and the context becomes a headline of a headline held together by
    nothing. So the first thing `compact` does is price the context: if it fits
    the PROMPT budget, it returns `messages` unchanged, and `summarize` is not
    called at all. That makes compaction idempotent — calling it every round is
    free until the context actually grows past the budget — and it is why the
    return value may be the caller's own list object.

DESIGN DECISION — `summarize` is called AT MOST ONCE, and never with the parts
    that stay.
    One call per compaction, with exactly the middle (the older turns). If the
    system prompt were in there, the summary would argue with the instruction it
    is sitting under; if the kept tail were in there, the model would read its
    own last step twice, once verbatim and once retold, and the two readings
    drift. Which messages form the middle is decided before `summarize` runs, so
    the choice cannot depend on what it returns.

DESIGN DECISION — what does not fit is a `HarnessError`, not a smaller context.
    After the middle is replaced, if the system prompt, the summary and the
    newest turn still exceed the prompt budget, there is nothing left that this
    stage is allowed to throw away — dropping the newest turn is exactly the
    forgetting the tail exists to prevent, and dropping the system prompt
    changes the question. That is a harness bug (a budget set below what the
    harness's own configuration needs), so it raises `HarnessError` naming the
    parts and their sizes: a prompt the provider rejects is at least as bad, and
    arrives later, as a mystery 400.

DESIGN DECISION — the estimate is stage_02's rule, imported late.
    A budget means nothing without a shared unit. `estimate_tokens` belongs to
    stage_02 and that is what is used: the import is lazy (inside the function,
    so importing this stage never depends on a sibling being finished) and there
    is a local fallback with the same fixed rule (4 characters per token
    rounded up, +4 per message, `tool_calls` counted as canonical JSON) for the
    case where stage_02 is not on disk yet or is still its template. A stage
    that cannot be graded alone teaches nothing about the stage.

TODO: implement

    SUMMARY_PREFIX = "Summary of the earlier conversation: "
        The one string in front of every summary. It is what makes a summary
        identifiable as a summary — to the model reading it, and to a human
        reading a transcript months later. Given; do not edit.

    compact(messages, *, budget_tokens, summarize, reserve_tokens=0) -> list
        messages    the wire conversation: leading `system` message(s), then
                    turns (assistant / tool / user messages).
        summarize   fn(middle) -> str, called AT MOST ONCE, with the older
                    messages only (never the system message, never the kept
                    tail). It is the model-backed caller's own call, wrapped in
                    whatever retrying the caller trusts; this stage just calls
                    it once, with the right window, and puts the result where
                    the model reads it.
        The PROMPT budget is `budget_tokens - reserve_tokens` (the reserve is
        room for the completion, the same arithmetic as stage_02), and every
        "fits" below is about the prompt.

        Returns a list of messages in which
          * the leading system messages are unchanged and still first;
          * everything older than the newest assistant turn is gone, replaced
            by exactly one message
            `{"role": "user", "content": SUMMARY_PREFIX + summarize(middle)}`
            placed right after the system messages;
          * the newest turn (the last assistant-anchored block: the last
            assistant message and its tool messages, plus anything after it)
            is kept verbatim, at the end — every older turn was dropped from
            the front of the tail a WHOLE turn at a time (never a message at a
            time), so a call cannot survive without its observations;
          * the total estimate is at most the prompt budget.

        Returns the SAME list object (no copy, and `summarize` not called) when
        `messages` already fits the prompt budget.

        Raises `HarnessError` when the result cannot fit: when the system
        prompt, the summary and the newest turn still exceed the prompt budget,
        and when there is no middle to summarize at all (an over-budget context
        that is nothing but the system prompt and the newest turn). The message
        names what is too big and by how much.
"""

SUMMARY_PREFIX = "Summary of the earlier conversation: "


def compact(messages, *, budget_tokens, summarize, reserve_tokens=0):
    raise NotImplementedError("stage 7: implement compact()")
