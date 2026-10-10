"""Agents From Scratch — stage 1: the loop, and the transcript that is the state

SOLUTION. The loop is eleven lines and two decisions: a call and its result are
appended as a pair, and hitting the step cap is a result rather than an
exception. `seen` records what the model was shown, which is what makes "the
transcript is the state" testable instead of aspirational.
"""


def _copy(message):
    out = dict(message)
    if isinstance(out.get("args"), dict):
        out["args"] = dict(out["args"])
    return out


def run_agent(model, toolbox, task, system=None, max_steps=8, messages=None):
    if messages is not None:
        transcript = [_copy(m) for m in messages]
    else:
        transcript = []
        if system:
            transcript.append({"role": "system", "content": system})
        if task is not None:
            transcript.append({"role": "user", "content": task})

    seen = []
    tool_calls = []
    steps = 0
    status = "max_steps"
    answer = None

    while steps < max_steps:
        shown = [_copy(m) for m in transcript]
        seen.append(shown)
        steps += 1
        decision = model(shown)

        if isinstance(decision, dict) and "final" in decision:
            answer = decision["final"]
            transcript.append({"role": "assistant", "content": answer})
            status = "answered"
            break

        # Anything that is not a final answer is a tool call as far as the loop
        # is concerned — including a malformed decision. The toolbox is what
        # turns that into an observation the model can read (stage 3), so the
        # loop never has to guess what the model meant and never dies trying.
        name = decision.get("tool") if isinstance(decision, dict) else None
        args = decision.get("args") if isinstance(decision, dict) else None
        transcript.append({"role": "assistant", "tool": name, "args": args})

        result = toolbox.call(name, args)
        transcript.append({"role": "tool", "tool": name,
                           "ok": bool(result.get("ok")),
                           "content": result.get("content", "")})
        tool_calls.append(name)

    return {"status": status, "answer": answer, "steps": steps,
            "tool_calls": tool_calls, "messages": transcript, "seen": seen}
