"""solutions/mcp_server.py — reference implementation of the MCP-over-ERP server.

Drop-in replacement for the learner's ``mcp_server.py``: copy this file over it in a
scratch copy of the module and the whole contract in ``tests/test_mcp_server.py``
passes (18 passed). It is the answer key, kept beside the LEARN stub so the exercise
can still be done.

What it implements (SPEC.md): the JSON-RPC 2.0 dispatch, the pinned-revision
handshake, ``tools/list``, schema-validated ``tools/call`` with the two error
channels, idempotent retries, the per-session sequence policy, and the
streamable-HTTP framing.

DESIGN DECISION - the session policy is consulted *before* dispatch and on every
call, including the first of a forbidden sequence. ``SessionState.observe`` raises
before it records, so a refused mutation never reaches the ERP and never enters the
history (test 17). Cost: a legitimate "check a balance, then order" flow is refused;
that false positive is the point of limit L3 (SPEC).
DESIGN DECISION - idempotency replays before ``observe`` and before the ERP. A retry
is the *same* call, not a new one, so replaying it must not append to the session
history or re-validate against the ERP's duplicate-reference rule (test 15). Cost:
the replay window is unbounded in this MVP.
DESIGN DECISION - unknown tools are tool results (``isError``), not protocol errors.
The model reads them and picks another tool; a protocol error is for the client, not
the model (test 12). Cost: an unknown-tool typo is silent to a JSON-RPC client that
only logs protocol errors.
DESIGN DECISION - validation is hand-rolled against the same ``TOOL_SCHEMAS`` the
model sees, not a JSON-Schema library. The schemas are small and fixed, and adding a
dependency to a stdlib module has no payoff here. Cost: only the JSON-Schema subset
this module uses (type, required, additionalProperties) is enforced.
"""

from __future__ import annotations

import json
from typing import Any

from fake_erp import Erp, PolicyViolation

# --- JSON-RPC 2.0 protocol constants -------------------------------------------
JSONRPC = "2.0"
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# --- MCP revision handshake -----------------------------------------------------
PINNED_REVISION = "2025-11-25"
SUPPORTED_REVISIONS = ("2025-11-25", "2025-06-18")


