"""MCP From Scratch — stage 4: tools, and the line between a bad request and a failed tool

SOLUTION. One registry over a live tool table, one skeleton schema check, and
then the split the stage exists for: `call_tool` raises `ProtocolError` for a
request it cannot act on, and returns an ordinary result — with an explicit
`isError` — for anything the tool did. A tool's function is called as
`fn(arguments, session)`, the same shape every handler in this course has, so a
tool can see who is asking, and it may return either a plain value (stage 4
renders it) or a complete result (handed back unchanged). Deterministic: no
clock, no prints, sorted JSON everywhere.
"""

import json

from stage_01 import ERRORS, ProtocolError

PAGE = 2

# The JSON types a schema may declare. `integer`, `number` and `boolean` are
# special-cased in _type_ok(): isinstance(True, int) is True, and JSON `true`
# is not the integer 1.
_JSON_TYPES = {
    "string": str,
    "array": list,
    "object": dict,
    "null": type(None),
}


class ToolError(Exception):
    """A tool's own failure: reported INSIDE the result, never as a protocol error."""


class Tool:
    """One tool: what the model is shown, and the function that does the work.
    `fn(arguments, session)` — the same shape every handler in this course has."""

    def __init__(self, name, description, input_schema, fn, *, side_effect=False,
                 enabled=True, reason=None):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.fn = fn
        self.side_effect = side_effect
        self.enabled = bool(enabled)
        self.reason = reason

    def definition(self):
        # The spec's Tool shape and nothing else: everything in here is shown to
        # the model, so `fn`, `enabled` and `reason` stay out of it.
        return {"name": self.name, "description": self.description,
                "inputSchema": self.input_schema}


def _as_tool(candidate):
    """One Tool, whichever shape a caller hands us: a Tool, or a definition dict
    from the server's table (where the world-changing flag is spelled
    `mutates`)."""
    if isinstance(candidate, Tool):
        return candidate
    tool = Tool(candidate.get("name"), candidate.get("description", ""),
                candidate.get("inputSchema") or {}, candidate.get("fn"),
                side_effect=bool(candidate.get("mutates")))
    tool.enabled = bool(candidate.get("enabled", True))
    tool.reason = candidate.get("reason")
    return tool


def _type_ok(value, declared):
    if declared == "boolean":
        return isinstance(value, bool)
    if declared == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    kind = _JSON_TYPES.get(declared)
    if kind is None:
        # A type name we do not know is the tool author's business, not ours.
        return True
    return isinstance(value, kind)


def _check_arguments(schema, arguments):
    """The skeleton: required present, declared types match, enum membership, extra
    keys rejected. No $ref, no nested objects beyond one level, no coercion, no
    defaults — stage 2 of agents-from-scratch owns that job, and a second
    validator that grows here would drift from it within a week. Returns the
    problems as a list of sentences, in the order the arguments came in."""
    properties = schema.get("properties") or {}
    problems = []
    for key in schema.get("required") or []:
        if key not in arguments:
            problems.append(f"missing required argument {key!r}")
    for key, value in arguments.items():
        if key not in properties:
            problems.append(f"unknown argument {key!r}")
            continue
        rule = properties[key] or {}
        declared = rule.get("type")
        if declared is not None and not _type_ok(value, declared):
            problems.append(f"argument {key!r} must be {declared}, got "
                            f"{type(value).__name__}")
        if "enum" in rule and value not in rule["enum"]:
            problems.append(f"argument {key!r} must be one of {rule['enum']!r}, "
                            f"got {value!r}")
    return problems


def _cursor_offset(params, count):
    """The offset a `cursor` asks for: an opaque string this server handed out
    (`str(offset)`), or an integer, and `None` for "no cursor". Anything that is
    not a position in the CURRENT list is refused: a cursor from a page that has
    since changed would otherwise skip results silently."""
    cursor = params.get("cursor")
    if cursor is None:
        return 0
    offset = None
    if isinstance(cursor, bool):
        offset = None
    elif isinstance(cursor, int):
        offset = cursor
    elif isinstance(cursor, str):
        # '.isdigit()' alone is not enough: '²'.isdigit() is True and int('²')
        # raises, while a cursor we emitted never leaves the ASCII digits.
        offset = int(cursor) if cursor.isascii() and cursor.isdigit() else None
    if offset is None or not 0 <= offset < count:
        raise ProtocolError(ERRORS["invalid_params"],
                            f"cursor {cursor!r} is not a position in this list "
                            f"of {count} tools",
                            data={"cursor": cursor})
    return offset


def _looks_like_result(value):
    """A COMPLETE tools/call result: a `content` list AND a bool `isError`. Both
    halves are required — a dict that merely HAS a `content` key (a row with a
    "content" column, say) is an ordinary value and gets rendered as JSON, and
    an `isError` that is not a bool is not the field this protocol defines."""
    return (isinstance(value, dict) and isinstance(value.get("content"), list)
            and isinstance(value.get("isError"), bool))


