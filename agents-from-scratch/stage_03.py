"""Agents From Scratch — stage 3: the toolbox, where a failed tool is an observation

DESIGN DECISION — a tool failure is an observation, not an exception.
    The model is the only component that can react to a bad call: it can fix
    the argument name, try another tool, or give up and answer. So every
    failure the agent could have caused — an unknown tool name, arguments that
    are not a dict, arguments that do not fit the schema, an exception inside
    the tool — has to arrive as an `ok=False` row the model READS, in the same
    shape as a success. Let any of them raise and the loop dies with a
    traceback: the run the user asked for is gone, and the model never learns
    what it did wrong, so the same bug happens on the retry that never comes.
    The toolbox is the boundary that converts "something went wrong" into
    "here is what went wrong, in words".

DESIGN DECISION — a rejected call never runs, and is not a tool call.
    `call()` checks the name, then the argument container, then the schema,
    before the tool's function is touched at all. A tool is code with side
    effects (it writes files, it spends money); running it with the wrong
    arguments so that it can fail on its own is how a mistyped key becomes a
    half-written file. `.executed` is the trace of the functions actually
    invoked, so it stays empty for every call rejected before the function —
    and the check asserts that, because "I did not run it" is a promise, not a
    detail.

DESIGN DECISION — the rendering is deterministic; truncation keeps the head.
    The transcript is diffed, cached and replayed, so the same result must
    render to the same bytes every run: a `str` passes through untouched and
    anything else is `json.dumps(value, sort_keys=True)` — never `str(obj)`,
    which can embed a memory address. When a result is longer than `limit`,
    the HEAD is kept and the marker names how many characters were dropped.
    The obvious implementation keeps the tail, and it is exactly backwards:
    tools put their payload first and their bad news last ("0 matches in 4,120
    characters"), so cutting the tail removes the part the model needs.

TODO: implement

    class ToolBox
        ToolBox(tools=(), *, limit=None)
            `tools` is an iterable of the tool definitions stage 2 builds:
                {"name": str, "description": str, "parameters": {...},
                 "fn": callable, "side_effect": bool}
            `limit` is the maximum number of characters of result content
            handed to the model, or None for no truncation.

        .names   -> list[str]     # registry order, stable, not sorted
        .registry -> dict         # name -> definition, same order as .names
        .limit   -> int | None
        .executed -> list[str]    # names of the tools whose function was
                                  # invoked, in call order; a call rejected
                                  # before the function is never recorded

        call(name, args) -> {"tool": str, "ok": bool, "content": str,
                             "truncated": bool, "error": str | None,
                             "args": dict | None}

        call() NEVER raises for anything the agent can fix. Every one of these
        is an ok=False observation whose `content` the MODEL can act on:

          - unknown name: content names the tool and lists the available ones
            in registry order, e.g.
                unknown tool 'raed_file'; available: list_dir, read_file
            (a did-you-mean is a bonus, not a requirement). The tool does not
            run and is not recorded in .executed.
          - args that are not a dict: rejected, content says so, the tool does
            not run. `args` in the result is then None, because there is no
            argument dict to echo.
          - args that fail the definition's `parameters` schema: rejected the
            same way, before the tool runs, with the offending key named. Call
            stage 2's validate() for this: it owns what a schema means here, and
            a second validator in this file would drift from the first within a
            week. Use the args it hands back, so the tool receives the coerced
            values and the applied defaults, not the model's spelling.
          - the tool raising: ok=False, `error` is exactly
            "{type(exc).__name__}: {exc}", `content` carries the same text.
            Never a traceback, never a re-raise. The function DID run, so it
            IS in .executed.
          - a result that cannot be rendered as JSON: ok=False, content names
            the type it got (never str(value), which can embed an address and
            change between runs).

        Rendering: a `str` result passes through unchanged; any other
        JSON-serialisable value is json.dumps(value, sort_keys=True).

        Truncation: when `limit` is set and the rendered content is longer,
        keep the head and append a marker naming the number of dropped
        characters, e.g.

            "\n[... 4210 characters dropped]"

        and set truncated=True. `limit=None` means no truncation and
        truncated is always False.
"""


class ToolBox:
    """A registry of tools that turns a bad call into a message, not a crash."""

    def __init__(self, tools=(), *, limit=None):
        raise NotImplementedError("stage 3: implement ToolBox.__init__()")

    def call(self, name, args=None):
        raise NotImplementedError("stage 3: implement ToolBox.call()")
