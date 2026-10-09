# mcp-from-scratch — an MCP server in front of a legacy ERP

## What it is

A Model Context Protocol server that exposes a legacy ERP as tools an agent can call:
read the open orders of a customer, read a vendor balance, create a purchase order.
The protocol is JSON-RPC 2.0 over the streamable HTTP transport. The ERP itself is a
deterministic in-memory fake (`fake_erp.py`) that mirrors the ERPNext/Odoo domain shape
— customers, open sales orders, vendor balances, purchase orders — because a real ERP
needs Docker and a network this environment does not have.

**Pinned MCP revision: 2025-11-25** (previous stable: 2025-06-18). Everything the
server implements is defined by that revision, and `initialize` fails closed on
revisions it does not know.

## What it demonstrates

- Protocol plumbing: the JSON-RPC dispatch, the initialize/version negotiation,
  tools/list with schemas, and the streamable-HTTP framing. This half is a day's work
  once you have read the spec — the tests make you do it exactly right.
- Tool design under an unreliable caller. The caller sends plausible-looking wrong
  arguments, retries after a timeout without knowing whether the first call landed,
  and chains calls in orders you did not anticipate. Every safety property below has
  to hold against that caller; none of it is in the MCP spec.
- The two error channels: JSON-RPC protocol errors (numeric codes) versus tool
  results with `isError` and a sentence written for whoever will read it next.
- Per-call checks versus per-session checks: some properties are properties of the
  trajectory, not of any single call.

## The interface

Infrastructure (provided, implemented — `fake_erp.py`):

```python
class PolicyViolation(Exception): ...          # a forbidden sequence, not a bad call

class Erp(Protocol):
    def open_orders(self, customer, *, identity=None) -> list[dict]: ...
    def vendor_balance(self, vendor, *, identity=None) -> float: ...
    def create_purchase_order(self, reference, vendor, amount, *, identity=None) -> dict: ...
    @property
    def orders(self) -> tuple[dict, ...]: ...  # everything created so far

class FakeErp:   # deterministic; every public call logs (method, args, identity) to .calls
```

Infrastructure (provided, implemented — `mcp_server.py`):

```python
JSONRPC = "2.0"; PARSE_ERROR = -32700; INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601; INVALID_PARAMS = -32602; INTERNAL_ERROR = -32603
PINNED_REVISION = "2025-11-25"; SUPPORTED_REVISIONS = ("2025-11-25", "2025-06-18")

class RpcError(Exception):
    def __init__(self, code, message, data=None): ...   # .error_payload() -> error object

TOOL_SCHEMAS  # get_open_orders, get_vendor_balance, create_purchase_order — JSON-Schema
              # input schemas, additionalProperties: false everywhere

class SessionState:
    def observe(self, identity, tool) -> None   # raises PolicyViolation on a forbidden
                                                # sequence; records allowed calls
```

CORE (the learner implements; all currently `raise NotImplementedError`):

```python
class McpServer:
    def __init__(self, erp)                                        # provided
    def handle(self, message) -> dict | None                       # dispatch one parsed JSON-RPC message
    def initialize(self, params) -> dict                           # revision handshake
    def list_tools(self) -> list[dict]                             # tools/list payload
    def call_tool(self, name, arguments, *, identity=None,
                  idempotency_key=None) -> dict                    # validate, authorise, execute
    def handle_http(self, body: bytes, headers: dict)
        -> tuple[int, dict, bytes]                                 # (status, headers, body)
```

Tool results use the MCP convention `{"content": [{"type": "text", "text": ...}],
"isError": bool}`. There is no `run_query(sql)` and there never will be.

## Acceptance

