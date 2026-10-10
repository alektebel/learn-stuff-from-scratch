"""Agents From Scratch — stage 2: tool schemas and the arguments you accept

SOLUTION. `tool()` validates and stores a definition, `describe()` renders the
schema a prompt shows the model, and `validate()` is the gate between the
model's arguments and the tool's `fn`. `validate()` never raises for bad
arguments: it returns the cleaned subset it could build plus named errors. The
one thing it must get right is that a boolean is not an integer, which
`isinstance(True, int)` quietly disagrees with.
"""

import copy
import difflib
import re

_NAME = re.compile(r"[a-z][a-z0-9_]*\Z")


def tool(name, description, parameters, fn, *, side_effect=False):
    if not isinstance(name, str) or not _NAME.match(name):
        raise ValueError(
            f"tool name {name!r} must match [a-z][a-z0-9_]*: the model reads "
            f"the name in the prompt and calls it back verbatim, so it has to "
            f"be a stable identifier")
    if not callable(fn):
        raise ValueError(
            f"tool {name!r} has no callable fn={fn!r}: a definition without a "
            f"function describes a tool the loop cannot run")
    if not _object_schema(parameters):
        raise ValueError(
            f"tool {name!r} parameters are not an object schema: {parameters!r}. "
            f"A tool takes named arguments, so the schema root is an object "
            f"with a 'properties' mapping")
    return {"name": name, "description": description, "parameters": parameters,
            "fn": fn, "side_effect": side_effect}


def describe(tools):
    return [{"name": t["name"], "description": t["description"],
             "parameters": t["parameters"]} for t in tools]


def validate(parameters, args):
    if not isinstance(parameters, dict):
        return {"ok": False, "args": {},
                "errors": [f"parameters are not an object schema: {parameters!r}"]}
    if not isinstance(args, dict):
        return {"ok": False, "args": {},
                "errors": [f"arguments must be an object, got "
                           f"{type(args).__name__}"]}

    props = parameters.get("properties") or {}
    required = parameters.get("required") or []
    errors = []
    cleaned = {}

    for key in args:
        if key not in props:
            errors.append(_unknown(key, props))

    for name in required:
        if name not in args:
            errors.append(f"missing required argument {name!r}")

    for name, spec in props.items():
        if name in args:
            value, err = _check(name, spec, args[name])
            if err is not None:
                errors.append(err)
                continue
            enum = spec.get("enum")
            if enum is not None and value not in enum:
                errors.append(
                    f"argument {name!r}: {value!r} is not one of {enum!r}")
                continue
        elif "default" in spec:
            # A copy, or one call's edit to a default list becomes the next
            # call's arguments — the bug is invisible until the second call.
            value = copy.deepcopy(spec["default"])
        else:
            continue
        cleaned[name] = value

    return {"ok": not errors, "args": cleaned, "errors": errors}


def _object_schema(parameters):
    if not isinstance(parameters, dict) or parameters.get("type") != "object":
        return False
    props = parameters.get("properties")
    if props is not None and not isinstance(props, dict):
        return False
    req = parameters.get("required")
    return req is None or isinstance(req, list)


def _unknown(key, props):
    close = difflib.get_close_matches(key, props, n=1)
    if close:
        return f"unknown argument {key!r}; did you mean {close[0]!r}?"
    return f"unknown argument {key!r}"


def _type_error(name, want, value):
    return (f"argument {name!r}: expected {want}, got {value!r} "
            f"({type(value).__name__})")


def _check(name, spec, value):
    """(cleaned_value, error) for one provided argument. error is a str or None."""
    kind = spec.get("type")

    if kind == "string":
        if isinstance(value, str):
            return value, None
        return None, _type_error(name, "string", value)

    if kind == "boolean":
        if isinstance(value, bool):
            return value, None
        return None, (f"argument {name!r}: expected boolean, got {value!r}: only "
                      f"True and False are booleans, and the strings 'true'/'yes' "
                      f"are not")

    if kind == "integer":
        # bool first: isinstance(True, int) is True, and accepting True where an
        # integer was declared is the exact bug this stage exists to catch.
        if isinstance(value, bool):
            return None, (f"argument {name!r}: expected integer, got {value!r}: a "
                          f"boolean is not an integer even though isinstance("
                          f"True, int) is True in Python")
        if isinstance(value, int):
            return value, None
        if isinstance(value, str):
            text = value.strip()
            try:
                return int(text), None
            except ValueError:
                pass
            try:
                float(text)
            except ValueError:
                return None, _type_error(name, "integer", value)
            return None, (f"argument {name!r}: expected integer, got {value!r}: "
                          f"a fractional number is not an integer")
        return None, _type_error(name, "integer", value)

    if kind == "number":
        if isinstance(value, bool):
            return None, (f"argument {name!r}: expected number, got {value!r}: a "
                          f"boolean is not a number")
        if isinstance(value, (int, float)):
            return value, None
        if isinstance(value, str):
            text = value.strip()
            try:
                return int(text), None
            except ValueError:
                pass
            try:
                return float(text), None
            except ValueError:
                return None, _type_error(name, "number", value)
        return None, _type_error(name, "number", value)

    if kind == "array":
        if not isinstance(value, list):
            return None, _type_error(name, "array", value)
        items = spec.get("items")
        if not items:
            return value, None
        out = []
        for i, item in enumerate(value):
            got, err = _check(f"{name}[{i}]", items, item)
            if err is not None:
                return None, err
            out.append(got)
        return out, None

    if kind == "object":
        if isinstance(value, dict):
            return value, None
        return None, _type_error(name, "object", value)

    # No declared type: the schema did not say, so there is nothing to enforce.
    return value, None
