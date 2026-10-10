"""MCP From Scratch — stage 7: the tools you expose, read-only first

SOLUTION. Read-only is enforced where the model looks, not where the call lands:
a mutating tool is absent from `tools/list`, and a call to it is -32602 with
`data {"tool": ...}` and its fn untouched. The report tool is ONE tool with two
allowlists (report names, filter columns per report) and a declared type per
filter, so the structure is server-side and only the choices are the model's: the
request is {"table", "where": {column: value}, "columns"} with every column name
from the schema and every value compared as data — "1 OR 1=1" matches nothing and
is never parsed. A flip needs `approved_by` and is recorded; the render is a
sorted, allowlisted, deterministic text table. The read-only switch belongs to
the server, so `enable_writes` releases the server's own switch AND every
mutating tool it was holding — this stage's or another stage's — and returns how
many tools a client can now see. Both supported compositions (`Toolset` +
`Reports` + `install`, and `make_tools(erp)` + `install`) end in a single report
tool: `Reports.install` is idempotent for the same tool and still refuses a name
collision.
"""

from stage_01 import ERRORS, ProtocolError

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

# One sentence, one place: every way of reaching a disabled tool says the same
# thing, and none of them promises it will work tomorrow. The string is also what
# the server stamps on the tools IT holds back while read-only (stage 3's
# READ_ONLY_REASON), which is how a flip finds another stage's mutating tools
# without importing that stage: the values must agree, and the check proves it
# against the real server.
_READ_ONLY = "this server is read-only"

# The declared filter types. `bool` is checked before `int` because True IS an
# int: a filter declared integer that accepted True would compare 1 to a boolean
# and answer a different question than the one it was asked.
_FILTER_TYPES = {
    "string": lambda value: isinstance(value, str),
    "boolean": lambda value: isinstance(value, bool),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
}

# The render's ordering: same-typed values compare naturally, anything else falls
# back to its text, so the sort is total whatever the ERP hands back and two runs
# of the same report never disagree about row order.
_SORT_RANK = {str: 0, bool: 1, int: 2, float: 3}


def _cell(value):
    """One printed cell. None prints as nothing rather than as the word 'None'."""
    return "" if value is None else str(value)


def _sort_key(value):
    rank = _SORT_RANK.get(type(value))
    if rank is None:
        return (4, str(value))
    return (rank, value)


class Toolset:
    def __init__(self, *, read_only=True):
        self._read_only = bool(read_only)
        self._tools = {}          # name -> definition, in registration order
        self._approvals = []      # {"tool", "approved_by"}, one per exposed tool
        self._watchers = []       # published copies that must follow a flip

    @property
    def read_only(self):
        # A property with no setter on purpose: `toolset.read_only = False` would
        # be a capability flip with no approver attached, which is the one thing
        # enable_writes() exists to prevent.
        return self._read_only

    @property
    def enabled(self):
        return [name for name, tool in self._tools.items() if self._visible(tool)]

    @property
    def disabled(self):
        return [name for name, tool in self._tools.items() if not self._visible(tool)]

    @property
    def approvals(self):
        return [dict(entry) for entry in self._approvals]

    # --- registration ------------------------------------------------------

    def add(self, name, description, input_schema, fn, *, mutates=False):
        if not isinstance(name, str) or not name:
            raise ValueError("a tool needs a non-empty name, got %r" % (name,))
        if name in self._tools:
            raise ValueError("a tool named %r is already registered" % name)
        if not callable(fn):
            raise ValueError("the tool %r has no fn to call" % name)
        self._tools[name] = {"name": name, "description": description,
                             "inputSchema": input_schema, "fn": fn,
                             "mutates": bool(mutates)}

    def _visible(self, tool):
        # The whole read-only rule, in one place: a mutating tool is hidden while
        # the server is read-only, and nothing else is.
        return not (self._read_only and tool["mutates"])

    def _definition(self, name):
        """The definition registered under `name`, or None — a copy, so a caller
        cannot reach into the table through it."""
        tool = self._tools.get(name)
        return dict(tool) if tool is not None else None

    def _registered(self):
        """(name, definition) in registration order — what `install` publishes."""
        for name in self._tools:
            yield name, self._definition(name)

    def _watch(self, watcher):
        """Private seam: `install` subscribes the server's tool table, so no one
        has to remember to re-publish after a flip (and stage 10 can hang its
        `notifications/tools/list_changed` on the same event)."""
        self._watchers.append(watcher)

    # --- the two methods a client reaches tools through --------------------

    def list_tools(self, params):
        # Enabled only. A definition in `.disabled` must not appear here in any
        # form, name or description: the client that can read it is the client
        # that will call it.
        return {"tools": [{"name": tool["name"], "description": tool["description"],
                           "inputSchema": tool["inputSchema"]}
                          for tool in self._tools.values() if self._visible(tool)]}

    def call_tool(self, params, session):
        name = params.get("name")
        arguments = params.get("arguments")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise ProtocolError(
                ERRORS["invalid_params"],
                "the arguments of a tool call must be an object, got %s"
                % type(arguments).__name__, data={"tool": name})
        tool = self._tools.get(name) if isinstance(name, str) else None
        if tool is None:
            raise ProtocolError(
                ERRORS["invalid_params"],
                "unknown tool %r" % (name,), data={"tool": name})
        if not self._visible(tool):
            # Refused BEFORE the fn is reached: a disabled tool is not a tool that
            # failed, it is one that is not there.
            raise ProtocolError(
                ERRORS["invalid_params"],
                "tool %r is not enabled: %s" % (name, _READ_ONLY),
                data={"tool": name})
        # The result shape is the tool's: a toolset is a registry and a gate, and
        # it does not wrap what a tool returned or swallow what a tool raised.
        return tool["fn"](arguments, session)

    def enable_writes(self, *, approved_by):
        if not isinstance(approved_by, str) or not approved_by.strip():
            raise ValueError(
                "enable_writes needs a non-empty approved_by: an unattributed "
                "capability flip is how a read-only server becomes a write server "
                "with nobody to blame")
        appearing = [name for name, tool in self._tools.items()
                     if tool["mutates"] and self._read_only]
        self._read_only = False
        for name in appearing:
            self._approvals.append({"tool": name, "approved_by": approved_by})
        visible = set(appearing)
        for watcher in self._watchers:
            # A watcher returns the names it made visible BESIDES the ones it was
            # handed: the server's table holds other stages' tools too, and the
            # count below is "what the client can now see", not "what this object
            # owns".
            visible.update(watcher(appearing) or ())
        return len(visible)


