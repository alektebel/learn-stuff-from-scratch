"""MCP From Scratch — stage 4: tools, and the line between a bad request and a failed tool

Pinned spec: MCP 2025-06-18. A server that exposes tools declares the `tools`
capability; the client discovers them with `tools/list` and invokes them with
`tools/call`. The spec spends a section on how a failure is DELIVERED, and this
stage exists for that section:

    Tools use two error reporting mechanisms:

    1. Protocol Errors: Standard JSON-RPC errors for issues like:
       - Unknown tools
       - Invalid arguments
       - Server errors

    2. Tool Execution Errors: Reported in tool results with `isError: true`:
       - API failures
       - Invalid input data
       - Business logic errors

    Any errors that originate from the tool SHOULD be reported inside the
    result object, with `isError` set to `true`, NOT as an MCP protocol error.

    (server/tools, "Error Handling")

And the spec's own examples of the two, which are the shapes you must produce:
the protocol error is

    {"code": -32602, "message": "Unknown tool: invalid_tool_name"}

and the execution error is an ordinary result, `id` for `id` identical to a
success:

    {"result": {"content": [{"type": "text",
                             "text": "Failed to fetch weather data: API rate limit exceeded"}],
                "isError": true}}

DESIGN DECISION — the two failures are different messages because different
    things read them.
    A protocol error is the SERVER saying "I cannot act on this request": the
    tool never ran, the world did not change, and the message is a fact about
    the wiring. A tool execution error is the WORLD saying no to a perfectly
    well-formed request ("unknown vendor 'v9'", "credit hold", "disk on
    fire"): the tool ran, and the words it produced are the only thing that can
    tell the model what to try next. So the second one has to arrive as an
    ordinary result the model READS — `isError: true` and the message as
    content — and the first has to arrive as a JSON-RPC `error` the client
    handles. Get it backwards and the failure is worse than a crash: answer an
    unknown tool with `isError: true` and the model concludes the tool exists
    and retries it forever; raise a business failure as a protocol error and a
    client's error path kills a conversation that had a perfectly good next
    step. This is the whole stage: `call_tool` either RAISES ProtocolError or
    RETURNS a result, and never converts one into the other.

DESIGN DECISION — the whole request is checked before the tool is touched.
    A tool is code with side effects: it writes orders, it moves money. So the
    name, the argument container and the schema are checked first and the tool's
    function is called only once all of them pass. Running a tool "so it can
    fail on its own" is how a mistyped key becomes a half-applied change.
    `session["steps"]` gets `"tools/call:<name>"` for every call that REACHED a
    tool — which is why the append sits after the checks — so a rejected request
    leaves the record untouched, and the check asserts that. "I did not run it"
    is a promise, not a detail.

DESIGN DECISION — the schema check here is a skeleton, and says so.
    Stage 2 of agents-from-scratch owns argument validation for a model loop and
    it does the hard part: coercion, defaults, did-you-mean for typos. Here we
    check the four things a tool's own contract depends on, and nothing else:
    every `required` key is present, every declared JSON type matches, every
    `enum` value is in the enum, and a key the schema does not declare is
    rejected rather than passed through. No `$ref`, no nested objects beyond one
    level, no coercion (`"3"` is not the integer 3), no defaults. All four are
    routed into ONE `ProtocolError` naming the offending argument(s) — the model
    gets one message it can act on, not four exceptions. A validator that grows
    features in this file drifts from stage 2's within a week, and the schema
    dialect is not the lesson; a tool that needs deeper checks does them itself
    and reports a tool execution error, which is exactly the split above.
    The trap to remember: `isinstance(True, int)` is True in Python, and JSON
    `true` is not an integer.

DESIGN DECISION — `isError` is always present, and always a real bool.
    The spec says the field is optional and "if not set ... assumed to be
    false". Assumed by whom? A client that has to assume is a client that
    guesses; the field costs eight bytes and closes that hole. Every result this
    stage produces carries `isError` explicitly — `False` on success.

DESIGN DECISION — the last page carries no `nextCursor` KEY.
    Pagination spec: the response includes "an optional `nextCursor` field if
    more results exist", clients "Treat a missing `nextCursor` as the end of
    results", and "Invalid cursors SHOULD result in an error with code -32602
    (Invalid params)". So the key is there exactly when there is more to fetch —
    not `None`, not `""`, both of which are a lie the client has to
    special-case. Cursors are opaque strings this server invents (`str(offset)`
    here), stable across calls, and a cursor that is not a position in the list
    AS IT IS NOW is refused instead of silently skipped: a cursor from a page
    that has since changed skips results, and skipped results are the one bug
    nobody notices.

DESIGN DECISION — content is text blocks; rendering is deterministic, and a
    finished result is not re-rendered.
    A tool may return either:

      (a) a plain value — a `str` produces ONE text block with that text, any
          other JSON value is `json.dumps(value, sort_keys=True)` (the model
          reads JSON, and sorted keys mean the same call renders to the same
          bytes every run), and a value that cannot be serialised is a tool
          execution error naming the TYPE — never `str(value)`/`repr(value)`,
          which can embed a memory address and change between runs; or

      (b) a COMPLETE result — a dict whose `content` is a list and whose
          `isError` is a bool — which comes back UNCHANGED. The stages above
          build the text the model has to read itself (a report's table, a
          ledger's replay, a diff), and encoding a result into a result shows
          the model a JSON dump of the envelope instead of the table. Both
          halves are required for (b): a dict that merely HAS a `content` key (a
          vendor row with a "content" column) is an ordinary value and is
          rendered as JSON, and an `isError` that is not a bool is not the field
          this protocol defines. `text_result()` is the constructor for (b), so
          a tool that wants to build its own text produces exactly the shape
          that comes back verbatim.

DESIGN DECISION — a tool is not a method.
    `tools/list` and `tools/call` are the only two methods here. A tool lives in
    the server's tool table (`server.add_tool(...)`, one `tools/call` entry
    point) because a client that has to know your tool names as JSON-RPC methods
    does not need `tools/list` at all. `install(server)` with no registry builds
    one over `server.tools`, read LIVE, so a tool some other module registers
    after this stage is installed is listed by the same `tools/list` — and so
    the `enabled` flag a read-only mode flips is honoured on the next request.

TODO: implement

    PAGE = 2
        The default page size for `tools/list`.

    class ToolError(Exception)
        A tool's own failure — "the world said no". `call_tool` turns it into an
        ordinary result with `isError: true` and the exception's message as the
        text content. It is NEVER a protocol error.

    class Tool
        Tool(name, description, input_schema, fn, *, side_effect=False,
             enabled=True, reason=None)
            `fn` is called as `fn(arguments, session)` — the same shape every
            handler in this course has. `arguments` is the validated arguments
            dict, exactly what the caller sent (no splatting, no coercion);
            `session` is the session the call belongs to, because a tool has to
            know WHO is asking before it changes the world (a later stage keeps
            the identity and the idempotency key there).
            `side_effect=True` marks a tool that can change the world (a later
            stage gates those behind an approval; this stage only carries the
            flag).
            `enabled`/`reason` mirror the server table's fields: a disabled tool
            is not listed, and calling it is a protocol error whose message
            carries `reason`.

            .name .description .input_schema .fn .side_effect .enabled .reason

        definition() -> {"name", "description", "inputSchema"}
            The spec's Tool shape, exactly: what the model is shown. Nothing of
            ours leaks into it (no `fn`, no `enabled`), and the schema rides
            along verbatim — the model only knows the arguments you show it.

    class ToolRegistry
        ToolRegistry(*, page=PAGE, table=None)
            `table` is a live `name -> definition` mapping to read in addition
            to the tools added here — that is how `install(server)` serves
            `server.tools`. A definition is a dict with
            `name`, `description`, `inputSchema`, `fn`, `mutates`, `enabled`
            (and optionally `reason`); `mutates` is this stage's `side_effect`.
            A definition is enabled unless something disabled it.

        add(tool) -> Tool
            Registers a `Tool`, or a definition dict, under its name.
            Registration order is the list order, and stays that order.

        .tools -> dict[str, Tool]
            A fresh mapping of everything this registry can see, in
            registration order (the tools added here first, then the live
            table). A mapping, so `enabled` is re-read on every request;
            register through `add()`, never by assigning into it.

        .names -> list[str]
            The same order, derived, never a second list to keep in sync.

        list_tools(params) -> {"tools": [...], "nextCursor"?}
            `params` carries an optional `cursor`. Pages the ENABLED tools,
            `page` at a time; the last page has no `nextCursor` key at all.
            `nextCursor` is `str(offset of the next page)`. A cursor that is
            not a position in the current enabled list is
            ProtocolError(-32602, ..., data={"cursor": <what was sent>}) —
            cursors are opaque strings this server handed out, so `"0"` and
            (`0`) mean the start, `None` means "no cursor", and anything else
            that is not in range is refused. Never silently skips.

        call_tool(params, session) -> {"content": [...], "isError": bool}
            `params` is `{"name": ..., "arguments": {...}}` (`arguments`
            optional). Raise `ProtocolError(ERRORS["invalid_params"], message,
            data={"tool": name})` for: no/blank name, an unknown tool, a
            DISABLED tool (message carries its `reason`), `arguments` that are
            not an object, and any schema problem. The tool's function must NOT
            run and `session["steps"]` must not grow for any of those.
            Otherwise: append `"tools/call:<name>"` to `session["steps"]`, call
            `fn(arguments, session)`, and return a result — `isError: true` with the
            exception's words when the tool raised a `ToolError`, `isError:
            true` with `"{type}: {message}"` when it raised anything else (a
            bug is still not a protocol error), and never a protocol error for
            anything the tool itself did. The return value is rendered by the
            two contracts above: a plain value through the rendering rules, a
            complete result unchanged.

    text_result(text, *, is_error=False) -> dict
        The one result shape: `{"content": [{"type": "text", "text": text}],
        "isError": bool}`. It is the constructor for a tool that returns a
        COMPLETE result — one that builds its own text (a table, a diff) —
        which `call_tool` passes through unchanged instead of encoding it again.

    install(server, registry=None) -> None
        Registers `tools/list` and `tools/call` on `server`, each handler being
        `handler(params, session)`. With `registry=None`, build the registry
        over `server.tools`.
"""

