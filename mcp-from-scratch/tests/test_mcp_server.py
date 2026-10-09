"""Contract for the MCP-over-ERP server.

Tests 1-6 exercise the provided infrastructure (constants, RpcError, tool catalog,
SessionState, FakeErp) and pass today. Tests 7-18 call the learner's core and are
xfail(NotImplementedError) until it is written; once written correctly they pass,
written wrongly they fail. Every Acceptance (A1-A7) and Limit case (L1-L4) in
SPEC.md maps to at least one test, noted in the docstrings.
"""
import json

import pytest

from fake_erp import FakeErp, PolicyViolation
from mcp_server import (
    INVALID_PARAMS,
    INTERNAL_ERROR,
    INVALID_REQUEST,
    JSONRPC,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    PINNED_REVISION,
    McpServer,
    RpcError,
    SessionState,
    TOOL_SCHEMAS,
)


def make_server() -> McpServer:
    return McpServer(FakeErp())


# --- infrastructure: these must pass now ----------------------------------------

def test_01_jsonrpc_constants():
    """Interface: the JSON-RPC 2.0 error-code table is fixed by its spec."""
    assert JSONRPC == "2.0"
    assert PARSE_ERROR == -32700
    assert INVALID_REQUEST == -32600
    assert METHOD_NOT_FOUND == -32601
    assert INVALID_PARAMS == -32602
    assert INTERNAL_ERROR == -32603


def test_02_rpc_error_shape():
    """Infrastructure: RpcError carries code/message/data and builds the error object."""
    err = RpcError(METHOD_NOT_FOUND, "no such method", data={"method": "x/y"})
    assert isinstance(err, Exception)
    assert err.code == METHOD_NOT_FOUND
    assert err.message == "no such method"
    assert err.data == {"method": "x/y"}
    assert "no such method" in str(err)

    plain = RpcError(INVALID_PARAMS, "missing vendor")
    assert plain.data is None
    assert plain.error_payload() == {"code": INVALID_PARAMS, "message": "missing vendor"}


def test_03_tool_catalog_schemas():
    """Acceptance A2 (static half) and limit L4 (static half): three narrow tools,
    valid JSON-Schema input schemas, no run_query anywhere."""
    names = {tool["name"] for tool in TOOL_SCHEMAS}
    assert names == {"get_open_orders", "get_vendor_balance", "create_purchase_order"}
    assert "run_query" not in names
    for tool in TOOL_SCHEMAS:
        assert tool["description"].strip()
        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        for prop in schema["properties"].values():
            assert "type" in prop
        assert set(schema["required"]) <= set(schema["properties"])


def test_04_session_state_refuses_surveillance_sequence():
    """Limit L3, mechanism level: read vendor list + read balances + payment run is
    refused, though each call alone is allowed and identities are isolated."""
    state = SessionState()
    state.observe("u1", "list_vendors")
    state.observe("u1", "get_vendor_balance")
    with pytest.raises(PolicyViolation):
        state.observe("u1", "create_payment_run")

    # each call on its own, in a fresh session, is allowed
    for tool in ("list_vendors", "get_vendor_balance", "create_payment_run"):
        SessionState().observe("u1", tool)

    # an incomplete sequence is not refused; another identity starts clean
    other = SessionState()
    other.observe("u2", "list_vendors")
    other.observe("u2", "create_payment_run")


def test_05_fake_erp_is_deterministic():
    """Infrastructure: no clock, no randomness — identical inputs, identical outputs."""
    erp = FakeErp()
    first = erp.open_orders("Northwind Traders")
    assert first == erp.open_orders("Northwind Traders")
    assert erp.vendor_balance("Acme Supplies") == erp.vendor_balance("Acme Supplies")
    assert erp.orders == erp.orders
    assert FakeErp().vendor_balance("Cortado GmbH") == FakeErp().vendor_balance("Cortado GmbH")
    # seeded data is actually there for the reads the tools will make
    assert [o["reference"] for o in first] == ["SO-1001", "SO-1014"]
    assert erp.vendor_balance("Acme Supplies") == 4200.0


