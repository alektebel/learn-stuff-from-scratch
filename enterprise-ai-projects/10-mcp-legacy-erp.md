# 10 — Custom MCP server for legacy ERPs

## What it is

A Model Context Protocol server exposing a legacy ERP as tools an agent can call — reading
data, and performing updates — with the safety properties that make "an LLM can write to
SAP" a sentence someone will sign off on.

## What it actually demonstrates

That you can connect agents to what enterprises actually run on — correct. But the
interesting half is not the protocol. MCP is a JSON-RPC transport with a tool schema; a
working server is a day's work once you have read the spec.

The half that demonstrates something is **tool design under an unreliable caller**. The
model will call your tools with plausible-looking wrong arguments, will retry after a
timeout without knowing whether the first call succeeded, and will chain calls in orders
you did not anticipate. Every safety property has to hold against that, and none of it is
in the MCP spec.

## The substrate

**SAP's own trial image**, which exists and is free:

```
docker pull sapse/abap-cloud-developer-trial:<tag>
```

Details that matter: it is an ABAP Platform on SAP HANA 2.0, pre-configured with Fiori
launchpad and sample applications, community-supported only. The bundled licence lasts
**three months**; extend it by logging in as `SAP*` on client `000`, running transaction
`SLICENSE`, taking the hardware key and requesting a licence from minisap for system
`A4H`. Expect a large image and a long first start.

If that is too heavy, **ERPNext** or **Odoo** give you a real ERP domain model — chart of
accounts, purchase orders, stock movements, approval workflows — with a sane API, and the
domain modelling problem is the same. You lose the specific pain of SAP's interfaces,
which is a real loss but not a fatal one.

Reuse the hostile Oracle/SQL Server substrate from project 1 if you are doing both; the
database is the expensive part to set up.

## The decisions

**Read-only first, and mean it.** Ship a server that cannot write, use it for a week, and
only then design writes. Most of the value is in retrieval and most of the risk is in
mutation, and separating them in time is how you learn which is which.

**Tool granularity.** One `run_query(sql)` tool is trivially expressive and hands the
model arbitrary SQL against a production ERP. Fifty narrow tools (`get_open_orders`,
`get_vendor_balance`) are safe, bounded, and the model will constantly want the one you
did not write. The workable middle — a small set of parameterised, schema-validated
queries with an explicit allowlist of tables and columns — is more work than either
extreme and is the right answer.

**Idempotency, because the caller will retry.** The model calls `create_purchase_order`,
your call takes 40 seconds, the client times out, the model calls it again. Without a
client-supplied idempotency key threaded into the ERP transaction, you have two purchase
orders. This is exactly the mechanism from project 6, and this is where it stops being an
exercise.

**Confirmation and its limits.** MCP's elicitation and the human-in-the-loop patterns let
you require approval before a mutation. That is necessary and it is not sufficient: a
human approving their fortieth confirmation dialog of the morning approves whatever is in
front of them. Design the confirmation to show the *diff* — what will change, from what to
what — not the tool name and arguments.

**Authorisation identity.** Does the ERP see the agent's service account or the end user?
A service account with rights to everything means your access control is entirely in your
tool layer, and one prompt injection is a privilege escalation. Passing the user's
identity through is correct and hard, and it is what an enterprise security review will
ask about first.

**Errors are prompts.** Your error strings go into the model's context and shape its next
action. `ORA-00001: unique constraint (SAPSR3.Z_PO_UK) violated` teaches it nothing;
"a purchase order with this reference already exists — do not retry, ask the user" changes
the outcome. Treat error text as part of the interface.

## Where it breaks

The model finds a legitimate sequence of individually-safe calls that is not safe as a
sequence. Read the vendor list, read balances, create a payment run — each tool call is
permitted, the composition is fraud.

Per-tool authorisation cannot see this because it is a property of the trajectory, not the
call. You need either a session-level policy over sequences, or a hard rule that mutations
require an approval that carries the full context of the session so far. Knowing that this
is a real class of problem, and that per-call checks do not address it, is the most
valuable thing this project can teach you.

## Resources

- Model Context Protocol specification — <https://modelcontextprotocol.io/specification/> `[v]`. Latest stable revision **2025-11-25** (previous: 2025-06-18); it adds OpenID Connect Discovery for authorization-server discovery, elicitation over URLs, and experimental durable tasks. Pin a revision in your README.
- MCP servers and SDKs — <https://github.com/modelcontextprotocol>
- SAP ABAP Cloud Developer Trial image — <https://hub.docker.com/r/sapse/abap-cloud-developer-trial> `[v]`; documentation <https://github.com/SAP-docs/abap-platform-trial-image> `[v]`
- ERPNext — <https://github.com/frappe/erpnext>
- OWASP Top 10 for LLM Applications — <https://genai.owasp.org/> — excessive agency and insecure plugin/tool design are the two entries this project is about.
- `aws-from-scratch/iam.py` in this repo — policy evaluation, where explicit deny beats everything in any order. If you are building the authorisation layer rather than delegating it, that rule is the one to start from.