PAGE = 2


class ToolError(Exception):
    """A tool's own failure: reported INSIDE the result, never as a protocol error."""


class Tool:
    """One tool: what the model is shown, and the function that does the work."""

    def __init__(self, name, description, input_schema, fn, *, side_effect=False,
                 enabled=True, reason=None):
        raise NotImplementedError("stage 4: implement Tool.__init__()")

    def definition(self):
        raise NotImplementedError("stage 4: implement Tool.definition()")


class ToolRegistry:
    """Lists and calls tools: the schema skeleton, then the split."""

    def __init__(self, *, page=PAGE, table=None):
        raise NotImplementedError("stage 4: implement ToolRegistry.__init__()")

    def add(self, tool):
        raise NotImplementedError("stage 4: implement ToolRegistry.add()")

    @property
    def tools(self):
        raise NotImplementedError("stage 4: implement ToolRegistry.tools")

    @property
    def names(self):
        raise NotImplementedError("stage 4: implement ToolRegistry.names")

    def list_tools(self, params):
        raise NotImplementedError("stage 4: implement ToolRegistry.list_tools()")

    def call_tool(self, params, session):
        raise NotImplementedError("stage 4: implement ToolRegistry.call_tool()")


def text_result(text, *, is_error=False):
    raise NotImplementedError("stage 4: implement text_result()")


def install(server, registry=None):
    raise NotImplementedError("stage 4: implement install()")
