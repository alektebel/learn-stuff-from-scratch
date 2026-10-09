# RESOURCES.md — reading list

Each entry says why it is worth reading, restated in our own words; nothing here is
copied into the module. `[v]` = confident it exists at this address; `[verify]` =
written from memory, confirm the address or details later.

- **Model Context Protocol specification, revision 2025-11-25** —
  <https://modelcontextprotocol.io/specification/> `[v]` — the contract our
  `handle`/`initialize`/`list_tools` implement: read the lifecycle section
  (initialize and version negotiation), the tools section (schemas, `isError`
  results), and the streamable HTTP transport. **Pin a revision** in anything you
  ship: the spec moves, and un-pinned behavior is untestable behavior. This revision
  adds OpenID Connect discovery for authorization servers, elicitation over URLs, and
  experimental durable tasks.
- **MCP revision 2025-06-18 (previous stable)** —
  <https://modelcontextprotocol.io/specification/2025-06-18> `[verify]` — why our
  `initialize` still accepts it (and answers with the pinned revision); also the
  revision that removed JSON-RPC batching, which is why a correct modern server
  refuses batch arrays.
- **Official SDKs** — <https://github.com/modelcontextprotocol> `[v]` — the reference
  implementations (TypeScript and Python SDKs). Use them to check the semantics you
  hand-rolled — session framing, error mapping — not to copy the implementation.
- **JSON-RPC 2.0** — <https://www.jsonrpc.org/specification> `[v]` — the error-code
  table (-32700/-32600/-32601/-32602/-32603), the `id`/notification rule behind our
  `handle` returning `None`, and the result-vs-error framing MCP inherits unchanged.
- **ERPNext** — <https://github.com/frappe/erpnext> `[v]`; docs
  <https://docs.frappe.io/erpnext> `[verify]` — the real-ERP domain our fake mirrors:
  customers, purchase orders, accounts payable. Its REST API shows the field names and
  document states a real tool layer would map onto narrow tools.
- **Odoo** — <https://www.odoo.com/documentation> `[verify]` — second domain
  reference, and the convenient one: its external API is itself JSON-RPC (the
  `/web/service` endpoints), so mapping our protocol layer onto it is unusually
  direct.
- **SAP ABAP Cloud Developer Trial** — <https://hub.docker.com/r/sapse/abap-cloud-developer-trial>
  `[v]`, docs <https://github.com/SAP-docs/abap-platform-trial-image> `[v]` — the heavy
  alternative substrate (bundled 3-month licence, HANA included, long first start);
  why we did not use it here: this environment has no Docker.
- **OWASP Top 10 for LLM Applications** — <https://genai.owasp.org/> `[v]` — restated,
  "excessive agency" and "insecure plugin/tool design" are exactly this module's limit
  cases: unbounded writes without idempotency, missing end-user identity, blindness to
  call sequences, and over-broad tools.
- **`aws-from-scratch/iam.py` (elsewhere in this repo)** `[v]` — explicit-deny-wins
  policy evaluation; the starting point if you grow `SessionState` from a sequence
  heuristic into a real authorization layer instead of delegating the decision.
