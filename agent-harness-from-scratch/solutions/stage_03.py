"""Agent Harness From Scratch — stage 3 solution: the loop, and what a budget
exhaustion returns.

The reasoning lives in `stage_03.py`'s docstring; this file is the implementation.
"""

from stage_01 import assistant_message, collect, usage_add
from tiny_env import HarnessError

EMPTY_USAGE = {"input_tokens": 0, "output_tokens": 0}

STATUSES = ("done", "budget", "truncated")


def _note(trace, **step):
    """Record one step, if the caller asked for a trace at all. Duck-typed on
    purpose: stage 3 does not import stage 8, and any object with `.step` that
    takes these keywords is a trace."""
    if trace is not None:
        trace.step(**step)


def run(model, dispatch, question, *, system=None, tools=None, max_steps=8,
        trace=None, usage=None, clock=None):
    """Drive one conversation to a stop and return what happened."""
    if max_steps < 0:
        raise HarnessError("max_steps cannot be negative, got %r" % (max_steps,))
    messages = []
    if system is not None:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": question})

    total = dict(EMPTY_USAGE)
    answer = ""
    steps = 0
    status = "budget"                  # what we get if the budget runs out

    while steps < max_steps:
        steps += 1
        turn = collect(model(list(messages), tools))
        # The request goes in BEFORE the work it asks for: a crash between the
        # two leaves a conversation that still parses.
        messages.append(assistant_message(turn))
        total = usage_add(total, turn["usage"])
        if usage is not None:
            usage["input_tokens"] = total["input_tokens"]
            usage["output_tokens"] = total["output_tokens"]
        _note(trace, kind="model", turn=steps,
              tokens=turn["usage"]["input_tokens"] + turn["usage"]["output_tokens"],
              ok=True, clock=clock)
        if turn["text"]:
            answer = turn["text"]

        reason = turn["reason"]
        if reason == "length":
            status = "truncated"
            break
        if reason == "stop":
            status = "done"
            break
        if reason == "tool_calls":
            if not turn["tool_calls"]:
                raise HarnessError(
                    "the model's turn ended with reason 'tool_calls' and asked for "
                    "no tools: treating that as done ends the conversation while "
                    "the model believes it is mid-action")
            for call in turn["tool_calls"]:
                observation = dispatch(call)
                messages.append(observation)
                _note(trace, kind="tool", turn=steps, tool=call["name"],
                      ok=not observation.get("is_error"), clock=clock)
            continue
        raise HarnessError("unknown end reason %r: a harness that treats an "
                           "unrecognised stop as 'done' guesses" % (reason,))

    # A model that stops with nothing to say is a real turn: the answer is the
    # empty string and the status still says "done", so the caller can tell "it
    # said nothing" from "it never got the chance".
    return {"status": status, "answer": answer, "messages": messages, "steps": steps,
            "usage": total}
