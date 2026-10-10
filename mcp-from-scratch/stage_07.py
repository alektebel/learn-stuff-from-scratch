"""MCP From Scratch — stage 7: the tools you expose, read-only first

DESIGN DECISION — read-only is a property of the LIST, not of the call.
    A tool the model can see is a tool the model will call. A refused call costs a
    turn, teaches the model nothing about the ERP (the refusal is a protocol
    error, not data it can reason about), and invites the same call again from a
    fresh context. So `read_only=True` does not mean "mutating tools answer with
    an error": it means a mutating tool is NOT LISTED. `tools/list` advertises
    `.enabled` and never a name from `.disabled` — that invariant is the whole
    stage. The definitions stay registered, though: the day somebody calls
    `enable_writes(approved_by=...)` the reachable surface grows without a
    redeploy, which is the part the name `disabled` was chosen for.

DESIGN DECISION — to the protocol, a hidden tool is an UNKNOWN tool.
    A call to a disabled tool is `ProtocolError(-32602)`, exactly like a name
    nobody ever registered, and the tool's `fn` does not run: it is not a tool
    that failed, it is a tool that is not there. `data` carries the name
    (`{"tool": name}`) because the spec's example does, and the message may tell
    an operator why it is absent ("not enabled: this server is read-only"). What
    the message must NOT do is promise a future: "ask the user to enable writes"
    is a sentence a model will copy into a user-facing answer as if the server had
    offered it. The state is the operator's, and only `enable_writes` moves it.

DESIGN DECISION — the read-only switch belongs to the SERVER, not to this stage.
    A tool registered by another stage is not this stage's to hide by itself:
    stages 8 and 9 put their mutating tools in the server's table, and a read-only
    server already registers those disabled (the server's own rule, so a tool
    added after this stage's install is hidden too). What this stage owns is the
    flip: `enable_writes(approved_by=...)` releases the server's switch AND every
    mutating tool the server was holding back, whether this stage registered it or
    someone else did. So the count it returns is what a client can now SEE, and
    the invariant "read-only means `tools/list` holds no mutating tool" holds in
    both install orders, not only the one this stage happens to control.

DESIGN DECISION — a capability flip needs a name attached, or it does not happen.
    `enable_writes(approved_by=...)` refuses an empty or missing approver with a
    `ValueError`, before any flag moves: an unattributed capability flip is how a
    read-only server becomes a write server with nobody to blame. Every tool the
    flip exposes is recorded in `.approvals` as `{"tool": name, "approved_by":
    who}` — no timestamp, because this course does not read a clock and a
    timeline the file invents is worse than none; the caller's log has the clock.
    The method returns how many tools BECAME VISIBLE — its own, plus every
    mutating tool the server was holding back (0 when the switch was already
    down) — and sends nothing itself: stage 10 owns
    `notifications/tools/list_changed`, and a list that changes silently is worse
    than one that does not change.

DESIGN DECISION — one tool with an allowlist, not `run_query(sql)` and not fifty
narrow tools.
    `run_query(sql)` puts a value and a structure in the same channel: the model
    writes a query language, the server executes whatever came back, and "which
    tables may this client read" becomes a regex over a string nobody validated.
    Fifty narrow tools put fifty schemas in the context window, and every new
    question becomes a new release. The middle ground is one tool whose entire
    vocabulary is data the server chose: an allowlist of REPORT names, an
    allowlist of filter COLUMNS per report, and a declared TYPE per column
    (`REPORT_SCHEMA` below). The model picks which allowlisted report and which
    allowlisted values; the table, the columns and the comparison are server-side
    and unreachable. A question outside the vocabulary is -32602 naming what was
    asked for (`data: {"report": ...}`, `{"filter": ...}`), which is a message an
    operator can act on — a new entry in `REPORT_SCHEMA`, not a prompt edit.

DESIGN DECISION — values and structure travel in different channels.
    `Reports` builds its request as
        {"table": <schema>, "where": {<column from schema>: <caller's value>},
         "columns": [<schema's columns>]}
    and hands the three parts, separately, to the ERP. Column names come from the
    schema, so a filter key that is not allowlisted for THAT report is refused
    (-32602) instead of reaching the executor; values arrive as values, so
    `"1 OR 1=1"` for a string filter is compared with `==` and matches nothing —
    it is never parsed, never concatenated into a table or column name, and no
    part of it can appear in `table`, `columns` or a `where` KEY. The statement
    the request makes about a value is about its TYPE, never about its text.

DESIGN DECISION — the rendered result is a table, deterministic, and allowlisted.
    A header row of the schema's columns in schema order, then the rows sorted by
    the report's first column (the executor makes no ordering promise, and two
    runs of the same report must read the same or a diff is a coin flip). Cells
    are `str(value)` and the shape is rows and columns: never `str(dict)`, because
    a model that reads `{'vendor_id': 'v1', 'balance': 12000}` learns this
    program's Python instead of the vendor's balance. The header comes from the
    ALLOWLIST, not from whatever the executor returned, so no column outside
    `REPORT_SCHEMA` can appear in a result. A report that matched nothing is a
    SUCCESSFUL result — a header and no rows — because "no open orders" is an
    answer to the question the model asked, and an `isError` there would tell it
    the report failed when the ERP answered perfectly.

TODO: implement

    REPORT_SCHEMA = {name: {"table", "filters": {column: type}, "columns": tuple}}
        Given above and not to be edited: it is the stage's whole vocabulary.

    class Toolset
        __init__(*, read_only=True)
            .read_only   -> bool     # read-only only as a property: the one way
                                     # to move it is enable_writes(approved_by=...)
            .enabled     -> list[str]    # what the model can see right now, in
                                         # registration order (read-only excludes
                                         # every definition added with mutates=True)
            .disabled    -> list[str]    # registered, not exposed
            .approvals   -> list[dict]   # {"tool", "approved_by"} per tool a flip exposed

        add(name, description, input_schema, fn, *, mutates=False) -> None
            fn is called as fn(arguments, session) and returns the tools/call
            result: {"content": [...], "isError": bool}. A tool is a definition in
            a table, not a JSON-RPC method.

        list_tools(params) -> dict
            {"tools": [{"name", "description", "inputSchema"}, ...]} in
            registration order, ENABLED ONLY.

        call_tool(params, session) -> dict
            params is the spec's {"name", "arguments"}. -32602 with
            data {"tool": name} for a name that is not registered AND for one that
            is registered but disabled; in both cases fn does not run. A
            ProtocolError raised by fn is the protocol's answer; anything else is
            left to the dispatcher, which owns -32603.

        enable_writes(*, approved_by) -> int
            approved_by must be a non-empty string (ValueError otherwise, with
            nothing flipped), it is recorded in .approvals, and the return value is
            how many tools BECAME VISIBLE: this stage's own mutating tools, PLUS
            every mutating tool the server's table had disabled because the server
            was read-only (another stage's, or the server's own). The flip releases
            the server's switch too (`server.read_only = False`) — see the DESIGN
            DECISION above — and 0 is the answer when the switch was already down.

    class Reports
        __init__(erp, schema=REPORT_SCHEMA)
            erp is the provided domain (`erp.Erp`); its read side is
            erp.report(table, where=None, columns=None) -> {"columns", "rows"}.

        .names -> list[str]          # the allowlisted report names, schema order

        run(params, session) -> dict
            params is the tool's arguments: {"report": name, "filters": {...}}.
            Raises -32602 for an unlisted report name (data {"report": ...}), for a
            filter key that is not in THAT report's allowlist (data {"filter":
            key}), and for a value that is not the declared type (message naming
            the key and the type). Returns
            {"content": [{"type": "text", "text": <the table>}], "isError": False}.

        install(toolset) -> dict
            Registers ONE tool named "report" whose fn is run and whose
            inputSchema declares the report name and the filters, and RETURNS the
            definition the toolset holds for it. Idempotent for the SAME tool:
            filling a toolset that already holds this report tool returns that
            definition instead of raising, because this helps a composition that
            legitimately runs twice. A DIFFERENT tool under the name (another fn,
            or a report built from another schema) is a name collision, and
            Toolset.add raises for it — install must not adopt a stranger.

    def install(server, toolset, reports) -> None
        reports.install(toolset); publishes the toolset into the server's tool
        table (`server.add_tool`, disabled definitions published disabled with a
        reason); hooks the flip onto the server's table (`set_tool_enabled` on
        every tool the read-only server was holding, whichever stage registered
        it); and registers `tools/list` and `tools/call` for a server that does
        not already serve them (stage 4's registry owns them for the whole
        server).

    def make_tools(erp) -> Toolset
        The read-only default this stage argues for: a toolset holding the report
        tool and nothing that writes.

COMPOSITION — two supported shapes, and both end in ONE report tool.

    canonical, with a toolset nothing has filled yet:

        toolset = Toolset(read_only=True)
        install(server, toolset, Reports(erp))

    convenience, with the toolset `make_tools` already filled:

        install(server, make_tools(erp), Reports(erp))

    The second one reaches `Reports.install` twice for the same tool — once
    inside `make_tools`, once inside `install` — which is exactly the case that
    method's idempotence is for. Two `Reports` instances over the same schema are
    the same tool; the toolset keeps the one it already has, and the server ends
    up advertising one "report", not two.
"""


