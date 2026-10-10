"""Agents From Scratch — stage 8: the gate, and the content that is not a command

SOLUTION. A crude phrase scan for the trace, a structural check on the roles,
and a policy gate that turns a refusal into an observation. The messy part is
the precedence, which is the point: deny, then the mode, then approvals.
"""

import fnmatch

PHRASES = (
    "ignore previous",
    "ignore all previous",
    "disregard your instructions",
    "now you are",
    "system:",
    "as the system administrator",
    "delete the tests",
    "copy the token",
    "| sh",
)


def scan_injection(text):
    if not text:
        return []
    lowered = text.lower()
    found = []
    for phrase in PHRASES:
        if phrase in lowered and phrase not in found:
            found.append(phrase)
    return found


def scan_transcript(messages):
    flagged = []
    system_messages = 0
    for index, message in enumerate(messages):
        role = message.get("role")
        if role == "system":
            system_messages += 1
            continue
        if role not in ("tool", "user"):
            continue
        for phrase in scan_injection(message.get("content", "")):
            flagged.append({"index": index, "role": role, "phrase": phrase})
    return {"system_messages": system_messages, "flagged": flagged}


class Gate:
    def __init__(self, *, mode="read_only", allow=(), deny=(), approve=None):
        if mode not in ("read_only", "workspace"):
            raise ValueError(f"unknown mode {mode!r}")
        self.mode = mode
        # Not `self.allow`: that name belongs to the method that decides, and an
        # attribute shadowing it turns every gate into a TypeError.
        self.allow_patterns = list(allow)
        self.deny_patterns = list(deny)
        self.approve = approve
        self.refusals = []

    def _deny_reason(self, tool):
        for pattern in self.deny_patterns:
            if fnmatch.fnmatch(tool, pattern):
                return (f"the tool {tool!r} matches the deny pattern {pattern!r}: "
                        f"an approval cannot authorise what the policy forbids")
        return None

    def allow(self, tool, args, *, side_effect=False):
        denied = self._deny_reason(tool)
        if denied:
            return self._refuse(tool, args, denied)
        if side_effect and self.mode == "read_only":
            return self._refuse(
                tool, args, f"{tool!r} has side effects and this gate is "
                            f"read-only: change the mode deliberately, not as a "
                            f"side effect of an agent's suggestion")
        if side_effect and self.approve is not None:
            if not self.approve({"tool": tool, "args": args}):
                return self._refuse(tool, args,
                                    f"the approval hook declined {tool!r}")
        if self.allow_patterns:
            for pattern in self.allow_patterns:
                if fnmatch.fnmatch(tool, pattern):
                    break
            else:
                return self._refuse(tool, args,
                                    f"{tool!r} is not in the allow list "
                                    f"{self.allow_patterns}")
        return {"allowed": True, "reason": "policy allows this call"}

    def _refuse(self, tool, args, reason):
        self.refusals.append({"tool": tool, "args": args, "reason": reason})
        return {"allowed": False, "reason": reason}


class Gated:
    def __init__(self, toolbox, gate):
        self.toolbox = toolbox
        self.gate = gate
        self.names = list(toolbox.names)

    def call(self, name, args):
        definition = self.toolbox.registry.get(name) if hasattr(
            self.toolbox, "registry") else None
        if definition is None:
            raise ValueError(
                f"Gated needs the tool definitions to know which tools have side "
                f"effects, and {name!r} is not in the registry")
        verdict = self.gate.allow(name, args,
                                  side_effect=bool(definition.get("side_effect")))
        if not verdict["allowed"]:
            return {"ok": False, "denied": True, "tool": name,
                    "content": f"denied by policy: {verdict['reason']}"}
        return self.toolbox.call(name, args)
