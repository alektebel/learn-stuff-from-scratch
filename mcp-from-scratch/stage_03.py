"""MCP From Scratch — stage 3: the handshake, and the session it creates

DESIGN DECISION — the handshake is not a formality, it is a negotiation.
    The client says which revision it speaks and which features it has; the server
    answers with a revision it can actually speak and a capability table it can
    actually honour. Both halves must be true or the client plans against a
    fiction: a server that declares `resources` and then answers -32601 to
    `resources/list` is worse than one that declares nothing, because the client
    built a UI for it.

DESIGN DECISION — the lifecycle is a gate, not a comment.
    Until initialization completes, every request except `initialize` and `ping`
    is answered with an error. A server that cheerfully serves `tools/call`
    before the handshake has no negotiated revision and no client capabilities —
    which is exactly the state in which a server sends an `elicitation/create` to
    a client that never said it could show one.

DESIGN DECISION — derived capabilities, overridden only by more truth.
    The capability table is computed from the methods that are registered: no
    `tools/*`, no `tools` capability; `resources/subscribe` present, and
    `subscribe: true`. An explicitly declared capability that has no method behind
    it is a bug in the server, so it raises a ValueError naming the capability
    (the envelope turns that into -32603 — the client sees an internal error, the
    author sees the sentence).

DESIGN DECISION — one session dict, and the identity in it.
    `session` belongs to the caller of the server, not to a module: every handler
    receives it and stages hang their state on it (`identity`, `steps`, `data`).
    `identity` is set from the handshake's `_meta` when present. In a real
    deployment it comes from the OAuth token at the transport and not from a field
    the client chooses — the field exists here so that the authorisation DECISION
    (who may mutate what) is the exercise rather than the token plumbing.

TODO: implement

    PROTOCOL_VERSIONS = ("2025-06-18",)     # what this build speaks, newest first

    class Server
        __init__(self, name, version, *, protocol_versions=PROTOCOL_VERSIONS,
                 capabilities=None, on_notify=None)
            .name .version .protocol_versions .on_notify
            .capabilities -> dict               # what was hand-negotiated
            .initialized -> bool
            .client_info -> dict | None .client_capabilities -> dict | None
            .protocol_version -> str | None
            .session -> {"identity": None, "steps": [], "data": {}}
            .notifications -> list[dict]        # every notification this server sent
            .tools -> dict[name, definition]    # the tool table (stage 4 lists/calls it)
            .dispatcher -> the stage 1 Dispatcher, so .failures is reachable
        add(method, handler) -> handler
            Registers a non-tool method. The handler is called with
            (params, session); it must not worry about the handshake, because the
            gate below runs first.
        add_tool(name, description, input_schema, fn, *, mutates=False, enabled=True) -> dict
            Appends {"name", "description", "inputSchema", "fn", "mutates",
            "enabled"} to .tools. `fn` is called with (arguments, session) — the
            same shape as a method handler, so a tool can reach the identity and
            the steps. A name already in the table is a ValueError: a duplicate
            that silently replaces a definition is how a read-only server grows a
            write tool.
            A server starts READ-ONLY (`server.read_only` is True): a tool
            registered with mutates=True arrives disabled with `reason` set to
            READ_ONLY_REASON, so it is not in tools/list at all until stage 7's
            enable_writes(approved_by=...) flips the server and enables every
            mutating tool on it.
        set_tool_enabled(name, enabled, *, reason=None) -> dict
            Flips definition["enabled"] and stores definition["reason"].
        notify(method, params=None) -> dict
            Builds a notification, appends it to .notifications, calls on_notify
            with it, and returns it.
        install(module) -> None
            Calls module.install(self) — how every later stage joins the server.
        supports(feature) -> bool
            True when the CLIENT declared the capability `feature` in the
            handshake (e.g. "elicitation"), False before the handshake.
        initialize(params, session) -> dict
            The handshake itself:
              - params["protocolVersion"] must be a string; if it is one this
                build speaks, that revision is echoed; otherwise raise
                ProtocolError(-32602, "Unsupported protocol version",
                data={"supported": [all of them], "requested": the string}).
              - remember clientInfo and the client's capabilities; set
                session["identity"] from params["_meta"]["identity"] when it is a
                non-empty string.
              - validate the capability table (see above), then return
                {"protocolVersion", "capabilities", "serverInfo": {"name", "version"}}.
              - a second initialize is ProtocolError(-32600, ...): the
                initialization phase is the FIRST interaction.
        dispatch(message) -> dict | None
            Stage 1's envelope rules plus:
              - `initialize` is always allowed. `ping` is always allowed and
                answers {} — a liveness check that needs a handshake cannot check
                liveness.
              - any other request before .initialized is
                ProtocolError(-32600, "server not initialized: send initialize
                first") and its handler must NOT run. (-32600 rather than -32601:
                the method may well exist, the session is what is wrong.)
              - `notifications/initialized` (a notification) sets .initialized;
                being a notification it answers nothing, so a failure lands in
                .dispatcher.failures.
              - when a cancellations registry is installed (stage 6) it is
                consulted three times: the initialize request's id is added to its
                .protected set (the spec forbids cancelling that one), every
                request's id enters its .in_flight set BEFORE the handler runs
                (only the server knows a request has started, and that set is what
                lets the registry ignore a cancellation for work that is over),
                and the final response goes through cancellations.answer_for(...)
                so a cancelled request sends nothing at all.
"""

PROTOCOL_VERSIONS = ("2025-06-18",)


class Server:
    def __init__(self, name, version, *, protocol_versions=PROTOCOL_VERSIONS,
                 capabilities=None, on_notify=None):
        raise NotImplementedError("stage 3: implement Server.__init__")

    # -- registration -------------------------------------------------------

    def add(self, method, handler):
        raise NotImplementedError("stage 3: implement Server.add")

    def add_tool(self, name, description, input_schema, fn, *, mutates=False,
                 enabled=True):
        raise NotImplementedError("stage 3: implement Server.add_tool")

    def set_tool_enabled(self, name, enabled, *, reason=None):
        raise NotImplementedError("stage 3: implement Server.set_tool_enabled")

    def notify(self, method, params=None):
        raise NotImplementedError("stage 3: implement Server.notify")

    def install(self, module):
        raise NotImplementedError("stage 3: implement Server.install")

    # -- lifecycle ----------------------------------------------------------

    def supports(self, feature):
        raise NotImplementedError("stage 3: implement Server.supports")

    def initialize(self, params, session):
        raise NotImplementedError("stage 3: implement Server.initialize")

    def dispatch(self, message):
        raise NotImplementedError("stage 3: implement Server.dispatch")
