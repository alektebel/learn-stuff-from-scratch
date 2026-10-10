"""MCP From Scratch — stage 8: idempotency, because the caller will retry

DESIGN DECISION — the key is a required argument, declared in the schema.
    The failure this stage exists for is the quiet one: the write landed and the
    response was lost, so the caller tries again. The caller cannot tell the two
    cases apart — that is the definition of the problem — so the server must be
    able to recognise the second call, which means the first call had to carry
    something stable. That something is the key, and it is the CALLER's to pick:
    a server that invents a key when the model forgot one dedupes nothing at all,
    because the retry arrives with a fresh invention. So the key is in
    `required`, and a model that omits it is told -32602 with the parameter's
    name, in the same breath as any other bad argument.

DESIGN DECISION — the same key with the same arguments is the SAME call, byte
for byte.
    The client that timed out cannot tell a replay from a first answer, which is
    the whole point: the second response must be the first response, not a
    re-rendering of whatever the world looks like now. It also creates nothing.
    The assertion that matters is not on the text but on the world: the ERP
    holds ONE order, and `Ledger.reused` counts the calls answered from the
    ledger instead of the ERP.

DESIGN DECISION — the same key with DIFFERENT arguments is a client bug, not a
second operation.
    Only one of the two requests can be the one the caller meant, and the server
    has no way to pick. Applying the second one silently changes the world under
    a key that has already been accounted for; rejecting it has to be loud, and
    its text is part of the interface, because the text is what the model reads
    next: it says the key was already used for a different request, and that
    retrying will not help — do not retry, ask the user.

DESIGN DECISION — a business failure is an outcome too.
    If the ERP refuses the order (an unknown vendor, a duplicate reference, a
    negative quantity), the write was attempted and the world said no. That is
    an answer, and the key is spent: a retry gets the same refusal instead of a
    second attempt, so a client stuck in a retry loop cannot turn one refusal
    into a storm of them. A VALIDATION failure is different: -32602 means the
    arguments never reached the tool, nothing was attempted, so there is nothing
    to remember and the key is NOT consumed.

DESIGN DECISION — the fingerprint is a canonical serialization, and it is
stable across processes.
    The same arguments in a different dict order are the same request, so the
    digest is taken over JSON with sorted keys, never over the dict's iteration
    order and never over `hash()`, whose value changes with the process salt —
    a ledger that forgets its own keys across restarts protects nothing.

TODO: implement

    CREATE_ORDER_SCHEMA
        The inputSchema the model sees:
            {"type": "object",
             "properties": {"idempotencyKey": {"type": "string", "minLength": 8},
                            "reference": {"type": "string"},
                            "vendor_id": {"type": "string"},
                            "item_id": {"type": "string"},
                            "quantity": {"type": "integer"}},
             "required": ["idempotencyKey", "reference", "vendor_id", "item_id",
                          "quantity"]}
        The key is declared, not implied: a schema that hides it makes the model
        guess, and a guessed key is a new key.

    class Ledger:
        __init__(self, erp)
            The ERP the tool writes to. A fake Erp with the contract's methods is
            enough; nothing here imports the server.
        .applied -> dict[key, dict]
            key -> {"fingerprint": str, "outcome": "ok" | "error",
                    "result" | "message": the response the caller got}
        .reused -> int
            How many calls were answered from the ledger instead of the ERP.
        create_order(params, session) -> dict
            A text result in the stage 4 shape:
                {"content": [{"type": "text", "text": str}], "isError": bool}
            - validates before anything else: a missing required parameter, or an
              idempotencyKey that is not a string of at least 8 characters,
              raises ProtocolError(-32602) naming the parameter, with
              data={"tool": "create_purchase_order"}; the ERP is untouched;
            - the response text names the order reference and its status, and the
              first status is "draft" (stage 9 approves; stage 10 polices the
              trajectory), so the mutation path is erp.draft(...) then
              erp.apply(...) with the session's identity;
            - key seen with the same fingerprint: return the stored response
              (used + 1), write nothing;
            - key seen with a different fingerprint: an isError result telling
              the caller not to retry;
            - erp.draft/erp.apply raising ErpError is a business failure: store
              it as outcome "error" and return it as an isError result.

    install(server, ledger) -> None
        Registers the mutating tool "create_purchase_order" with the schema above
        and ledger.create_order as its function, via
        server.add_tool(name, description, input_schema, fn, mutates=True).
"""

CREATE_ORDER_SCHEMA = {}             # TODO: the schema the model sees


class Ledger:
    def __init__(self, erp):
        raise NotImplementedError("stage 8: implement Ledger")

    def create_order(self, params, session):
        raise NotImplementedError("stage 8: implement Ledger.create_order()")


def install(server, ledger):
    raise NotImplementedError("stage 8: implement install()")
