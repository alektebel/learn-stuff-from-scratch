"""MCP From Scratch — stage 1: the envelope, and the four ways to answer it

DESIGN DECISION — the envelope is validated before anything else happens.
    Every other stage in this course assumes a message that arrived intact: a
    method name that is a string, an id that can be matched to a response, params
    that are an object. Those assumptions are not free, and getting them wrong is
    invisible until a client hangs — which is why the whole envelope is checked in
    one place, with the spec's own codes, before a handler is called.

DESIGN DECISION — a request is a notification with an id.
    JSON-RPC's rule is on the PRESENCE of the `id` member, and MCP narrows the
    type to `string | integer`. So `{"id": null}` is neither: it is a malformed
    request (-32600), because a null id cannot be matched to anything on the way
    back. Two failures follow from getting this backwards — a client waiting
    forever for the response to a message the server treated as a notification,
    and a server answering a message that had no id to answer to.

DESIGN DECISION — an internal error is a code and a type, not a stack trace and
not the request.
    The message that goes back names the exception's type and its own message,
    and nothing else. Tracebacks leak paths and versions to a caller who did not
    ask for them, and echoing the REQUEST that caused the failure copies whatever
    the caller sent — including the secret sitting in the parameters — into an
    error the client logs and a model reads. Whoever wrote the handler writes the
    message; the dispatcher must not add to it.

DESIGN DECISION — a batch is refused, not half-supported.
    MCP removed JSON-RPC batching. A server that answers the first element of an
    array and drops the rest is worse than one that says -32600, because the
    client's remaining requests silently never happen.

TODO: implement

    ERRORS = {"parse": -32700, "invalid_request": -32600, "method_not_found": -32601,
              "invalid_params": -32602, "internal": -32603,
              "resource_not_found": -32002}

    request(id, method, params=None) -> dict      # an id member is what makes it a request
    notification(method, params=None) -> dict     # no id member at all
    result(id, value) -> dict                     # exactly one of result/error
    error(id, code, message, data=None) -> dict   # data only when there is one

    class ProtocolError(Exception)
        ProtocolError(code, message, data=None), carrying .code .message .data,
        and to_error(id) -> the error response for that id.

    decode(raw) -> dict
        JSON text to a message. When the text is not JSON, return the -32700
        error RESPONSE to send (JSON-RPC sends `id: null` when the id cannot be
        determined — the one place a null id is correct).

    encode(message) -> str
        One line: json.dumps(..., sort_keys=True, separators=(",", ":")). A
        message must never contain an embedded newline (MCP's stdio framing is
        newline-delimited), and two encodings of the same message must be the
        same bytes or every transport test is a coin flip.

    class Dispatcher
        __init__()
        .handlers -> dict[method, handler]        # registration order, in a dict
        .failures -> list[dict]                   # failures with no id to report
                                                  # them to: {"method", "error"}
        add(method, handler) -> handler           # usable as a decorator
        dispatch(message) -> dict | None
            The response to send back, or None when nothing may be sent (a
            notification, or a cancelled request). Rules, in this order:
              - a list is a batch: -32600, id null, and no handler runs;
              - a non-dict, a missing or non-"2.0" jsonrpc, a missing or empty
                method, a params that is not an object, and an id that is present
                but neither a string nor an integer: -32600, id null (except when
                the id itself was well-formed, which is echoed) ;
              - an unknown method: -32601 for a request, nothing for a
                notification (a notification has nobody to answer to — record it
                in .failures instead of inventing a response);
              - the handler is called with (params, ) where params is {} when
                absent; a ProtocolError becomes its own code/message/data, any
                other exception becomes -32603 whose message is
                "{type}: {the exception's own message}" — never the params, never
                a traceback;
              - a result that json.dumps cannot serialize is -32603 naming the
                type, never a broken line on the wire;
              - for a notification the handler still runs and its return value is
                discarded; its exceptions land in .failures.
"""


ERRORS = {}                          # TODO: the spec's codes


def request(id, method, params=None):
    raise NotImplementedError("stage 1: implement request()")


def notification(method, params=None):
    raise NotImplementedError("stage 1: implement notification()")


def result(id, value):
    raise NotImplementedError("stage 1: implement result()")


def error(id, code, message, data=None):
    raise NotImplementedError("stage 1: implement error()")


class ProtocolError(Exception):
    def __init__(self, code, message, data=None):
        raise NotImplementedError("stage 1: implement ProtocolError")


def decode(raw):
    raise NotImplementedError("stage 1: implement decode()")


def encode(message):
    raise NotImplementedError("stage 1: implement encode()")


class Dispatcher:
    def __init__(self):
        raise NotImplementedError("stage 1: implement Dispatcher")

    def add(self, method, handler):
        raise NotImplementedError("stage 1: implement Dispatcher.add()")

    def dispatch(self, message):
        raise NotImplementedError("stage 1: implement Dispatcher.dispatch()")
