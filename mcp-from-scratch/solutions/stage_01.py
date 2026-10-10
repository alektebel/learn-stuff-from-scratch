"""MCP From Scratch — stage 1: the envelope, and the four ways to answer it

SOLUTION. One validation pass, one dispatch switch, and the spec's codes. The
only subtleties are where the response's id comes from (the request's, or null
when it cannot be determined) and the two failures that have nobody to answer to.
"""

import json

ERRORS = {
    "parse": -32700,
    "invalid_request": -32600,
    "method_not_found": -32601,
    "invalid_params": -32602,
    "internal": -32603,
    "resource_not_found": -32002,
}


class ProtocolError(Exception):
    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_error(self, id):
        return error(id, self.code, self.message, self.data)


def request(id, method, params=None):
    message = {"jsonrpc": "2.0", "id": id, "method": method}
    if params is not None:
        message["params"] = params
    return message


def notification(method, params=None):
    message = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        message["params"] = params
    return message


def result(id, value):
    return {"jsonrpc": "2.0", "id": id, "result": value}


def error(id, code, message, data=None):
    payload = {"code": code, "message": message}
    if data is not None:
        payload["data"] = data
    return {"jsonrpc": "2.0", "id": id, "error": payload}


def decode(raw):
    try:
        return json.loads(raw)
    except ValueError as exc:
        # JSON-RPC: when the id cannot be determined the response carries null.
        return error(None, ERRORS["parse"], f"the message is not JSON: {exc}")


def encode(message):
    return json.dumps(message, sort_keys=True, separators=(",", ":"))


def _valid_id(value):
    # bool first: isinstance(True, int) is True, and `{"id": true}` is not a
    # request id, it is a bug on the other end.
    if isinstance(value, bool):
        return False
    return isinstance(value, (str, int))


class Dispatcher:
    def __init__(self):
        self.handlers = {}
        self.failures = []

    def add(self, method, handler):
        self.handlers[method] = handler
        return handler

    def dispatch(self, message):
        if isinstance(message, list):
            return error(None, ERRORS["invalid_request"],
                         "JSON-RPC batching was removed from MCP: send one "
                         "message per line")

        id = None
        has_id = False
        if isinstance(message, dict):
            candidate = message.get("id")
            has_id = "id" in message
            if has_id and _valid_id(candidate):
                id = candidate

        if not isinstance(message, dict):
            return error(None, ERRORS["invalid_request"],
                         f"a message is an object, got {type(message).__name__}")
        if message.get("jsonrpc") != "2.0":
            return error(id, ERRORS["invalid_request"],
                         'jsonrpc must be exactly "2.0"')
        if has_id and not _valid_id(message.get("id")):
            return error(None, ERRORS["invalid_request"],
                         "id must be a string or an integer (MCP's RequestId): "
                         "a null or boolean id cannot be matched to a response")
        method = message.get("method")
        if not isinstance(method, str) or not method:
            return error(id, ERRORS["invalid_request"],
                         "method must be a non-empty string")
        params = message.get("params", {})
        if not isinstance(params, dict):
            return error(id, ERRORS["invalid_request"],
                         "params must be an object")

        handler = self.handlers.get(method)
        if handler is None:
            if not has_id:
                self.failures.append({"method": method,
                                      "error": f"unknown method {method!r}"})
                return None
            return error(id, ERRORS["method_not_found"],
                         f"unknown method {method!r}")

        try:
            value = handler(params)
        except ProtocolError as exc:
            if not has_id:
                self.failures.append({"method": method,
                                      "error": f"{exc.code}: {exc.message}"})
                return None
            return exc.to_error(id)
        except Exception as exc:                      # noqa: BLE001 - classified
            if not has_id:
                self.failures.append({"method": method,
                                      "error": f"{type(exc).__name__}: {exc}"})
                return None
            return error(id, ERRORS["internal"], f"{type(exc).__name__}: {exc}")

        if not has_id:
            return None

        try:
            encode(value)
        except (TypeError, ValueError):
            return error(id, ERRORS["internal"],
                         f"the handler returned a {type(value).__name__}, which is "
                         f"not JSON-serializable")
        return result(id, value)
