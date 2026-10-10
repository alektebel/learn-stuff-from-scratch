"""MCP From Scratch — stage 9: a confirmation that shows the diff, and whose identity it runs as

DESIGN DECISION — the confirmation shows the DIFF, not the tool call.
    The elicitation message is built from `erp.diff(change)`: `"change quantity
    from 10 to 25"`, one line per field, plus the reference. This is the whole
    argument of the stage, and it is worth stating as the guide does: a dialog
    showing `apply_change({"quantity": 25})` tells a person what the agent wanted,
    not what will change, and a person who is shown the arguments of a tool call
    cannot tell a change that matters from one that does not — so the fortieth
    dialog of the morning is approved without being read. A person shown `from 10
    to 25` on a purchase order they know is looking at the world, and a diff over
    a real value is the only thing that makes "read before you approve" possible.

DESIGN DECISION — an approval must be affirmative, not the absence of a no.
    The elicitation's requested schema asks for an explicit boolean
    (`{"type": "object", "properties": {"approve": {"type": "boolean"}},
    "required": ["approve"]}`), and a client answer that does not carry
    `content["approve"] is True` counts as a DECLINE. A truthy string is not a
    boolean and an empty `content` is not a yes: the moment "no answer" can be
    read as "yes", the dialog is decoration that also logs consent.

DESIGN DECISION — `decline` and `cancel` both leave the ERP untouched, and read
differently in the log.
    Both are `isError: true` with a message saying the change did not happen, and
    `applied: false` in `.approvals`. They differ only in the wording — `"the
    user declined"` versus `"the user cancelled the request"` — because the
    operator reading the log tomorrow needs to know whether a person said no to
    this change or walked away from the dialog.

DESIGN DECISION — the approval is bound to the DIFF, not to the call.
    `diff_token(diff)` is sha256 over the canonical diff, and
    `require(change, session, token=...)` accepts a token ONLY when it equals the
    token of the diff that is about to be applied. An approval for `quantity
    10 -> 25` replayed for `10 -> 250` is refused, with a message naming both the
    reason and the state that changed. That is the difference between a
    confirmation dialog and authorisation: a token over the tool name and its
    arguments would still be replayable against a state that has moved on since.

DESIGN DECISION — the identity comes from the session, never from the arguments.
    `session["identity"]` must be a non-empty string: a mutation with no identity
    is `isError: true` (`"denied: no identity on this session"`) and the change is
    not proposed at all — nothing is shown to a person until the server knows who
    it is asking on behalf of. The tool declares no argument named `identity`, so a
    caller trying to claim one is refused by `tools/call` with -32602 rather than
    being believed.

TODO: implement

    diff_token(diff) -> str
        sha256 over the canonical diff (json.dumps(diff, sort_keys=True,
        separators=(",", ":"))), hex. Two identical diffs give the same string; a
        different `from` or `to` gives a different one. This is the approval's
        identity.

    class Confirmation
        Confirmation(erp, request)
            `request(message, requested_schema) -> {"action": ..., "content"?: ...}`
            is the client's half of `elicitation/create`, injected so a caller can
            play a person.
        .approvals -> list[dict]
            One entry per round: {"token", "diff", "identity", "action",
            "applied"}. `action` is the EFFECTIVE action — "accept", "decline",
            "cancel", or "refused" for a token that did not match the diff — and
            `applied` is True only for the round that actually wrote to the ERP.
            A round with no identity is not a round and is not recorded.
        .pending -> dict[token, dict]
            The change each accepted token was issued for, by the fields that
            identify it ("reference", "vendor_id", "item_id", "quantity"), so a
            replayed token can be checked against the change it was issued for:
            a token is honoured only when it is the token of the diff about to be
            applied AND the round that issued it was applied.
        propose(change, session) -> dict
            The elicitation round: refuse if the session has no identity, show
            `erp.diff(change)`, ask for the boolean, and apply the change only on
            an affirmative accept, as `session["identity"]`. Returns a
            `tools/call` result: text content naming the reference and the new
            status, or `isError: true` with the reason. A business failure from
            `erp` is text, never a crash.
        require(change, session, *, token=None) -> dict
            `propose` when there is no token; otherwise re-validate the token
            against the diff this change would make and apply only on a match. A
            token from a round that was declined, cancelled or refused is not an
            approval and is refused too.

    install(server, confirmation) -> None
        Registers the mutating tool "apply_change" through
        `server.add_tool(name, description, input_schema, fn, mutates=True)`.
        The schema declares `change` (required) and the optional `approvalToken`,
        and `additionalProperties: false`; it must NOT declare an `identity`.

    format_diff(diff) -> str
        The human-readable lines shown in the prompt: one line per field, from
        where to where (`"change quantity from 10 to 25"`). A field that does not
        exist yet reads `nothing`.
"""

APPROVAL_SCHEMA = {}                 # TODO: the elicitation's requested schema

APPLY_CHANGE_SCHEMA = {}             # TODO: the tool's inputSchema


def diff_token(diff):
    raise NotImplementedError("stage 9: implement diff_token()")


def format_diff(diff):
    raise NotImplementedError("stage 9: implement format_diff()")


class Confirmation:
    def __init__(self, erp, request):
        raise NotImplementedError("stage 9: implement Confirmation")

    def propose(self, change, session):
        raise NotImplementedError("stage 9: implement Confirmation.propose()")

    def require(self, change, session, *, token=None):
        raise NotImplementedError("stage 9: implement Confirmation.require()")


def install(server, confirmation):
    raise NotImplementedError("stage 9: implement install()")
