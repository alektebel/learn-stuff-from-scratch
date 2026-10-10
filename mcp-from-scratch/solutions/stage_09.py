"""MCP From Scratch — stage 9: the confirmation shows the diff, and the approval is bound to it

SOLUTION. `install()` registers one mutating tool; the prompt a person reads is
built from `erp.diff(change)`, the token in that dialog is sha256 over the very
same diff, and the mutation runs as `session["identity"]`.
"""

import hashlib
import json

from erp import ErpError

# What the elicitation asks for: an explicit yes, not the absence of a no.
APPROVAL_SCHEMA = {"type": "object",
                   "properties": {"approve": {"type": "boolean"}},
                   "required": ["approve"]}

# The tool's schema. `identity` is deliberately absent: the mutation runs as the
# session's identity, and a parameter a caller may set is a parameter a caller
# may lie in. Stage 4 answers an undeclared parameter with -32602.
APPLY_CHANGE_SCHEMA = {
    "type": "object",
    "properties": {
        "change": {"type": "object", "description": "the change to apply"},
        "approvalToken": {"type": "string",
                          "description": "a token diff_token() issued for this exact diff"},
    },
    "required": ["change"],
    "additionalProperties": False,
}

# The fields that identify a change in .pending.
PENDING_FIELDS = ("reference", "vendor_id", "item_id", "quantity")


def diff_token(diff):
    """The approval's identity: sha256 over the canonical diff, and nothing else."""
    canonical = json.dumps(diff, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _shown(value):
    return "nothing" if value is None else value


def format_diff(diff):
    """One line per field, from where to where — what a person is shown."""
    return "\n".join(f"change {entry['field']} from {_shown(entry['from'])} "
                     f"to {_shown(entry['to'])}"
                     for entry in diff)


def _result(text, *, error=False):
    return {"content": [{"type": "text", "text": text}], "isError": error}


def _answer_parts(answer):
    """An answer is only as good as it is explicit: anything that is not a dict
    with a known action and a dict content is a decline."""
    if not isinstance(answer, dict):
        return "decline", {}
    action = answer.get("action")
    if action not in ("accept", "decline", "cancel"):
        return "decline", {}
    content = answer.get("content")
    return action, (content if isinstance(content, dict) else {})


class Confirmation:
    """The elicitation round: what is shown, what is approved, what is written."""

    def __init__(self, erp, request):
        self.erp = erp
        self.request = request
        self.approvals = []
        self.pending = {}

    # --- the decision ------------------------------------------------------

    def propose(self, change, session):
        identity = self._identity(session)
        if identity is None:
            return _result("denied: no identity on this session", error=True)
        try:
            diff = self.erp.diff(change)
        except ErpError as exc:
            return _result(f"refused: {exc}", error=True)
        token = diff_token(diff)
        reference = change.get("reference")
        answer = self.request(self._message(change, diff), dict(APPROVAL_SCHEMA))
        action, content = _answer_parts(answer)
        if action == "cancel":
            self._record(token, diff, identity, "cancel", False)
            text = f"the user cancelled the request — no change was made to {reference}"
            return _result(text, error=True)
        if action != "accept" or content.get("approve") is not True:
            self._record(token, diff, identity, "decline", False)
            extra = "" if action == "decline" else " (the answer did not carry approve: true)"
            text = f"the user declined — no change was made to {reference}{extra}"
            return _result(text, error=True)
        return self._apply(change, diff, token, identity)

    def require(self, change, session, *, token=None):
        """Propose the change, or re-validate a token against the diff it would
        authorise. A token is an approval of a change of state, not a licence to
        run a tool call."""
        if token is None:
            return self.propose(change, session)
        identity = self._identity(session)
        if identity is None:
            return _result("denied: no identity on this session", error=True)
        try:
            diff = self.erp.diff(change)
        except ErpError as exc:
            return _result(f"refused: {exc}", error=True)
        expected = diff_token(diff)
        if token != expected or token not in self.pending:
            self._record(token, diff, identity, "refused", False)
            if token not in self.pending:
                return _result("refused: this approval token was never approved by "
                               "this session, so there is no change of state it can "
                               "authorise", error=True)
            return _result(self._mismatch(token, diff), error=True)
        return self._apply(change, diff, token, identity)

    # --- the pieces --------------------------------------------------------

    def _apply(self, change, diff, token, identity):
        try:
            order = self.erp.apply(change, identity=identity)
        except ErpError as exc:
            self._record(token, diff, identity, "accept", False)
            return _result(f"the change was approved but could not be applied: {exc}",
                           error=True)
        self.pending[token] = {field: change[field] for field in PENDING_FIELDS
                               if field in change}
        self._record(token, diff, identity, "accept", True)
        return _result(f"applied {order['reference']} — status is {order['status']}")

    def _message(self, change, diff):
        return f"Approve this change to {change.get('reference')}?\n{format_diff(diff)}"

    def _identity(self, session):
        identity = session.get("identity") if isinstance(session, dict) else None
        if isinstance(identity, str) and identity:
            return identity
        return None

    def _mismatch(self, token, diff):
        """Why a token that this session did issue does not authorise this diff."""
        issued = [entry["diff"] for entry in self.approvals if entry["token"] == token]
        before = ({item["field"]: (item["from"], item["to"]) for item in issued[0]}
                  if issued else {})
        moved = []
        for entry in diff:
            old = before.get(entry["field"])
            if old is None:
                moved.append(f"{entry['field']} was not part of the approved change")
            elif old != (entry["from"], entry["to"]):
                moved.append(f"{entry['field']}: approved when it read {old[0]} -> "
                             f"{old[1]}, but this change reads {entry['from']} -> "
                             f"{entry['to']}")
        detail = "; ".join(moved) or "the approved change is not this one"
        return (f"refused: this approval token was issued for a different change — "
                f"{detail}")

    def _record(self, token, diff, identity, action, applied):
        self.approvals.append({"token": token,
                               "diff": [dict(entry) for entry in diff],
                               "identity": identity, "action": action,
                               "applied": bool(applied)})


def install(server, confirmation):
    """The one mutating tool, registered in the server's tool table."""

    def apply_change(arguments, session):
        return confirmation.require(arguments["change"], session,
                                    token=arguments.get("approvalToken"))

    server.add_tool(
        "apply_change",
        "Apply a change to the purchase-order ERP. The change's diff is shown to "
        "the operator for approval before anything is written; the call runs as the "
        "session's identity, never as an identity a caller supplies.",
        APPLY_CHANGE_SCHEMA,
        apply_change,
        mutates=True,
    )
