"""mcp_server.py — a Model Context Protocol server in front of a legacy ERP.

The protocol half is JSON-RPC 2.0 over streamable HTTP. The interesting half is the
safety layer around tools that write to an ERP for an unreliable caller: retries,
plausible-looking wrong arguments, and call chains nobody anticipated.

LEARN mode: everything on ``McpServer`` below the constructor is CORE and raises
NotImplementedError — the tests in ``tests/`` define what each method must make true.
``RpcError``, ``TOOL_SCHEMAS`` and ``SessionState`` are provided infrastructure; use
them, do not re-implement them. The ERP substrate lives in ``fake_erp.py``.

Pinned MCP revision: 2025-11-25 (previous stable: 2025-06-18). See SPEC.md.
"""
from __future__ import annotations

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
# initialize() negotiates: a client asking for a revision we support is answered with
# PINNED_REVISION (echoed if it asked for exactly it); anything else fails closed.
PINNED_REVISION = "2025-11-25"
SUPPORTED_REVISIONS = ("2025-11-25", "2025-06-18")


class RpcError(Exception):
    """A JSON-RPC protocol-level error (infrastructure: implemented).

    Protocol violations (bad revision, unknown method, invalid params) raise this;
    tool-level business failures are *not* this — they are tool results with
    ``isError: true``. Two channels, on purpose (SPEC, design decisions).
    """

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def error_payload(self) -> dict[str, Any]:
        """The ``error`` object of a JSON-RPC error response."""
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            error["data"] = self.data
        return error


# --- Tool catalog (infrastructure: declarative data) ----------------------------
# Three tools. Narrow, parameterised, schema-validated. There is no run_query(sql)
# and there never will be — expressiveness is the vulnerability (SPEC, limit L4).
# Descriptions are written for the model that will read them.
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


# --- Session state and the sequence policy (infrastructure: implemented) --------
class ForbiddenSequence:
    """A mutation that is refused once the listed reads happened in the same session."""

    def __init__(self, reads: tuple[str, ...], mutation: str) -> None:
        self.reads = tuple(reads)
        self.mutation = mutation


class SessionState:
    """Per-identity memory of the tools called so far, plus the policy over sequences.

    Per-call authorisation cannot see trajectories; this object can (SPEC, limit L3).
    The learner must consult it from ``call_tool`` — call ``observe`` BEFORE
    dispatching, so a refused mutation is never executed and never recorded.
    """

    DEFAULT_RULES = (
        # the canonical pattern from the literature: recon the vendors, then move money
        ForbiddenSequence(("list_vendors", "get_vendor_balance"), "create_payment_run"),
        # the same pattern expressed with this server's own tools
        ForbiddenSequence(("get_open_orders", "get_vendor_balance"), "create_purchase_order"),
    )

    def __init__(self, rules: list[ForbiddenSequence] | None = None) -> None:
        self.rules = list(SessionState.DEFAULT_RULES if rules is None else rules)
        self._history: dict[str, list[str]] = {}

    def observe(self, identity: str | None, tool: str) -> None:
        """Check the sequence policy for this call, then record it.

        Raises PolicyViolation if calling ``tool`` now completes a forbidden
        sequence for this identity's session.
        """
        history = self._history.setdefault(identity if identity is not None else "?", [])
        for rule in self.rules:
            if tool == rule.mutation and all(read in history for read in rule.reads):
                raise PolicyViolation(
                    "refused: this session already read "
                    f"{', '.join(rule.reads)}; calling {rule.mutation} now is the "
                    "recon-then-move pattern — start a new session or ask for approval"
                )
        history.append(tool)


# --- The server (CORE: the learner implements every method below) ---------------
class McpServer:
    """MCP server surface: JSON-RPC 2.0, streamable HTTP transport.

    ``handle`` dispatches one *parsed* JSON-RPC message. ``handle_http`` owns the
    bytes: framing, Accept headers, parse errors. Tool results use the MCP
    convention ``{"content": [{"type": "text", "text": ...}], "isError": bool}``.
    """

    def __init__(self, erp: Erp) -> None:
        self.erp = erp
        self.session = SessionState()

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Dispatch one JSON-RPC message; return the response dict, or None for
        notifications (messages without an id). Unknown method -> error -32601."""
        raise NotImplementedError("handle(): JSON-RPC dispatch (SPEC A4)")

    def initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Revision handshake. Supported revision -> result with protocolVersion,
        capabilities (tools) and serverInfo. Unknown revision -> RpcError."""
        raise NotImplementedError("initialize(): revision negotiation (SPEC A1)")

    def list_tools(self) -> list[dict[str, Any]]:
        """The tool catalog with its JSON-Schemas, for tools/list."""
        raise NotImplementedError("list_tools(): return the catalog (SPEC A2)")

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        identity: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Validate arguments against the schema (-32602), consult the session
        policy, execute against the ERP, and return a tool result dict.

        Unknown tool -> isError result. Mutating tools replay the first result when
        the idempotency_key was seen before. ``identity`` reaches the ERP call log.
        """
        raise NotImplementedError(
            "call_tool(): validate, authorise, execute (SPEC A3, A5, A6, L1-L4)"
        )

    def handle_http(self, body: bytes, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
        """One streamable-HTTP POST: parse the body, dispatch, frame the response.

        Returns (http_status, response_headers, body_bytes). Malformed JSON ->
        400 with error -32700. Notifications -> 202 with no body."""
        raise NotImplementedError("handle_http(): streamable HTTP framing (SPEC A7)")