def _render(tool, value):
    """The tools/call result the model reads.

    A tool may return a plain value — a `str` passes through untouched, anything
    else is `json.dumps(value, sort_keys=True)` — or a COMPLETE result, which is
    handed back unchanged: a later stage builds the text the model must read
    itself, and encoding a result into a result would show it a JSON dump of an
    envelope instead of a table."""
    if _looks_like_result(value):
        return value
    if isinstance(value, str):
        return text_result(value)
    try:
        text = json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        # str(value) is deliberately not used: for many objects it embeds an
        # address, and the same call would then render differently every run.
        return text_result(f"tool {tool.name!r} returned a value that cannot be "
                           f"rendered as JSON (type {type(value).__name__})",
                           is_error=True)
    return text_result(text)


class ToolRegistry:
    """Lists and calls tools: the schema skeleton, then the split."""

    def __init__(self, *, page=PAGE, table=None):
        self.page = page
        self.table = table
        self._tools = {}

    def add(self, tool):
        added = _as_tool(tool)
        self._tools[added.name] = added
        return added

    @property
    def tools(self):
        # A fresh mapping on every access, so the server's table is read LIVE:
        # a tool registered after install() is listed by the same registry, and
        # the `enabled` flag a read-only mode flips is honoured on the next
        # request instead of at install time.
        found = dict(self._tools)
        if self.table is not None:
            for name, definition in self.table.items():
                found[name] = _as_tool(definition)
        return found

    @property
    def names(self):
        # Derived, never duplicated: a second list would eventually disagree
        # with the table it is supposed to describe.
        return list(self.tools)

    def list_tools(self, params):
        found = self.tools
        enabled = [name for name, tool in found.items() if tool.enabled]
        offset = _cursor_offset(params, len(enabled))
        window = enabled[offset:offset + self.page]
        page = {"tools": [found[name].definition() for name in window]}
        following = offset + self.page
        if following < len(enabled):
            page["nextCursor"] = str(following)
        return page

    def call_tool(self, params, session):
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise ProtocolError(ERRORS["invalid_params"],
                                "tools/call needs the tool's name as a string",
                                data={"tool": name})
        found = self.tools
        tool = found.get(name)
        if tool is None:
            available = ", ".join(n for n, t in found.items() if t.enabled)
            raise ProtocolError(ERRORS["invalid_params"],
                                f"unknown tool {name!r}; available: "
                                f"{available or '(none)'}",
                                data={"tool": name})
        if not tool.enabled:
            because = f" ({tool.reason})" if tool.reason else ""
            raise ProtocolError(ERRORS["invalid_params"],
                                f"tool {name!r} is disabled{because}: it was "
                                f"not run",
                                data={"tool": name})

        arguments = params.get("arguments")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise ProtocolError(ERRORS["invalid_params"],
                                f"arguments must be an object, got "
                                f"{type(arguments).__name__}",
                                data={"tool": name})
        problems = _check_arguments(tool.input_schema, arguments)
        if problems:
            raise ProtocolError(ERRORS["invalid_params"],
                                f"invalid arguments for {name!r}: "
                                + "; ".join(problems),
                                data={"tool": name})

        # Past this point the request is well-formed, so the call reached the
        # tool: that is what `steps` records, and it is recorded before fn runs
        # so a tool that raises is still a call that happened.
        session["steps"].append(f"tools/call:{name}")
        try:
            returned = tool.fn(arguments, session)
        except ToolError as exc:
            # The tool's own failure: the request was fine, the work failed.
            return text_result(str(exc), is_error=True)
        except Exception as exc:            # noqa: BLE001 - the point of the stage
            # A bug in the tool is still a tool execution error: the client's
            # request was valid, and only the model can do anything about it.
            return text_result(f"{type(exc).__name__}: {exc}", is_error=True)
        return _render(tool, returned)


def text_result(text, *, is_error=False):
    """The one result shape: text blocks and a real bool. `isError` is never
    missing — the spec assumes a missing one is false, and a client that has to
    assume is a client that guesses."""
    return {"content": [{"type": "text", "text": text}], "isError": bool(is_error)}


def install(server, registry=None):
    """Register `tools/list` and `tools/call` on `server`, each handler being
    `handler(params, session)`. Without a registry, the server's own tool table
    IS the registry's source, read live."""
    if registry is None:
        registry = ToolRegistry(table=getattr(server, "tools", None))

    def list_tools(params, session):
        return registry.list_tools(params)

    def call_tool(params, session):
        return registry.call_tool(params, session)

    server.add("tools/list", list_tools)
    server.add("tools/call", call_tool)
