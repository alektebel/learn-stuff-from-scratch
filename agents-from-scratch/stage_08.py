"""Agents From Scratch — stage 8: the gate, and the content that is not a
command

DESIGN DECISION — tool output is data, and the only thing that stops it from
being an instruction is where it sits.
    Every text an agent reads is a candidate instruction: a file, a web page, a
    ticket, a test failure message. What keeps a well-built agent boringly safe
    is not a smarter filter, it is that tool output goes into the transcript
    with role "tool" and the system prompt is written once at the start. An
    agent that concatenates tool output into its system prompt has promoted
    whatever it read to operator level, and no amount of scanning undoes that:
    the scan is a detector, the role is the defence.

DESIGN DECISION — the policy decides, and the model is told.
    A refusal is not an exception: it is an observation the model reads
    (`ok=False`, "denied by policy: read-only mode"). The agent then does what
    an agent should — stops trying, or asks. A gate that raises teaches the
    model nothing and turns a policy decision into a crash; a gate that
    silently skips the call teaches the model that the call worked.

DESIGN DECISION — deny outranks approve.
    An approval hook is a person saying yes to one specific action, and a
    denylist is the thing the person is not allowed to say yes to. Checking
    approvals first is how a "temporary" yes ships a permanent capability.

TODO: implement

    PHRASES = (...)   # the documented, deliberately crude list of instruction
                      # shapers: "ignore previous", "ignore all previous",
                      # "disregard your instructions", "now you are",
                      # "system:", "as the system administrator",
                      # "delete the tests", "copy the token", "to the file",
                      # "| sh"

    scan_injection(text) -> list[str]
        Every phrase from PHRASES that occurs in `text`, case-insensitively, in
        the order they appear and each one reported once. Crude on purpose: it
        is a detector that raises a flag for a human reading the trace, not a
        classifier, and it is expected to miss paraphrases and to flag honest
        text that says "ignore previous" for other reasons.

    scan_transcript(messages) -> dict
        {"system_messages": int, "flagged": [{"index", "role", "phrase"}, ...]}
        Flags matching content in "tool" and "user" messages only: the system
        message is the trusted prompt and flagging it would be noise. The
        `system_messages` count is the structural half of the audit — more than
        one means something was promoted into the prompt.

    class Gate:
        __init__(self, *, mode="read_only", allow=(), deny=(), approve=None)
            mode: "read_only" refuses every tool whose definition says
            side_effect=True. "workspace" allows side effects but still applies
            `deny` and `approve`.
            allow/deny: name patterns matched with fnmatch ("delete_*"),
            checked against the tool name. deny is checked FIRST and an
            approval cannot override it.
            approve: a callable taking {"tool", "args"} and returning bool.
            None means "no approval hook": in "workspace" mode the call is
            allowed without one.
        .refusals -> list[dict]      # {"tool", "args", "reason"} in order
        allow(tool, args, *, side_effect=False) -> {"allowed": bool, "reason": str}
            The decision, with a reason a person can read. A denial is recorded
            in .refusals.

    class Gated:
        A toolbox wrapper (see stage 1's protocol): .names passes through and
        .call applies the gate first.
        __init__(self, toolbox, gate)
        .call(name, args) -> the toolbox's result unchanged when allowed,
        otherwise {"ok": False, "denied": True, "tool": name,
                   "content": "denied by policy: <reason>"} — never a raise,
        so the loop and the model both survive.
        It reads `side_effect` from toolbox.registry[name]; a toolbox that does
        not expose a registry is a programming error and may raise.
"""


def scan_injection(text):
    raise NotImplementedError("stage 8: implement scan_injection()")


def scan_transcript(messages):
    raise NotImplementedError("stage 8: implement scan_transcript()")


class Gate:
    def __init__(self, *, mode="read_only", allow=(), deny=(), approve=None):
        raise NotImplementedError("stage 8: implement Gate")

    def allow(self, tool, args, *, side_effect=False):
        raise NotImplementedError("stage 8: implement Gate.allow()")


class Gated:
    def __init__(self, toolbox, gate):
        raise NotImplementedError("stage 8: implement Gated")

    def call(self, name, args):
        raise NotImplementedError("stage 8: implement Gated.call()")
