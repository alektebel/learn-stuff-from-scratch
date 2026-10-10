"""MCP From Scratch — stage 10: the trajectory, and the audit line

Every call in stage 9 was approved. The session was still unsafe. That is the
lesson of this stage: safety is a property of a SEQUENCE, and no per-call check
can see a sequence.

DESIGN DECISION — the budget is per window, and a window is "since a person
    last saw the batch".
    A session may make up to `max_mutations` writes totalling at most
    `max_total_quantity` before a human has to look at the whole thing. Three
    calls that move 40 units each are each harmless; the third makes 120. The
    cap and the total are the same mechanism (one window, two limits), and the
    refusal names the aggregate — "this needs one approval that shows all three
    changes", never "call 3 is too big".

DESIGN DECISION — a refusal is an execution outcome, not a protocol error.
    "You may not do that" is something the MODEL has to act on: it must change
    its plan. It reads results, not error codes, and a client that receives
    -32602 learns only that its server is broken. So a refused call answers an
    ordinary result with `isError: true` whose text says why and what would make
    it possible. The one thing that must be true: the tool's fn did NOT run.

DESIGN DECISION — reads are never refused.
    A session that cannot read cannot explain itself, and refusing reads is how a
    budget stops the agent from telling a person what it already did. Whatever a
    window has spent, `resources/read`, `tools/list` and a read-only report still
    work.

DESIGN DECISION — an approval is bound to a state, so a write makes it stale.
    An approval says "this state, this change, yes". After any write, that
    sentence is about a state that no longer exists: every earlier approval is
    stale, and a replayed token is refused with the reason naming the write that
    invalidated it. This is the difference between a signature and a password.

DESIGN DECISION — the audit line has no clock and no payload.
    One deterministic line per message: method, id, ok, error code, identity,
    how many mutations that session has made. No timestamp (a wall clock in a
    line makes the line untestable and the log unmergeable), and never the
    params — an audit that copies payloads is a second copy of the customer's
    data, in the one place nobody guards. `Audit.record` writes exactly these six
    keys and nothing else.

TODO: implement

    LIMITS = {"max_mutations": 3, "max_total_quantity": 100}

    def impact(call) -> int
        The quantity a write moves, from whichever shape the call uses: an
        `arguments["quantity"]`, the `quantity` inside an `arguments["change"]`
        (stage 9's tool hands over a change, not arguments), or a bare
        `call["change"]`. An int, never a bool (`isinstance(True, int)` is True in
        Python), and the absolute value — a write is judged by how far it moves,
        not by which way. Approving an order moves nothing by itself.

    class SessionPolicy
        __init__(self, *, max_mutations=3, max_total_quantity=100)
            .max_mutations .max_total_quantity .generation
            .window -> list[dict]        # writes since the last approval:
                                         # [{"tool", "quantity"}]
            .refused -> list[dict]       # [{"call", "reason"}]
            .approvals -> list[dict]     # [{"token", "call", "generation"}]
            .stale -> list[dict]         # approvals a later write invalidated
        classify(call) -> str
            "read" when the call is not a write, "write" otherwise. A call is a
            write when `call["mutates"]` is true or it carries a `"change"` key.
        decide(session, call) -> {"allowed": bool, "reason": str}
            reads: always allowed. writes: refused when the session has no
            non-empty `session["identity"]`, when the window already holds
            `max_mutations` writes, or when this call's impact would push the
            window's total over `max_total_quantity` — the reason names the
            aggregate and the ceiling, and says the aggregate needs one approval
            that shows the whole diff. Every refusal is appended to `.refused`.
        record(session, call, *, outcome="ok") -> dict
            A write that HAPPENED: appends {"tool", "quantity"} to `.window` and
            the call to `session["steps"]`, bumps `.generation`, and moves every
            approval of an older generation into `.stale`. An outcome other than
            "ok" (a business failure, a refusal) changed nothing and must not
            spend the window.
        approve(session, call, *, token) -> dict
            A person approved the window: records the approval at the current
            generation and RESETS `.window` (the batch has been seen, once).
        accept(call, *, token) -> {"accepted": bool, "reason": str}
            Replays a token: accepted only when a live (non-stale) approval has
            that token AND its call matches this one; otherwise refused with the
            reason saying which of the two failed.

    class Audit
        __init__(self, sink=None)        # sink(line_text) -> None
            .lines -> list[dict] .text -> list[str] .sink
        record(self, message, response, *, session, mutations=0) -> dict
            Builds {"code", "id", "identity", "method", "mutations", "ok"}:
            the method and id from the message (None when it has none), the error
            code from the response's error or None, `ok` true only when a
            response came back without an error, the identity from the session,
            and the mutation count the caller passed. Serializes with sorted
            keys, appends the text to `.text` and the dict to `.lines`, calls the
            sink, and returns the line. Never the params, never a clock.

    def announce_tools_changed(server) -> dict
        Sends notifications/tools/list_changed. Stage 7 flips the switch and
        returns how many tools appeared; a client that cached tools/list keeps
        offering the old set until somebody tells it, so the flip and this
        notification are one operation.

    def guard(server, policy, audit) -> callable
        Wraps `server.dispatch`. Returns a dispatch-shaped function that
          - recognizes a `tools/call` whose tool is a write (via `server.tools`)
            and, when the policy refuses it, answers an ordinary result with
            `isError: true` and the refusal as its text WITHOUT calling the
            server (the tool's fn must not run);
          - for a write that went through and changed something (a result that is
            not an error and not `isError`), calls `policy.record(...)`;
          - audits every message, requests and notifications alike;
          - and is otherwise exactly the server it wrapped.
"""

LIMITS = {"max_mutations": 3, "max_total_quantity": 100}


def impact(call):
    raise NotImplementedError("stage 10: implement impact")


class SessionPolicy:
    def __init__(self, *, max_mutations=3, max_total_quantity=100):
        raise NotImplementedError("stage 10: implement SessionPolicy.__init__")

    def classify(self, call):
        raise NotImplementedError("stage 10: implement SessionPolicy.classify")

    def decide(self, session, call):
        raise NotImplementedError("stage 10: implement SessionPolicy.decide")

    def record(self, session, call, *, outcome="ok"):
        raise NotImplementedError("stage 10: implement SessionPolicy.record")

    def approve(self, session, call, *, token):
        raise NotImplementedError("stage 10: implement SessionPolicy.approve")

    def accept(self, call, *, token):
        raise NotImplementedError("stage 10: implement SessionPolicy.accept")


class Audit:
    def __init__(self, sink=None):
        raise NotImplementedError("stage 10: implement Audit.__init__")

    def record(self, message, response, *, session, mutations=0):
        raise NotImplementedError("stage 10: implement Audit.record")


def announce_tools_changed(server):
    raise NotImplementedError("stage 10: implement announce_tools_changed")


def guard(server, policy, audit):
    raise NotImplementedError("stage 10: implement guard")