class RpcError(Exception):
    """A JSON-RPC protocol-level error."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def error_payload(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            error["data"] = self.data
        return error


# --- Tool catalog ---------------------------------------------------------------
TOOL_SCHEMAS: tuple[dict[str, Any], ...] = (
    {
        "name": "get_open_orders",
        "description": "List the open sales orders of one customer. Read-only.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "customer": {
                    "type": "string",
                    "description": "exact customer name as the ERP knows it",
                },
            },
            "required": ["customer"],
        },
    },
    {
        "name": "get_vendor_balance",
        "description": "Return the outstanding balance owed to one vendor. Read-only.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "vendor": {
                    "type": "string",
                    "description": "exact vendor name as the ERP knows it",
                },
            },
            "required": ["vendor"],
        },
    },
    {
        "name": "create_purchase_order",
        "description": (
            "Create one purchase order. Mutating: when retrying this call after a "
            "timeout, always send the same idempotency key — never invent a new one."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "unique reference for the order; never reuse after a failure",
                },
                "vendor": {
                    "type": "string",
                    "description": "exact vendor name as the ERP knows it",
                },
                "amount": {
                    "type": "number",
                    "description": "order total, positive",
                },
            },
            "required": ["reference", "vendor", "amount"],
        },
    },
)


# --- Session state and the sequence policy --------------------------------------
class ForbiddenSequence:
    """A mutation that is refused once the listed reads happened in the same session."""

    def __init__(self, reads: tuple[str, ...], mutation: str) -> None:
        self.reads = tuple(reads)
        self.mutation = mutation


class SessionState:
    """Per-identity memory of the tools called so far, plus the policy over sequences."""

    DEFAULT_RULES = (
        ForbiddenSequence(("list_vendors", "get_vendor_balance"), "create_payment_run"),
        ForbiddenSequence(("get_open_orders", "get_vendor_balance"), "create_purchase_order"),
    )

    def __init__(self, rules: list[ForbiddenSequence] | None = None) -> None:
        self.rules = list(SessionState.DEFAULT_RULES if rules is None else rules)
        self._history: dict[str, list[str]] = {}

    def observe(self, identity: str | None, tool: str) -> None:
        history = self._history.setdefault(identity if identity is not None else "?", [])
        for rule in self.rules:
            if tool == rule.mutation and all(read in history for read in rule.reads):
                raise PolicyViolation(
                    "refused: this session already read "
                    f"{', '.join(rule.reads)}; calling {rule.mutation} now is the "
                    "recon-then-move pattern — start a new session or ask for approval"
                )
        history.append(tool)


# --- The server -----------------------------------------------------------------
class McpServer:
    """A Model Context Protocol server in front of an ERP (reference implementation)."""

    SERVER_NAME = "erp-mcp"
    SERVER_VERSION = "0.1.0"

    def __init__(self, erp: Erp) -> None:
        self.erp = erp
        self.session = SessionState()
        self._idempotency: dict[tuple[str | None, str, str], dict[str, Any]] = {}

    # -- JSON-RPC dispatch -------------------------------------------------------
    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(message, dict):
            return self._error(None, RpcError(INVALID_REQUEST, "message must be a JSON object"))
        request_id = message.get("id")
        has_id = "id" in message
        method = message.get("method")
        params = message.get("params") or {}
        if method is None:
            if not has_id:
                return None
            return self._error(request_id, RpcError(INVALID_REQUEST, "missing method"))
        if not has_id:
            # A notification gets no response; dispatch only for side effects, and a
            # protocol error in a notification is dropped (there is nowhere to send it).
            try:
                self._dispatch(method, params)
            except RpcError:
                pass
            return None
        try:
            result = self._dispatch(method, params)
        except RpcError as exc:
            return self._error(request_id, exc)
        except Exception as exc:  # never leak a traceback to the client
            return self._error(request_id, RpcError(INTERNAL_ERROR, str(exc)))
        return {"jsonrpc": JSONRPC, "id": request_id, "result": result}

    def _dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "initialize":
            return self.initialize(params)
        if method == "tools/list":
            return {"tools": self.list_tools()}
        if method == "tools/call":
            return self.call_tool(
                params.get("name"),
                params.get("arguments") or {},
                identity=params.get("identity"),
                idempotency_key=params.get("idempotencyKey"),
            )
        if method == "notifications/initialized":
            return {}
        raise RpcError(METHOD_NOT_FOUND, f"unknown method {method!r}")

    @staticmethod
    def _error(request_id: Any, rpc_error: RpcError) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC, "id": request_id, "error": rpc_error.error_payload()}

    # -- MCP methods -------------------------------------------------------------
    def initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        requested = (params or {}).get("protocolVersion")
        if requested not in SUPPORTED_REVISIONS:
            raise RpcError(
                INVALID_PARAMS,
                f"unsupported protocolVersion {requested!r}; supported: "
                f"{', '.join(SUPPORTED_REVISIONS)}",
            )
        return {
            "protocolVersion": PINNED_REVISION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": self.SERVER_NAME, "version": self.SERVER_VERSION},
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return list(TOOL_SCHEMAS)

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        identity: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        schema = self._schema_for(name)
        if schema is None:
            available = ", ".join(tool["name"] for tool in TOOL_SCHEMAS)
            return self._text(
                f"unknown tool {name!r}; available tools: {available}", is_error=True)

        self._validate(name, schema["inputSchema"], arguments)

        # A retry with a seen key is the same call: replay it, do not re-run it.
        replay_key = (
            (identity, name, idempotency_key) if idempotency_key is not None else None)
        if replay_key is not None and replay_key in self._idempotency:
            return self._idempotency[replay_key]

        # Per-session sequence policy, BEFORE the ERP is touched (SPEC limit L3).
        self.session.observe(identity, name)

        try:
            result = self._execute(name, arguments, identity)
        except (KeyError, ValueError) as exc:
            # Business failures are tool results with model-facing text, not protocol
            # errors: the model reads them and changes its next call.
            message = exc.args[0] if exc.args else str(exc)
            return self._text(str(message), is_error=True)

        if replay_key is not None:
            self._idempotency[replay_key] = result
        return result

    def handle_http(
        self, body: bytes, headers: dict[str, str]
    ) -> tuple[int, dict[str, str], bytes]:
        try:
            message = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            payload = self._error(None, RpcError(PARSE_ERROR, "parse error: body is not valid JSON"))
            return 400, {"Content-Type": "application/json"}, json.dumps(payload).encode()
        if isinstance(message, list):
            payload = self._error(
                None, RpcError(INVALID_REQUEST, "batch requests are not supported"))
            return 400, {"Content-Type": "application/json"}, json.dumps(payload).encode()
        response = self.handle(message)
        if response is None:
            return 202, {"Content-Type": "application/json"}, b""
        return 200, {"Content-Type": "application/json"}, json.dumps(response).encode()

    # -- helpers -----------------------------------------------------------------
    @staticmethod
    def _schema_for(name: str) -> dict[str, Any] | None:
        for tool in TOOL_SCHEMAS:
            if tool["name"] == name:
                return tool
        return None

    @staticmethod
    def _validate(name: str, schema: dict[str, Any], arguments: dict[str, Any]) -> None:
        if not isinstance(arguments, dict):
            raise RpcError(INVALID_PARAMS, f"{name}: arguments must be a JSON object")
        properties = schema["properties"]
        extra = sorted(key for key in arguments if key not in properties)
        if extra:
            raise RpcError(
                INVALID_PARAMS,
                f"{name}: unexpected argument(s) {', '.join(extra)}; "
                f"allowed: {', '.join(sorted(properties))}",
            )
        missing = [key for key in schema["required"] if key not in arguments]
        if missing:
            raise RpcError(
                INVALID_PARAMS,
                f"{name}: missing required argument(s) {', '.join(missing)}",
            )
        for key, value in arguments.items():
            expected = properties[key].get("type")
            if expected == "string" and not isinstance(value, str):
                raise RpcError(
                    INVALID_PARAMS,
                    f"{name}: argument {key!r} must be a string, got {type(value).__name__}",
                )
            if expected == "number" and (
                isinstance(value, bool) or not isinstance(value, (int, float))
            ):
                raise RpcError(
                    INVALID_PARAMS,
                    f"{name}: argument {key!r} must be a number, got {type(value).__name__}",
                )
        if name == "create_purchase_order" and arguments.get("amount", 1) <= 0:
            raise RpcError(
                INVALID_PARAMS,
                "create_purchase_order: argument 'amount' must be positive",
            )

    def _execute(
        self, name: str, arguments: dict[str, Any], identity: str | None
    ) -> dict[str, Any]:
        if name == "get_open_orders":
            rows = self.erp.open_orders(arguments["customer"], identity=identity)
            return self._text(json.dumps(rows))
        if name == "get_vendor_balance":
            vendor = arguments["vendor"]
            balance = self.erp.vendor_balance(vendor, identity=identity)
            return self._text(json.dumps({"vendor": vendor, "balance": balance}))
        if name == "create_purchase_order":
            order = self.erp.create_purchase_order(
                arguments["reference"],
                arguments["vendor"],
                float(arguments["amount"]),
                identity=identity,
            )
            return self._text(json.dumps(order))
        raise RpcError(METHOD_NOT_FOUND, f"unknown tool {name!r}")  # unreachable

    @staticmethod
    def _text(text: str, *, is_error: bool = False) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": text}], "isError": is_error}


if __name__ == "__main__":  # tiny demo; the contract is in tests/
    from fake_erp import FakeErp

    server = McpServer(FakeErp())
    print("tools:", [tool["name"] for tool in server.list_tools()])
    print("orders:", server.call_tool(
        "get_open_orders", {"customer": "Northwind Traders"}, identity="demo")["content"][0]["text"])
    print("balance:", server.call_tool(
        "get_vendor_balance", {"vendor": "Acme Supplies"})["content"][0]["text"])
