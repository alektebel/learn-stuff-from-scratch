"""MCP From Scratch — stage 10: the trajectory, and the audit line

SOLUTION. One window of writes with two limits, an approval that is bound to a
state, and six audit keys — no clock, no payload. `guard` is the only place that
can refuse before the tool runs, which is why it wraps dispatch rather than the
handler: a policed call must not reach the fn at all.
"""

import json

from stage_01 import result

LIMITS = {"max_mutations": 3, "max_total_quantity": 100}
AUDIT_KEYS = ("code", "id", "identity", "method", "mutations", "ok")


def impact(call):
    """The quantity a write moves. A tool's arguments carry it either directly
    (`{"quantity": 40}`) or inside the change it applies (`{"change": {...}}`),
    because stage 9's tool takes the change — reading only the first shape is how
    a window of `apply_change` calls totals zero and never reaches its ceiling."""
    arguments = call.get("arguments") if isinstance(call, dict) else None
    if not isinstance(arguments, dict):
        arguments = {}
    quantity = arguments.get("quantity")
    if quantity is None:
        change = arguments.get("change")
        quantity = change.get("quantity") if isinstance(change, dict) else None
    if quantity is None and isinstance(call, dict):
        quantity = call.get("change", {}).get("quantity") \
            if isinstance(call.get("change"), dict) else None
    # bool first: isinstance(True, int) is True and a boolean quantity is a bug.
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        return 0
    return abs(quantity)


def _name(call):
    if call.get("tool"):
        return call["tool"]
    change = call.get("change")
    return change.get("kind") if isinstance(change, dict) else "this call"


def _same_call(left, right):
    keep = ("tool", "arguments", "change")
    return (json.dumps({k: left.get(k) for k in keep}, sort_keys=True, default=str)
            == json.dumps({k: right.get(k) for k in keep}, sort_keys=True, default=str))


class SessionPolicy:
    def __init__(self, *, max_mutations=3, max_total_quantity=100):
        self.max_mutations = max_mutations
        self.max_total_quantity = max_total_quantity
        self.generation = 0
        self.window = []
        self.refused = []
        self.approvals = []          # live approvals only
        self.stale = []

    def classify(self, call):
        if call.get("mutates") or "change" in call:
            return "write"
        return "read"

    def _spent(self):
        return sum(entry["quantity"] for entry in self.window)

    def decide(self, session, call):
        if self.classify(call) != "write":
            return {"allowed": True, "reason": "read"}
        identity = session.get("identity") if isinstance(session, dict) else None
        reason = None
        if not isinstance(identity, str) or not identity:
            reason = ("denied: no identity on this session, so there is nobody the "
                      "change can be attributed to")
        elif len(self.window) >= self.max_mutations:
            reason = (f"denied: this session already made {len(self.window)} changes "
                      f"since a person last saw them (the limit is "
                      f"{self.max_mutations}); the whole batch needs one approval "
                      f"that shows every change, not one more call")
        elif self._spent() + impact(call) > self.max_total_quantity:
            seen = ", ".join(entry["tool"] or "?" for entry in self.window) or "nothing"
            reason = (f"denied: the aggregate needs one approval that shows the whole "
                      f"diff — {self._spent()} + {impact(call)} units would exceed "
                      f"this session's ceiling of {self.max_total_quantity} "
                      f"(already this window: {seen})")
        if reason is None:
            return {"allowed": True, "reason": ""}
        decision = {"allowed": False, "reason": reason}
        self.refused.append({"call": dict(call), "reason": reason})
        return decision

    def record(self, session, call, *, outcome="ok"):
        if outcome != "ok":
            return {"recorded": False,
                    "reason": f"outcome {outcome!r} changed nothing"}
        entry = {"tool": _name(call), "quantity": impact(call)}
        self.window.append(entry)
        if isinstance(session, dict):
            session.setdefault("steps", []).append(
                {"call": dict(call), "quantity": entry["quantity"]})
        self.generation += 1
        # every approval describes the state before this write
        self.stale.extend(a for a in self.approvals if a["generation"] < self.generation)
        self.approvals = [a for a in self.approvals if a["generation"] == self.generation]
        return {"recorded": True, "window": len(self.window)}

    def approve(self, session, call, *, token):
        approval = {"token": token, "call": dict(call),
                    "generation": self.generation,
                    "identity": session.get("identity") if isinstance(session, dict) else None}
        self.approvals.append(approval)
        self.window = []            # a person has now seen the batch, once
        return approval

    def accept(self, call, *, token):
        for approval in self.approvals:
            if approval["token"] != token:
                continue
            if _same_call(approval["call"], call):
                return {"accepted": True, "reason": ""}
            return {"accepted": False,
                    "reason": "that approval was issued for a different change"}
        if any(a["token"] == token for a in self.stale):
            return {"accepted": False,
                    "reason": "that approval is stale: a change was made after it was "
                              "issued, so it describes a state that no longer exists"}
        return {"accepted": False, "reason": "no approval carries that token"}


class Audit:
    def __init__(self, sink=None):
        self.sink = sink
        self.lines = []
        self.text = []

    def record(self, message, response, *, session, mutations=0):
        message = message if isinstance(message, dict) else {}
        method = message.get("method")
        id = message.get("id")
        if isinstance(id, bool) or not isinstance(id, (str, int)):
            id = None
        error = response.get("error") if isinstance(response, dict) else None
        line = {
            "method": method if isinstance(method, str) else None,
            "id": id,
            # a notification has no answer and did not fail, so ok stays true
            "ok": not isinstance(error, dict) or "code" not in error,
            "code": error.get("code") if isinstance(error, dict) else None,
            "identity": (session or {}).get("identity") if isinstance(session, dict) else None,
            "mutations": mutations,
        }
        text = json.dumps(line, sort_keys=True, separators=(",", ":"))
        self.lines.append(line)
        self.text.append(text)
        if self.sink is not None:
            self.sink(text)
        return line


def announce_tools_changed(server):
    return server.notify("notifications/tools/list_changed")


def _write_call(server, message):
    if not isinstance(message, dict) or message.get("method") != "tools/call":
        return None
    params = message.get("params")
    if not isinstance(params, dict):
        return None
    name = params.get("name")
    definition = server.tools.get(name) if isinstance(name, str) else None
    if definition is None or not definition.get("mutates"):
        return None
    arguments = params.get("arguments")
    return {"tool": name, "mutates": True,
            "arguments": arguments if isinstance(arguments, dict) else {}}


def guard(server, policy, audit):
    inner = server.dispatch

    def dispatch(message):
        session = server.session
        call = _write_call(server, message)
        blocked = None
        if call is not None:
            decision = policy.decide(session, call)
            if not decision["allowed"]:
                blocked = decision
        if blocked is None:
            response = inner(message)
        else:
            response = result(message.get("id"), {
                "content": [{"type": "text", "text": blocked["reason"]}],
                "isError": True})
        if (call is not None and blocked is None and isinstance(response, dict)
                and isinstance(response.get("result"), dict)
                and not response["result"].get("isError")):
            policy.record(session, call, outcome="ok")
        audit.record(message, response, session=session,
                     mutations=len(policy.window))
        return response

    return dispatch