REPORT_SCHEMA = {                      # the allowlist: this is the whole design
    "open_orders": {
        "table": "orders",
        "filters": {"status": "string", "vendor_id": "string"},
        "columns": ("reference", "vendor_id", "item_id", "quantity", "status"),
    },
    "vendor_balance": {
        "table": "vendors",
        "filters": {"vendor_id": "string"},
        "columns": ("vendor_id", "name", "balance"),
    },
}


class Toolset:
    def __init__(self, *, read_only=True):
        raise NotImplementedError("stage 7: implement Toolset")

    @property
    def read_only(self):
        raise NotImplementedError("stage 7: implement Toolset.read_only")

    @property
    def enabled(self):
        raise NotImplementedError("stage 7: implement Toolset.enabled")

    @property
    def disabled(self):
        raise NotImplementedError("stage 7: implement Toolset.disabled")

    @property
    def approvals(self):
        raise NotImplementedError("stage 7: implement Toolset.approvals")

    def add(self, name, description, input_schema, fn, *, mutates=False):
        raise NotImplementedError("stage 7: implement Toolset.add()")

    def list_tools(self, params):
        raise NotImplementedError("stage 7: implement Toolset.list_tools()")

    def call_tool(self, params, session):
        raise NotImplementedError("stage 7: implement Toolset.call_tool()")

    def enable_writes(self, *, approved_by):
        raise NotImplementedError("stage 7: implement Toolset.enable_writes()")


class Reports:
    def __init__(self, erp, schema=REPORT_SCHEMA):
        raise NotImplementedError("stage 7: implement Reports")

    @property
    def names(self):
        raise NotImplementedError("stage 7: implement Reports.names")

    def run(self, params, session):
        raise NotImplementedError("stage 7: implement Reports.run()")

    def install(self, toolset):
        raise NotImplementedError("stage 7: implement Reports.install()")


def install(server, toolset, reports):
    raise NotImplementedError("stage 7: implement install()")


def make_tools(erp):
    raise NotImplementedError("stage 7: implement make_tools()")
