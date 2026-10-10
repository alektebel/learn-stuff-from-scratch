"""MCP From Scratch — stage 3: the handshake, and the session it creates

SOLUTION. The stage 1 Dispatcher carries the envelope rules; this class adds the
gate (nothing but initialize/ping before the handshake completes), the negotiated
capability table (derived from the registered methods, so a declared capability
cannot be a lie), one session dict, and the tool table stages 4-9 fill.
"""

from stage_01 import (ERRORS, Dispatcher, ProtocolError, notification)

PROTOCOL_VERSIONS = ("2025-06-18",)

# capability name -> the method prefix that backs it
CAPABILITY_PREFIXES = {"tools": "tools/", "resources": "resources/",
                       "prompts": "prompts/"}
CAPABILITY_SUBKEYS = {"tools": ("listChanged",),
                      "resources": ("subscribe", "listChanged"),
                      "prompts": ("listChanged",)}
# messages a client may send before the handshake completes
GATE_EXEMPT = ("initialize", "ping", "notifications/initialized")
# why a mutating tool is not listed yet
READ_ONLY_REASON = "this server is read-only"


class Server:
    def __init__(self, name, version, *, protocol_versions=PROTOCOL_VERSIONS,
                 capabilities=None, on_notify=None):
        self.name = name
        self.version = version
        self.protocol_versions = tuple(protocol_versions)
        self._declared = capabilities
        self.on_notify = on_notify
        self.capabilities = {}
        self.initialized = False
        self._handshaken = False
        self.protocol_version = None
        self.client_info = None
        self.client_capabilities = None
        self.session = {"identity": None, "steps": [], "data": {}}
        self.notifications = []
        self.tools = {}
        self.read_only = True            # a server says otherwise explicitly
        self.cancellations = None
        self.dispatcher = Dispatcher()
        self._handlers = {}
        self.add("initialize", self.initialize)
        self.add("ping", self.ping)
        self.add("notifications/initialized", self._mark_initialized)

    # -- registration -------------------------------------------------------

    def add(self, method, handler):
        self._handlers[method] = handler
        self.dispatcher.add(method, lambda params: self._serve(method, handler, params))
        return handler

    def _serve(self, method, handler, params):
        if method not in GATE_EXEMPT and not self.initialized:
            raise ProtocolError(
                ERRORS["invalid_request"],
                f"server not initialized: {method!r} arrived before the handshake "
                f"completed; send initialize, then notifications/initialized")
        return handler(params, self.session)

    def add_tool(self, name, description, input_schema, fn, *, mutates=False,
                 enabled=True):
        # `fn` is called as fn(arguments, session) by tools/call (stage 4).
        if name in self.tools:
            raise ValueError(
                f"the tool {name!r} is already registered: replacing a definition "
                f"silently is how a read-only server grows a write tool")
        definition = {"name": name, "description": description,
                      "inputSchema": input_schema, "fn": fn,
                      "mutates": bool(mutates), "enabled": bool(enabled)}
        if definition["mutates"] and self.read_only:
            # Read-only first, and at the door: a mutating tool registered on a
            # read-only server arrives DISABLED, with the reason recorded, because
            # a tool the model can see is a tool the model will call (stage 7).
            definition["enabled"] = False
            definition["reason"] = READ_ONLY_REASON
        self.tools[name] = definition
        return definition

    def set_tool_enabled(self, name, enabled, *, reason=None):
        definition = self.tools.get(name)
        if definition is None:
            raise ValueError(f"no tool named {name!r} is registered")
        definition["enabled"] = bool(enabled)
        if reason is not None:
            definition["reason"] = reason
        return definition

    def notify(self, method, params=None):
        message = notification(method, params)
        self.notifications.append(message)
        if self.on_notify is not None:
            self.on_notify(message)
        return message

    def install(self, module):
        module.install(self)
        return module

    # -- lifecycle ----------------------------------------------------------

    def supports(self, feature):
        """A client declaring `"elicitation": {}` SUPPORTS elicitation — the value
        is the options object, so the declaration is the key's presence."""
        if not self.client_capabilities:
            return False
        return feature in self.client_capabilities

    def ping(self, params, session):
        return {}

    def _mark_initialized(self, params, session):
        if not self._handshaken:
            raise ProtocolError(ERRORS["invalid_request"],
                                "notifications/initialized arrived before initialize")
        self.initialized = True
        return {}

    def initialize(self, params, session):
        if self._handshaken:
            raise ProtocolError(
                ERRORS["invalid_request"],
                "already initialized: the initialization phase is the first "
                "interaction, and there is no second one")
        requested = params.get("protocolVersion")
        if not isinstance(requested, str):
            raise ProtocolError(ERRORS["invalid_request"],
                                "initialize needs protocolVersion, a string")
        if requested not in self.protocol_versions:
            raise ProtocolError(
                ERRORS["invalid_params"], "Unsupported protocol version",
                data={"supported": list(self.protocol_versions),
                      "requested": requested})
        table = self._capability_table()          # a declared lie raises here
        self.capabilities = table
        self.protocol_version = requested
        info = params.get("clientInfo")
        self.client_info = dict(info) if isinstance(info, dict) else {}
        caps = params.get("capabilities")
        self.client_capabilities = dict(caps) if isinstance(caps, dict) else {}
        meta = params.get("_meta")
        identity = meta.get("identity") if isinstance(meta, dict) else None
        if isinstance(identity, str) and identity:
            session["identity"] = identity
        self._handshaken = True
        return {"protocolVersion": requested,
                "capabilities": {k: dict(v) for k, v in sorted(table.items())},
                "serverInfo": {"name": self.name, "version": self.version}}

    def _capability_table(self):
        methods = set(self.dispatcher.handlers)
        derived = {}
        for name, prefix in sorted(CAPABILITY_PREFIXES.items()):
            if any(method.startswith(prefix) for method in methods):
                subs = {}
                for sub in CAPABILITY_SUBKEYS[name]:
                    subs[sub] = (name + "/subscribe" in methods) if sub == "subscribe" \
                        else True
                derived[name] = subs
        table = {name: dict(subs) for name, subs in derived.items()}
        for name, declared in sorted((self._declared or {}).items()):
            if name not in CAPABILITY_PREFIXES:
                raise ValueError(
                    f"capability {name!r} is not one this server knows: declaring a "
                    f"feature it does not implement is the bug this table exists to "
                    f"prevent")
            if name not in derived:
                raise ValueError(
                    f"capability {name!r} is declared but no {name}/* method is "
                    f"registered")
            if not isinstance(declared, dict):
                raise ValueError(f"capability {name!r} must be an object")
            for sub, value in sorted(declared.items()):
                if sub not in CAPABILITY_SUBKEYS[name]:
                    raise ValueError(f"unknown {name} capability {sub!r}")
                if value and not derived[name][sub]:
                    raise ValueError(
                        f"{name}.{sub} is declared true but nothing backs it")
                table[name][sub] = bool(value)
        return table

    def dispatch(self, message):
        if (isinstance(message, dict) and message.get("method") == "initialize"
                and "id" in message and self.cancellations is not None):
            # the spec forbids cancelling initialize: protect it the moment the
            # request is seen, before any handler can hear about a cancellation.
            self.cancellations.protected.add(message["id"])
        if (self.cancellations is not None and isinstance(message, dict)
                and "id" in message):
            # The server is the only place that knows a request has STARTED: the
            # registry needs that to tell "cancel something in flight" from "cancel
            # something that is over", which the spec says to ignore quietly.
            in_flight = getattr(self.cancellations, "in_flight", None)
            if in_flight is not None:
                in_flight.add(message["id"])
        response = self.dispatcher.dispatch(message)
        if (self.cancellations is not None and isinstance(message, dict)
                and "id" in message):
            response = self.cancellations.answer_for(message["id"], response)
        return response
