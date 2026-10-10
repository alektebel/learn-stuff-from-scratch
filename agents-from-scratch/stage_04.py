"""Agents From Scratch — stage 4: what the model actually said

DESIGN DECISION — the model is untrusted input too.
    Stage 3 made the toolbox unable to kill the run. The other half: the model's
    reply is a string from a system that was optimised to be plausible, not to
    be well-formed. It arrives fenced in markdown, wrapped in "Sure!", with the
    key capitalised, with two JSON objects in it, or with the arguments as a
    sentence instead of an object. A loop that assumes a dict crashes on the
    first real model; a loop that guesses what the model meant invents history.

DESIGN DECISION — repair the envelope, never the meaning.
    "```json\n{...}\n```" and "Sure! {...}" mean the same thing as {...}, and a
    parser is allowed to say so. '{"tool": "write_file", "args": "path=a.txt
    text=hi"}' does not mean the same thing as an args object, and a parser that
    splits it on whitespace has just invented the tool call. When the meaning is
    unparseable the run tells the MODEL what was wrong and lets it try again —
    the fix belongs to the model, and the number of tries belongs to the budget.

DESIGN DECISION — the transcript keeps what the model actually said.
    A malformed reply is appended to the transcript as the assistant message the
    model really produced, followed by a user note that names the problem. The
    raw text is never dropped and the note is never disguised as something the
    user said: the transcript is the audit trail, and a repaired history is a
    traced bug that can no longer be found.

TODO: implement

    parse_decision(raw, names=None) -> dict
        `raw` is whatever the model returned. Returns
            {"ok": bool, "decision": {...} | None, "problem": str | None,
             "repaired": [str, ...], "raw_text": str}
        Repairs, in order, each recorded in `repaired`:
          - a fenced block (``` or ```json) is unwrapped;
          - the first balanced JSON OBJECT in the text is taken (balanced means
            braces nested inside strings and escaped quotes do not end it);
          - keys are matched case-insensitively ("Tool" is "tool", "Final" is
            "final");
          - unknown extra keys are ignored (models add "reasoning"; refusing
            those helps nobody);
          - when `names` is given, a tool name that differs only in case from a
            known name is canonicalised.
        Problems (ok False, `decision` None, and a `problem` that names what is
        wrong): no JSON object present; invalid JSON; a non-object; both "final"
        and "tool"; neither; "final" that is not a string; "tool" that is not a
        non-empty string; "args" that is not an object. The LAST of those is the
        important one: the meaning is never repaired.

    run_parsed(model, toolbox, task, system=None, max_steps=8, messages=None,
               repairs=2) -> dict
        Stage 1's run result (status, answer, steps, tool_calls, messages, seen)
        plus {"repairs": int, "problems": [str, ...]}, with status one of
        "answered" | "max_steps" | "unparsed".

        On a malformed decision: append {"role": "assistant", "content":
        raw_text} (what the model said), then {"role": "user", "content": note}
        where the note names the problem and restates the two accepted shapes,
        charge one repair, and call the model again. No repair note is a
        tool call and no repair note goes to the toolbox.

        `repairs` is the cap (0 means a malformed reply ends the run): after it
        is used up, a malformed reply stops the run with status "unparsed" and
        the problem recorded — the agent must not sit in a repair loop forever
        with a model that cannot comply. A repair note costs a step like any
        other turn, and both caps end the run as a result, never as an
        exception.
"""


def parse_decision(raw, names=None):
    raise NotImplementedError("stage 4: implement parse_decision()")


def run_parsed(model, toolbox, task, system=None, max_steps=8, messages=None,
               repairs=2):
    raise NotImplementedError("stage 4: implement run_parsed()")
