"""Agent Harness From Scratch — stage 4: dispatch: an unknown tool is a message,
a failing tool is an observation

DESIGN DECISION — a bad call is an OBSERVATION, never an exception.
    A model that is told "unknown tool 'run_query'; available: run_sql" fixes its
    call on the very next turn. A model whose dispatcher raises loses the turn,
    and the exception travels up through the loop (stage 3) into the caller, where
    the only recovery is to start over with the same context and the same model,
    which invents the same name again. So every way a call can be WRONG in the
    eyes of the harness — an unknown name, a missing required argument, an
    argument of the wrong JSON type, an argument the schema never declared —
    comes back as a `tool` message with `is_error=True` that NAMES the argument.
    The alternative (raise and let the loop decide) is not safer: the loop has no
    more information than the dispatcher, and the model is the one party that can
    actually repair the call.

DESIGN DECISION — the boundary between "the world said no" and "our code is buggy"
    is the exception TYPE, and the dispatcher catches exactly one of them.
    `EnvError` is an outcome: the warehouse refused the SQL, and the driver's own
    message ("no such column: revenu") is the most useful sentence the model can
    read. Everything else — a `TypeError` in the tool's body, a `KeyError`, a
    `HarnessError` — is a bug in our program, and turning it into a message is
    how a broken tool becomes part of the conversation forever: the model keeps
    reading "unhashable type: 'list'" and rewrites a query over and over while the
    real fault sits in the tool. So `except EnvError` and nothing wider; a bug
    propagates to whoever can fix it.

DESIGN DECISION — validation lives at the dispatcher, BEFORE the fn runs.
    The schema in `definitions()` is a promise about what the fn accepts. A
    dispatcher that hands the raw arguments to the fn and lets it fail has moved
    the promise somewhere the model cannot read, and it has already run whatever
    half of the call was valid: a `limit` of `"five"` reaches the database before
    anything notices. Check first, then call: the fn is never entered for a call
    the schema does not admit, and no side effect happens for a call that was
    never valid. The check that "the fn ran" is a real failure here, not
    pedantry.

DESIGN DECISION — `render_result` is a text TABLE, not `str(env_result)` and not
    a JSON dump.
    The result dict is this program's Python and the model should not have to
    learn it: `{'columns': ['country', 'total'], 'rows': [['CN', 360.0]]}` spends
    the model's next turn parsing braces and quotes, and `json.dumps` is the same
    mistake with fewer quotes. What the model can use is the shape a person reads
    in a terminal — a header from `columns`, one line per row with the cells joined
    by `" | "`, the numbers exactly as SQL handed them back (`360.0` stays
    `360.0`), and a trailing `(N rows)` line so the model knows whether it is
    looking at all of the answer or the first page of one. Same input, same bytes:
    no clock, no `repr` of an object, no dict ordering.

`tools` is `{name: {"description", "input_schema", "fn"}}`; the dict's insertion
order is the order the model is offered the tools, and `fn(arguments) -> result`
where `result` is what `render_result` renders: `{"columns": [...], "rows": [...]}`.
A `fn` raises `EnvError` to say the world refused, and nothing else.

TODO: implement

    class Dispatcher:
        __init__(self, tools)
            Holds the registered tools. Raises ValueError for a table that is not a
            dict or a tool with no callable `fn` — a registration bug is the
            harness author's, and failing at construction names it once.

        .definitions() -> [{"name", "description", "inputSchema"}, ...]
            The tools the model may call, in REGISTRATION order. Copies — the
            schema too — so a caller cannot rewrite the registry, or the boundary
            the next call is validated against, through what it was handed.

        .observe(tool_call) -> tool message
            `tool_call` is a wire tool_call: {"id", "name", "arguments"}. Returns
            {"role": "tool", "tool_call_id": <the call's id>, "content": str,
             "is_error": bool} — `content` is ALWAYS a string, because it is what
            the model reads. Never raises for anything the model sent: an unknown
            name, a bad argument and an `EnvError` are all observations with
            `is_error=True`. Any other exception from `fn` propagates.

        .called -> [name, ...]     # copy; tools whose fn RAN, in order
        .unknown -> [name, ...]    # copy; names that are not registered, in order

        A call refused by validation is neither: the tool exists and did not run.

    def render_result(env_result) -> str
        `env_result` is {"columns": [names], "rows": [[cell, ...], ...]}. One line
        per row, cells joined with " | ", a header line from the columns, and a
        trailing "(N rows)" line (N is the number of rows printed). Numbers print
        as SQL gave them. Raises HarnessError for a shape that is not an env
        result: the fn is ours, so a fn that returns something else is a bug and
        the message says which one.
"""


class Dispatcher:
    def __init__(self, tools):
        raise NotImplementedError("stage 4: implement Dispatcher")

    def definitions(self):
        raise NotImplementedError("stage 4: implement Dispatcher.definitions()")

    def observe(self, tool_call):
        raise NotImplementedError("stage 4: implement Dispatcher.observe()")

    @property
    def called(self):
        raise NotImplementedError("stage 4: implement Dispatcher.called")

    @property
    def unknown(self):
        raise NotImplementedError("stage 4: implement Dispatcher.unknown")


def render_result(env_result):
    raise NotImplementedError("stage 4: implement render_result()")