def test_06_fake_erp_calls_log_and_errors():
    """Limit L2, mechanism level: every ERP call records (method, args, identity);
    business errors carry model-facing text."""
    erp = FakeErp()
    created = erp.create_purchase_order("PO-1", "Acme Supplies", 100.0, identity="user:d")
    assert created["reference"] == "PO-1"
    assert (
        "create_purchase_order",
        {"reference": "PO-1", "vendor": "Acme Supplies", "amount": 100.0},
        "user:d",
    ) in erp.calls
    assert len(erp.orders) == 1 and erp.orders[0]["reference"] == "PO-1"

    erp.open_orders("Contoso Ltd", identity="user:d")
    assert erp.calls[-1][0] == "open_orders"
    assert erp.calls[-1][2] == "user:d"

    # duplicate references and unknown entities fail loudly, in words not codes
    with pytest.raises(ValueError, match="already exists"):
        erp.create_purchase_order("PO-1", "Acme Supplies", 5.0)
    with pytest.raises(KeyError, match="unknown vendor"):
        erp.vendor_balance("Nobody SARL")
    with pytest.raises(KeyError, match="unknown customer"):
        erp.open_orders("Vandelay Industries")


# --- core: xfail until the learner implements -----------------------------------

@pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")
def test_07_initialize_negotiates_revision():
    """Acceptance A1: a supported older revision is answered with the pinned one;
    the pinned revision is echoed. The result advertises tools and a server name."""
    server = make_server()
    older = server.initialize(
        {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t"}}
    )
    assert older["protocolVersion"] == PINNED_REVISION
    assert "tools" in older["capabilities"]
    assert older["serverInfo"]["name"]

    current = server.initialize(
        {"protocolVersion": PINNED_REVISION, "capabilities": {}, "clientInfo": {"name": "t"}}
    )
    assert current["protocolVersion"] == PINNED_REVISION


@pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")
def test_08_initialize_rejects_unknown_revision():
    """Acceptance A1 (fail-closed half): an unknown revision is an RpcError naming
    the supported revisions — stricter than the spec's graceful fallback, on purpose."""
    server = make_server()
    with pytest.raises(RpcError) as exc:
        server.initialize(
            {"protocolVersion": "1999-04-01", "capabilities": {}, "clientInfo": {"name": "t"}}
        )
    assert exc.value.code == INVALID_PARAMS
    assert "2025-11-25" in exc.value.message


@pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")
def test_09_list_tools_returns_valid_catalog():
    """Acceptance A2: tools/list answers with the catalog — same names, valid schemas,
    and still no run_query."""
    server = make_server()
    tools = server.list_tools()
    assert {t["name"] for t in tools} == {t["name"] for t in TOOL_SCHEMAS}
    assert all(t in TOOL_SCHEMAS for t in tools)


@pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")
def test_10_read_tools_return_fake_erp_data():
    """Acceptance A3: a read tool call comes back as a successful tool result whose
    content carries the FakeErp data."""
    server = make_server()
    orders = server.call_tool(
        "get_open_orders", {"customer": "Northwind Traders"}, identity="user:d"
    )
    assert not orders.get("isError")
    assert "SO-1001" in json.dumps(orders["content"])

    balance = server.call_tool("get_vendor_balance", {"vendor": "Acme Supplies"})
    assert not balance.get("isError")
    assert "4200" in json.dumps(balance["content"])


@pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")
def test_11_unknown_method_answers_32601():
    """Acceptance A4: unknown methods are JSON-RPC errors with the original id;
    notifications (no id) produce no response at all."""
    server = make_server()
    response = server.handle(
        {"jsonrpc": JSONRPC, "id": 7, "method": "resources/list", "params": {}}
    )
    assert response["jsonrpc"] == JSONRPC
    assert response["id"] == 7
    assert "result" not in response
    assert response["error"]["code"] == METHOD_NOT_FOUND

    assert server.handle({"jsonrpc": JSONRPC, "method": "notifications/initialized"}) is None


@pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")
def test_12_unknown_tool_answers_is_error():
    """Acceptance A5: an unknown tool is a structured tool result with isError, written
    for the model — not a protocol error, not a traceback."""
    server = make_server()
    result = server.call_tool("no_such_tool", {}, identity="user:d")
    assert result["isError"] is True
    text = json.dumps(result["content"])
    assert "no_such_tool" in text
    assert "Traceback" not in text


@pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")
def test_13_invalid_params_answer_32602():
    """Acceptance A6: schema violations are RpcError(-32602) whose message names what
    to fix — the model reads it and corrects the next call."""
    server = make_server()
    with pytest.raises(RpcError) as missing:
        server.call_tool(
            "create_purchase_order", {"vendor": "Acme Supplies"}, identity="user:d"
        )
    assert missing.value.code == INVALID_PARAMS
    assert "reference" in missing.value.message
    assert "amount" in missing.value.message

    with pytest.raises(RpcError) as wrong_type:
        server.call_tool("get_vendor_balance", {"vendor": 42})
    assert wrong_type.value.code == INVALID_PARAMS


@pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")
def test_14_http_parse_error_answers_32700():
    """Acceptance A7: streamable HTTP framing — malformed JSON is HTTP 400 with a
    JSON-RPC parse error, not a 500."""
    server = make_server()
    status, headers, body = server.handle_http(
        b"{not json",
        {"Content-Type": "application/json", "Accept": "application/json"},
    )
    assert status == 400
    payload = json.loads(body)
    assert payload["error"]["code"] == PARSE_ERROR
    assert any(
        k.lower() == "content-type" and v.startswith("application/json")
        for k, v in headers.items()
    )


@pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")
def test_15_idempotency_key_makes_retry_safe():
    """Limit L1: the client will retry. Same key -> one purchase order, and the retry
    replays the first result (no duplicate-reference error). Different key -> a real
    second order."""
    server = make_server()
    arguments = {"reference": "PO-2026-042", "vendor": "Acme Supplies", "amount": 250.0}

    first = server.call_tool(
        "create_purchase_order",
        dict(arguments),
        identity="user:d",
        idempotency_key="retry-safe-1",
    )
    assert not first.get("isError")

    retry = server.call_tool(
        "create_purchase_order",
        dict(arguments),
        identity="user:d",
        idempotency_key="retry-safe-1",
    )
    assert not retry.get("isError"), "same key must replay the first result"
    assert len(server.erp.orders) == 1

    server.call_tool(
        "create_purchase_order",
        dict(arguments, reference="PO-2026-043"),
        identity="user:d",
        idempotency_key="retry-safe-2",
    )
    assert len(server.erp.orders) == 2


@pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")
def test_16_identity_reaches_the_erp_not_a_service_account():
    """Limit L2: the end user's identity given to call_tool is what the ERP records.
    A service account with rights to everything turns one injection into full access."""
    server = make_server()
    server.call_tool(
        "create_purchase_order",
        {"reference": "PO-9", "vendor": "Acme Supplies", "amount": 10.0},
        identity="user:d.heredia",
    )
    method, _args, seen = server.erp.calls[-1]
    assert method == "create_purchase_order"
    assert seen == "user:d.heredia"


@pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")
def test_17_sequence_policy_refuses_recon_then_move():
    """Limit L3, wired: two reads then a write in one session is refused with
    PolicyViolation even though each call alone is allowed — the SessionState is
    provided, consulting it from call_tool is the exercise. Another identity is
    unaffected."""
    server = make_server()
    server.call_tool("get_open_orders", {"customer": "Contoso Ltd"}, identity="user:x")
    server.call_tool("get_vendor_balance", {"vendor": "Acme Supplies"}, identity="user:x")
    with pytest.raises(PolicyViolation):
        server.call_tool(
            "create_purchase_order",
            {"reference": "PO-77", "vendor": "Acme Supplies", "amount": 900.0},
            identity="user:x",
            idempotency_key="k",
        )
    assert not any(
        method == "create_purchase_order" and args.get("reference") == "PO-77"
        for method, args, _identity in server.erp.calls
    ), "a refused mutation must not reach the ERP"
    # a different session never read anything: the same write alone is allowed
    server.call_tool(
        "create_purchase_order",
        {"reference": "PO-78", "vendor": "Acme Supplies", "amount": 900.0},
        identity="user:y",
        idempotency_key="k",
    )


@pytest.mark.xfail(raises=NotImplementedError, reason="core not implemented")
def test_18_sql_is_never_a_tool():
    """Limit L4: run_query does not exist and calling it returns an isError result
    without executing anything; an sql argument smuggled into a real tool is a
    schema violation (-32602), because every schema sets additionalProperties: false."""
    server = make_server()
    refused = server.call_tool(
        "run_query", {"sql": "SELECT * FROM purchase_orders"}, identity="user:d"
    )
    assert refused["isError"] is True
    assert len(server.erp.orders) == 0  # nothing executed

    with pytest.raises(RpcError) as exc:
        server.call_tool(
            "get_vendor_balance",
            {"vendor": "Acme Supplies", "sql": "DROP TABLE purchase_orders"},
            identity="user:d",
        )
    assert exc.value.code == INVALID_PARAMS
