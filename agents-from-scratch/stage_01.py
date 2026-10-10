"""Agents From Scratch — stage 1: the loop, and the transcript that is the state

DESIGN DECISION — the model is a callable, not a service.
    Every agent in this course is driven by something that takes the message
    list and returns either a tool call or a final answer. That is all an agent
    loop needs from a model, and it makes the whole runtime — retries, budgets,
    sandboxing, the trace — deterministic, offline and unit-testable. The
    interface is the one every provider converges on:

        model(messages) -> {"tool": "read_file", "args": {...}}
                        |  {"final": "the answer"}

DESIGN DECISION — the transcript is the state.
    There is no hidden agent memory. What the model sees next turn is the
    message list you built, so the loop's correctness is a property of that
    list: who said what, in what order, and what the model was shown. Get the
    roles or the ordering wrong and nothing raises — the model just behaves
    slightly worse, which is the most expensive class of bug in this course.

DESIGN DECISION — a call and its result are one unit.
    The assistant message that requests a tool and the tool message that
    answers it belong together: dropping, reordering or duplicating either one
    produces a conversation no real API accepts (and a model that cannot tell
    what happened). The loop appends them as a pair, and the check asserts the
    pairing survives a tool that fails.

TODO: implement

    run_agent(model, toolbox, task, system=None, max_steps=8, messages=None) -> dict
        A toolbox is anything with:
            .names   -> list of tool names (for the system prompt / the model)
            .call(name, args) -> {"ok": bool, "content": str, ...}
        It never raises for a tool failure — see stage 3 for the real one.

        When `messages` is given it IS the transcript to continue (the caller
        has already built it, stage 6 does exactly this) and `system`/`task` are
        ignored; otherwise the transcript starts with the system message (when
        given) and the user message `task`, and `task=None` appends no user
        message at all.

        The loop:
          1. call model(messages) with the transcript as it stands;
          2. {"tool": n, "args": a} -> append
             {"role": "assistant", "tool": n, "args": a}, call the toolbox, then
             append {"role": "tool", "tool": n, "ok": ..., "content": ...}, and
             go to 1;
          3. {"final": text} -> append it as
             {"role": "assistant", "content": text} and stop.

        Returns:
            {"status": "answered" | "max_steps",
             "answer": str | None,          # the final text, else None
             "steps": int,                  # model calls made
             "tool_calls": [name, ...],     # in order, for the trace and the tests
             "messages": [...],             # the full transcript
             "seen": [[...], ...]}          # what the model was shown, per call

        A tool that returns ok=False is an observation, not an error: the loop
        carries on and lets the model react (stage 3 is where a tool stops
        being able to kill the run). Hitting max_steps is a RESULT, not an
        exception: status "max_steps", answer None, and exactly max_steps model
        calls — the loop must never make the call that would exceed the cap.

        An unknown tool name from the model is passed to the toolbox like any
        other call (the toolbox owns the error).
"""


def run_agent(model, toolbox, task, system=None, max_steps=8, messages=None):
    raise NotImplementedError("stage 1: implement run_agent()")