class Reports:
    def __init__(self, erp, schema=REPORT_SCHEMA):
        self.erp = erp
        self.schema = schema

    @property
    def names(self):
        return list(self.schema)

    # --- the tool the model sees -------------------------------------------

    def _description(self):
        # The allowlist is written into the description the model reads: a tool
        # that lists what it can answer is a turn the model does not have to
        # spend discovering it.
        entries = []
        for name, entry in self.schema.items():
            filters = ", ".join("%s:%s" % pair for pair in entry["filters"].items())
            entries.append("%s (%s; filters: %s)" % (name, entry["table"], filters))
        return ("Run one of this server's allowlisted ERP reports. Reports: %s. "
                "Filter values are compared, never parsed." % "; ".join(entries))

    def _input_schema(self):
        return {
            "type": "object",
            "properties": {
                "report": {"type": "string", "enum": self.names,
                           "description": "which allowlisted report to run"},
                "filters": {"type": "object",
                            "description": "column filters from that report's own "
                                           "allowlist; values are data"},
            },
            "required": ["report"],
            "additionalProperties": False,
        }

    def _already_installed(self, toolset):
        """The definition the toolset already holds for THIS tool, or None.

        `make_tools()` fills a toolset with its own `Reports`, and the caller who
        then hands that toolset to `install()` passes a `Reports` of their own —
        so bound-method identity is not enough to recognise "the same tool". What
        identifies it: a `Reports` tool (its fn is `Reports.run`), registered under
        the name, with the same description and the same input schema. Anything
        else under `report` — a different fn, or a report built from a different
        schema — is a NAME COLLISION, and `Toolset.add` must raise for it.
        """
        existing = toolset._definition("report")
        if existing is None:
            return None
        if getattr(existing["fn"], "__func__", None) is not Reports.run:
            return None
        if (existing["description"], existing["inputSchema"]) != (
                self._description(), self._input_schema()):
            return None
        return existing

    def install(self, toolset):
        # ONE tool. The vocabulary is the schema, not the tool list.
        existing = self._already_installed(toolset)
        if existing is not None:
            # Installing the same tool twice is installing it once: this helper
            # can legitimately run twice (make_tools already filled the toolset),
            # which is why the tolerance lives here and not in Toolset.add.
            return existing
        toolset.add("report", self._description(), self._input_schema(), self.run)
        return toolset._definition("report")

    # --- running one -------------------------------------------------------

    def run(self, params, session):
        # `session` is unused on purpose: a read has nothing to hang on the
        # conversation, and inventing a step to record would be a lie the next
        # stage has to maintain.
        report = params.get("report")
        # isinstance first: an unhashable name would raise TypeError inside get()
        # and reach the client as -32603, blaming the server for bad arguments.
        entry = self.schema.get(report) if isinstance(report, str) else None
        if entry is None:
            raise ProtocolError(
                ERRORS["invalid_params"],
                "unknown report %r; this server exposes: %s"
                % (report, ", ".join(self.names)), data={"report": report})
        filters = params.get("filters")
        if filters is None:
            filters = {}
        if not isinstance(filters, dict):
            raise ProtocolError(
                ERRORS["invalid_params"],
                "the filters of report %r must be an object, got %s"
                % (report, type(filters).__name__), data={"report": report})
        # Every key is checked against THIS report's allowlist before any value is
        # used: a column that is valid for another report is not valid here, and
        # building the set from the whole schema is how that leaks.
        for key in filters:
            if key not in entry["filters"]:
                raise ProtocolError(
                    ERRORS["invalid_params"],
                    "unknown filter %r for report %r; allowed: %s"
                    % (key, report, ", ".join(entry["filters"])),
                    data={"filter": key})
        where = {}
        for column, declared in entry["filters"].items():     # schema order, not the caller's
            if column not in filters:
                continue
            value = filters[column]
            checker = _FILTER_TYPES.get(declared)
            if checker is None:
                # A schema type nobody declared is a bug in REPORT_SCHEMA, not in
                # the call: raise something the dispatcher reports as -32603
                # rather than blaming the caller with -32602.
                raise ValueError("REPORT_SCHEMA declares unknown filter type %r "
                                 "for %s.%s" % (declared, report, column))
            if not checker(value):
                raise ProtocolError(
                    ERRORS["invalid_params"],
                    "filter %r of report %r takes a %s, got %s"
                    % (column, report, declared, type(value).__name__),
                    data={"filter": column, "type": declared})
            where[column] = value
        # The request: names from the schema, values from the caller, in separate
        # members. Nothing that came from a caller is ever a name.
        request = {"table": entry["table"], "where": where,
                   "columns": list(entry["columns"])}
        answer = self.erp.report(request["table"], where=request["where"],
                                 columns=request["columns"])
        text = self._render(request["columns"], answer.get("rows") or [])
        # A report that matched nothing is an answer, not a failure.
        return {"content": [{"type": "text", "text": text}], "isError": False}

    def _render(self, columns, rows):
        # The first allowlisted column is the report's key; the executor is free
        # to hand rows back in any order, so the order that reaches the model is
        # decided here.
        ordered = sorted(rows, key=lambda row: _sort_key(row[0] if row else None))
        # Project onto the ALLOWLIST, not onto whatever came back: a row wider
        # than the schema must not widen the result.
        body = [[_cell(row[index]) if index < len(row) else ""
                 for index in range(len(columns))] for row in ordered]
        widths = [len(column) for column in columns]
        for line in body:
            for index, value in enumerate(line):
                if len(value) > widths[index]:
                    widths[index] = len(value)
        lines = ["  ".join(column.ljust(widths[index])
                           for index, column in enumerate(columns)).rstrip()]
        for line in body:
            lines.append("  ".join(value.ljust(widths[index])
                                   for index, value in enumerate(line)).rstrip())
        return "\n".join(lines)