1. **A1 — initialize negotiates the revision.** A client asking for `2025-06-18` is
   answered with `2025-11-25`; asking for `2025-11-25` is echoed; the result carries
   `capabilities.tools` and `serverInfo.name`. An unknown revision raises
   `RpcError(INVALID_PARAMS)` whose message names the supported revisions (fail-closed,
   stricter than the spec's graceful fallback — a named decision below).
   (tests 7, 8)
2. **A2 — tools/list schemas are valid.** The catalog is exactly the three tools; each
   input schema is an object with `additionalProperties: false` and
   `required ⊆ properties`. (tests 3, 9)
3. **A3 — a read call returns FakeErp data.** `get_open_orders`/`get_vendor_balance`
   return successful tool results whose content carries the fake's data. (test 10)
4. **A4 — unknown method answers -32601** with the original `id`; a notification (no
   `id`) produces no response. (test 11)
5. **A5 — unknown tool answers with a structured error.** A tool result with
   `isError: true` and model-facing text naming the tool — not a protocol error, not a
   traceback. (test 12)
6. **A6 — invalid params answer -32602 with a model-facing message**: missing fields
   are named in the message so the next call can be corrected. (test 13)
7. **A7 — streamable HTTP framing.** A malformed JSON body is HTTP 400 with JSON-RPC
   error -32700 (parse error), response Content-Type `application/json`. (test 14)

## Limit cases

Each of these is a test a naive implementation fails.

- **L1 — the caller will retry (idempotency).** `create_purchase_order` twice with the
  same `idempotency_key` produces one purchase order, and the retry replays the first
  result instead of surfacing the duplicate-reference failure; a different key produces
  a second order. The fake ERP itself rejects duplicate references, so forwarding the
  retry blindly fails the test. (test 15)
- **L2 — identity is the end user, not a service account.** The `identity` given to
  `call_tool` is what the ERP call log records. A service account with rights to
  everything makes every access control live in the tool layer, and one injection
  becomes a privilege escalation. (tests 6, 16)
- **L3 — a sequence of individually-allowed calls is not allowed as a sequence.**
  Read the open orders, read the vendor balances, then create the purchase order: the
  recon-then-move pattern (in the literature: vendor list, balances, payment run) is
  refused with `PolicyViolation` for that identity's session, while each call alone is
  allowed and other identities are unaffected. `SessionState` is provided; consulting
  it from `call_tool` before dispatching is the exercise. (tests 4, 17)
- **L4 — no SQL tool, no smuggled SQL.** `run_query` is not in the catalog; calling it
  returns an `isError` result and executes nothing. An `sql` argument added to a real
  tool is a schema violation (-32602), because every schema sets
  `additionalProperties: false`. (tests 3, 18)

## Out of scope / blocked

- **A real ERP substrate** (ERPNext, Odoo, SAP trial image): needs Docker and network
  access this environment lacks. `FakeErp` mirrors the domain shape instead; the
  mapping exercise to a real API is documented in RESOURCES.md.
- **SSE streaming, sessions (`Mcp-Session-Id`), server-initiated requests, OpenID
  Connect discovery**: the transport features beyond a single POST. The 2025-11-25
  revision adds them; the learning value of this module is in the tool and safety
  layer, so the transport is only as thick as the tests need. (Blocked, not ignored.)
- **Elicitation / human approval with diffs**: needs a client to render the dialog.
  The design decision it would encode is named here and not built: show the *diff*
  (what changes, from what to what), not the tool name and arguments — a human
  approving their fortieth confirmation dialog of the morning approves whatever is in
  front of them.
- **JSON-RPC batching**: removed from MCP in the 2025-06-18 revision, so a correct
  server rejects batch arrays; not yet covered by a test.
- **Amount validation, approval workflows, per-vendor authorization rules**: extension
  territory; the current contract is the MVP plus the four limit cases.

## How to run

```bash
cd mcp-from-scratch
/tmp/opencode/venv/bin/python -m pytest -q
```

(any Python 3.12+ with pytest works). Expected today: **6 passed, 12 xfailed**, exit 0 —
the xfailed tests are the learner's work; each one passes once the corresponding core
method is implemented correctly and fails if it is implemented wrongly.

## Design decisions

- **Read-only first is the guide's rule; this contract ships one write tool anyway.**
  The guide is right that most of the value is retrieval and most of the risk is
  mutation, and that a real deployment should run read-only for a week before designing
  writes. This module cannot teach idempotency or the sequence failure without a
  mutation to guard, so it includes exactly one write tool and makes the guards around it
  testable. Cost: the learner meets mutation from day one, so the sequencing the guide
  would impose has to be stated here instead. Build the read-only server first; add the
  guarded write once the reads are boring.
- **Pin a revision (2025-11-25) and fail closed on unknown ones.** The spec moves —
  batching was removed in 2025-06-18; 2025-11-25 adds OIDC discovery for authorization
  servers, elicitation over URLs and experimental durable tasks — so un-pinned behavior
  is untestable behavior. Cost: stricter than the spec's graceful negotiation, so a
  hypothetical future client is refused instead of downgraded. Deliberate.
- **Two error channels, on purpose.** Protocol violations are `RpcError` with JSON-RPC
  codes; business failures (unknown vendor, unknown tool, refused sequence) are tool
  results with `isError` and a sentence written for the model's context. Cost: callers
  handle two channels; worth it because error strings shape the next action —
  "a purchase order with this reference already exists — do not retry, ask the user"
  changes behavior, a constraint name does not.
- **The idempotency key is a `call_tool` argument, not a tool argument.** It routes to
  replay logic before the ERP is touched, so retries never reach the ERP. Cost: the
  server holds state keyed by identity and key, and this MVP's replay window is
  unbounded.
- **The sequence policy is default-on and coarse.** Refusing any reads-then-write
  pattern produces false refusals of legitimate flows (check a balance, then order).
  Cost accepted on purpose: the lesson of L3 is that per-call authorization cannot see
  trajectories, and the honest fixes — session-scoped approval that carries the full
  context, or showing the human the diff — need a client this module does not have.
- **Identity flows through as data.** The ERP records *who* called, which is what an
  enterprise security review asks about first. Cost: a real ERP would have to
  authorize per user; the fake only records.
- **Tool granularity stays narrow.** Three schema-validated tools beat one
  `run_query(sql)`: expressiveness against a production ERP is the vulnerability. The
  model will constantly want the tool you did not write; the answer is more narrow
  tools or an allowlisted, parameterised query layer — never arbitrary SQL.
- **Determinism everywhere.** The fake has no clock and no randomness; the same test
  run produces the same log, every time.
- Learning content is cited and restated, never copied — see RESOURCES.md.
