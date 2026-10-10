"""Agents From Scratch — stage 3: the toolbox, where a failed tool is an observation

SOLUTION. ToolBox validates a call before running anything, renders the result
deterministically, and turns every failure the agent can act on into an
ok=False row the model reads instead of an exception the loop cannot survive.
"""

import json

from stage_02 import validate


def describe_error(exc):
    """A tool's failure as the model must see it: the type and its message.

    str(exc) is the tool author's own words. A traceback would leak paths and
    line numbers that change between runs and that the model cannot act on.
    """
    return f"{type(exc).__name__}: {exc}"


def _observation(name, args, ok, content, error, truncated):
    """One result shape for every outcome: the loop reads ok/content and never
    has to guess which keys exist."""
    return {
        "tool": name,
        "ok": ok,
        "content": content,
        "truncated": truncated,
        "error": error,
        # echo the arguments the call was made with, and only when there were
        # arguments to echo
        "args": dict(args) if isinstance(args, dict) else None,
    }


class ToolBox:
    """A registry of tools that turns a bad call into a message, not a crash."""

    def __init__(self, tools=(), *, limit=None):
        # Insertion order IS the registry order: the model is shown the tools
        # in the order the author declared them, deterministically, and a
        # repeated name keeps its first position with the last definition.
        self.registry = {definition["name"]: definition for definition in tools}
        # A negative limit would slice the TAIL off, which is the mistake this
        # class exists to avoid, so it is clamped to zero.
        self.limit = None if limit is None else max(int(limit), 0)
        self.executed = []

    @property
    def names(self):
        # Derived, never duplicated: a second list would eventually disagree
        # with the registry it is supposed to describe.
        return list(self.registry)

    def call(self, name, args=None):
        definition = self.registry.get(name)
        if definition is None:
            available = ", ".join(self.names) or "(none)"
            return _observation(
                name, args, False,
                f"unknown tool {name!r}; available: {available}",
                f"unknown tool: {name}", False)

        if not isinstance(args, dict):
            return _observation(
                name, args, False,
                f"tool {name!r} was called with {type(args).__name__} instead of "
                f"a dict of arguments; it was not run",
                "bad args: not a dict", False)

        checked = validate(definition.get("parameters") or {}, args)
        if not checked["ok"]:
            problem = "; ".join(checked["errors"])
            return _observation(name, args, False, problem, problem, False)
        args = checked["args"]           # coerced, defaults applied

        # Past this point the function is invoked, so the call is recorded as
        # executed even when the function itself raises: .executed is the trace
        # of what touched the world.
        self.executed.append(name)
        try:
            value = definition["fn"](**args)
        except Exception as exc:                 # noqa: BLE001 - the whole point
            failure = describe_error(exc)
            return _observation(name, args, False, failure, failure, False)

        if isinstance(value, str):
            rendered = value
        else:
            try:
                rendered = json.dumps(value, sort_keys=True)
            except (TypeError, ValueError) as exc:
                # str(value) is deliberately not used: for many objects it
                # embeds an address, which would make the transcript differ
                # from one run to the next.
                return _observation(
                    name, args, False,
                    f"tool {name!r} returned a {type(value).__name__}, which "
                    f"cannot be rendered as JSON ({exc})",
                    f"result is not JSON-serialisable: {type(value).__name__}",
                    False)

        truncated = False
        if self.limit is not None and len(rendered) > self.limit:
            dropped = len(rendered) - self.limit
            # Keep the HEAD. A tool reports its payload first and its bad news
            # last ("0 matches in 4,120 characters"), so a tail cut would drop
            # exactly the part the model has to read.
            rendered = (rendered[:self.limit]
                        + f"\n[... {dropped} characters dropped]")
            truncated = True

        return _observation(name, args, True, rendered, None, truncated)