def install(server, toolset, reports):
    reports.install(toolset)
    _publish(server, toolset)
    # A tool is a definition in the server's tool table, reached through
    # `tools/call` — not a JSON-RPC method of its own. Stage 4 owns those two
    # methods for the whole server, so this stage only serves them when nothing
    # else does: registering them unconditionally would narrow the client's view
    # to one stage's tools whenever this install ran last.
    if not _serves(server, "tools/list"):
        server.add("tools/list", lambda params, session: toolset.list_tools(params))
    if not _serves(server, "tools/call"):
        server.add("tools/call", lambda params, session: toolset.call_tool(params, session))


def _serves(server, method):
    """Is this method already served? Stage 3 keeps its table in a private dict on
    the server and mirrors it into a Dispatcher; the tests' fakes keep a plain
    public one. Whichever shape came in, an existing method is left alone."""
    for owner in (server, getattr(server, "dispatcher", None)):
        for attribute in ("handlers", "_handlers"):
            table = getattr(owner, attribute, None)
            if isinstance(table, dict) and method in table:
                return True
    return False


def _publish(server, toolset):
    """Copy the toolset into the server's own tool table, disabled ones included.

    The toolset stays the truth about reachability; this keeps the copy from
    disagreeing with it, now and after every flip, so a single `tools/list` served
    by stage 4's registry cannot advertise what this stage hides. Servers without
    a tool table (the tests' fakes) are left alone.
    """
    add_tool = getattr(server, "add_tool", None)
    if not callable(add_tool):
        return
    set_enabled = getattr(server, "set_tool_enabled", None)
    hidden = set(toolset.disabled)
    for name, definition in toolset._registered():
        add_tool(name, definition["description"], definition["inputSchema"],
                 definition["fn"], mutates=definition["mutates"],
                 enabled=name not in hidden)
        if name in hidden and callable(set_enabled):
            set_enabled(name, False, reason=_READ_ONLY)
    if callable(set_enabled):
        def _follow(names):
            """The flip: the server's switch first, then every tool it hid.

            The read-only switch belongs to the SERVER, because a tool registered
            by another stage is not this stage's to hide by itself: a read-only
            server already registers stages 8 and 9's mutating tools disabled
            (that is the server's own rule), and this flip has to release them
            too. Returns the names it made visible, so `enable_writes` can report
            how many tools a client can now see.
            """
            if hasattr(server, "read_only"):
                server.read_only = False
            visible = []
            table = getattr(server, "tools", None)
            if not isinstance(table, dict):
                return visible
            wanted = set(names)
            for name in sorted(table):
                definition = table[name]
                if not definition.get("mutates") or definition.get("enabled", True):
                    continue
                if name in wanted or definition.get("reason") == _READ_ONLY:
                    set_enabled(name, True)
                    visible.append(name)
            return visible
        toolset._watch(_follow)


def make_tools(erp):
    toolset = Toolset(read_only=True)
    Reports(erp).install(toolset)
    return toolset
