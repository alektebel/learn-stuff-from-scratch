"""Agent Harness From Scratch — stage 4: dispatch: an unknown tool is a message,
a failing tool is an observation

The reasoning lives in `stage_04.py`'s docstring (the design decisions are the
lesson); this file is the implementation. One sentence each:

    * a bad call is an observation the model can read and repair, never an
      exception that ends the turn;
    * `EnvError` is an outcome and is caught; every other exception is a bug in
      our program and propagates;
    * arguments are validated against `input_schema` BEFORE the fn runs;
    * `render_result` is a bounded, deterministic text table with a row count,
      not `str(env_result)` and not JSON.
"""

import copy

from tiny_env import EnvError, HarnessError

# The JSON types a declared property can name, mapped to the Python that
# satisfies each one. `boolean` is checked before `integer`/`number` because
# `True` IS an `int` in Python: a property declared `integer` that accepted
# `True` would hand a flag to a body that expects a count, and the body would
# compare `1` to a value the model never meant to send. The same reason stage 7
# spells it out for filter types.
_JSON_TYPES = {
    "string": lambda value: isinstance(value, str),
    "boolean": lambda value: isinstance(value, bool),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
    "array": lambda value: isinstance(value, list),
    "object": lambda value: isinstance(value, dict),
    "null": lambda value: value is None,
}


def _name_text(name):
    """A tool name as a message should read it. `%r` for a string (so whitespace
    and an empty name are visible), and the TYPE for anything else — `repr` of an
    arbitrary object carries an address, and rendered text must be the same bytes
    on every run."""
    if isinstance(name, str):
        return repr(name)
    return "<%s>" % type(name).__name__


def _json_type_name(value):
    """The JSON type of a Python value, for the message that says what arrived."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return type(value).__name__


def _argument_error(name, schema, arguments):
    """The message for the first thing wrong with `arguments`, or None.

    Never raises for the model's arguments — every one of these is a sentence the
    model reads. It DOES raise `HarnessError` for a schema that declares a JSON
    type nobody knows: that is a bug in the tool table (ours), not in the call,
    and a message the model cannot act on is worse than a stop.

    The order is the one the stage documents: what is required, then the declared
    type of what arrived, then keys nothing declared. Iteration follows the SCHEMA
    where the schema has an order (required, properties) and sorts the caller's
    keys otherwise, so the message never depends on the model's key order.
    """
    if not isinstance(arguments, dict):
        return ("the arguments of tool %s must be an object, got %s"
                % (_name_text(name), type(arguments).__name__))
    schema = schema if isinstance(schema, dict) else {}
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        properties = {}
    required = schema.get("required")
    if not isinstance(required, list):
        required = []

    for key in required:
        if key not in arguments:
            return ("tool %s needs the required argument %r" % (_name_text(name), key))

    for key, declared in properties.items():
        if key not in arguments:
            continue
        declared_type = declared.get("type") if isinstance(declared, dict) else None
        if declared_type is None:
            # A property with no declared type accepts anything: only the key was
            # the boundary, and the boundary has been crossed correctly.
            continue
        names = declared_type if isinstance(declared_type, list) else [declared_type]
        checkers = []
        for type_name in names:
            checker = _JSON_TYPES.get(type_name)
            if checker is None:
                raise HarnessError(
                    "the schema of tool %r declares argument %r as the unknown "
                    "JSON type %r" % (name, key, type_name))
            checkers.append(checker)
        if not any(checker(arguments[key]) for checker in checkers):
            return ("argument %r of tool %s must be %s, got %s"
                    % (key, _name_text(name), "/".join(names),
                       _json_type_name(arguments[key])))

    for key in sorted(arguments):
        if key not in properties:
            declared = ", ".join(properties) or "(none)"
            return ("tool %s has no argument %r; it declares: %s"
                    % (_name_text(name), key, declared))
    return None


def _observation(tool_call, content, is_error):
    """One `tool` message. `content` is what the model reads, so it is a string
    here and nowhere else does it become one."""
    return {"role": "tool", "tool_call_id": tool_call.get("id"),
            "content": content, "is_error": bool(is_error)}


class Dispatcher:
    def __init__(self, tools):
        if not isinstance(tools, dict):
            raise ValueError("tools must be a {name: definition} dict, got %s"
                             % type(tools).__name__)
        self._tools = {}
        for name, definition in tools.items():
            if not isinstance(name, str) or not name:
                raise ValueError("a tool needs a non-empty string name, got %r"
                                 % (name,))
            if not isinstance(definition, dict) or not callable(definition.get("fn")):
                raise ValueError("tool %r has no fn to call" % name)
            self._tools[name] = {
                "name": name,
                "description": definition.get("description", ""),
                "input_schema": definition.get("input_schema") or {},
                "fn": definition["fn"],
            }
        self._called = []
        self._unknown = []

    def definitions(self):
        # Copies, deep ones for the schema: a caller (or anything that serialises
        # what it was handed) must not be able to rewrite the registry — or the
        # schema the next call is validated against — by keeping the definitions.
        return [{"name": tool["name"], "description": tool["description"],
                 "inputSchema": copy.deepcopy(tool["input_schema"])}
                for tool in self._tools.values()]

    @property
    def called(self):
        return list(self._called)

    @property
    def unknown(self):
        return list(self._unknown)

    def observe(self, tool_call):
        name = tool_call.get("name")
        # isinstance first: `.get` on an unhashable name raises TypeError, and
        # that would be the harness blaming the model for a bug in our lookup.
        tool = self._tools.get(name) if isinstance(name, str) else None
        if tool is None:
            self._unknown.append(name)
            available = ", ".join(self._tools) or "(none)"
            return _observation(
                tool_call,
                "unknown tool %s; available tools: %s"
                % (_name_text(name), available), True)

        arguments = tool_call.get("arguments")
        if arguments is None:
            arguments = {}
        problem = _argument_error(name, tool["input_schema"], arguments)
        if problem is not None:
            # The fn is NOT entered: a refused call has no side effect, and an
            # invalid `limit` never reaches the database.
            return _observation(tool_call, problem, True)

        self._called.append(name)
        try:
            result = tool["fn"](arguments)
        except EnvError as exc:
            # The world said no. The driver's own words are the observation —
            # prefixing them with harness noise only makes them harder to read.
            return _observation(tool_call, str(exc), True)
        # Anything else is a bug in the tool's body: it propagates, because a
        # bug turned into a message is a bug the model reads forever.
        return _observation(tool_call, render_result(result), False)


def _cell(value):
    """One printed cell: exactly what SQL handed back. A number keeps its spelling
    (`360.0` is not `360`), and a NULL arrives as `None` and prints as `None` —
    one rule for every cell rather than a sentinel this stage invents."""
    return str(value)


def render_result(env_result):
    if not isinstance(env_result, dict):
        raise HarnessError("a tool must return an env result dict, got %s"
                           % type(env_result).__name__)
    columns = env_result.get("columns")
    rows = env_result.get("rows")
    if not isinstance(columns, (list, tuple)) or not isinstance(rows, (list, tuple)):
        raise HarnessError("an env result is {'columns': [...], 'rows': [[...]]}, got %r"
                           % (sorted(env_result) if isinstance(env_result, dict) else env_result,))
    lines = [" | ".join(_cell(column) for column in columns)]
    for row in rows:
        if not isinstance(row, (list, tuple)):
            raise HarnessError("every row of an env result must be a list of cells, got %s"
                               % type(row).__name__)
        lines.append(" | ".join(_cell(cell) for cell in row))
    # The row count is not decoration: it is how the model knows whether it is
    # reading the whole answer, and it is the line a "just print the rows" render
    # drops first.
    lines.append("(%d rows)" % len(rows))
    return "\n".join(lines)
