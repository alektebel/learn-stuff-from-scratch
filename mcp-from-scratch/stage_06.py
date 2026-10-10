"""MCP From Scratch — stage 6: out-of-band messages — who hears what

Some of a server's traffic is not an answer to anything: a resource changed, a
slow tool is halfway done, the client gave up on a request it started. None of
those fit the request/response pair, and all three are places where the easy
implementation is the wrong one.

DESIGN DECISION — three registries, each with `notify` injected.
    Subscriptions answers "which connection cares about this uri", Progress
    answers "which request asked for progress and how far along it is", and
    Cancellations answers "which request has been given up on". Each takes a
    `notify(method, params=None)` callback instead of a server, so a registry can
    be exercised with nothing but a list to append to: no transport, no socket,
    no server. The state is small on purpose — who hears what is cheap to get
    wrong and expensive to debug.

DESIGN DECISION — a cancelled request gets NO response.
    The spec, for receivers of `notifications/cancelled`: "SHOULD: ... Not send a
    response for the cancelled request". `answer_for` is that rule in one place:
    None for a cancelled id, the response otherwise. Sending -32800 ("request
    cancelled") is what an implementation does when it cannot bear to have
    written nothing: the client has already given up and cannot match the answer
    to anything it is still waiting for, and a response to a request it cancelled
    reads as a protocol violation in its log. None is not a bug here; it is the
    message.

DESIGN DECISION — a notification nobody can answer is IGNORED, never an error.
    `notifications/cancelled` carries `requestId` and an optional `reason`. A
    cancellation that arrives for a request that is unknown, already answered, or
    already cancelled is not an error — the spec explicitly allows the
    notification to arrive after the work finished — and there is nobody to send
    an error TO. So it lands in `.ignored` with a reason and returns None.
    `.in_flight` is what makes "in flight" checkable: the ids the server is still
    working on, removed by `answer_for`, which is the one place a request is
    answered.

DESIGN DECISION — `initialize` is never cancellable, and the reason says why.
    The spec: a client MUST NOT cancel its `initialize` request. A server that
    lets it be cancelled is left with a session that has no handshake — no
    negotiated protocol version, no client capabilities, nothing to answer with.
    `.protected` holds those ids and a cancel of one lands in `.ignored` with the
    reason, exactly like an unknown id.

DESIGN DECISION — an absent progress token is None, and the server must not
invent one.
    A client asks for progress with `params._meta.progressToken`, and it is
    optional. A server that makes a token up sends progress for a request that
    never asked, and the client drops those notifications or, worse, counts them.
    MCP's ProgressToken is `string | integer`, and a boolean is neither —
    `isinstance(True, int)` is True and `True` is not a token.

DESIGN DECISION — progress only goes up, and `total` never changes.
    A `progress` value that is not greater than the last one sent for that token
    is a bug in the server, not a message to send: the spec's contract is
    "progress increases every time progress is made", and a bar that goes
    backwards cannot be read. `report` raises ValueError naming both values, and
    `total`, once sent for a token, must not change either — the client has
    already drawn the axis. A different token starts clean.

DESIGN DECISION — subscribe is idempotent; an unknown uri is -32002.
    `resources/subscribe` of a uri the server cannot serve is
    ProtocolError(ERRORS["resource_not_found"], "Resource not found",
    data={"uri": uri}) — the same code and the same data the contract gives
    `resources/read` — and it must NOT subscribe. Subscribing twice must not
    create two subscriptions (the subscribed set makes it a no-op), or `updated`
    would notify the same connection twice. `updated(uri)` sends exactly one
    notification for a subscribed uri, none for the rest, and returns how many it
    sent. Without a `known` oracle the registry has nothing to test the uri
    against, so it accepts rather than inventing a rejection.

DESIGN DECISION — install registers the handlers; progress is the outbound one.
    `install` registers `notifications/cancelled` (a server with no registry
    still gets the rule, so one is made if none was given) and, when a
    Subscriptions registry is given, `resources/subscribe` and
    `resources/unsubscribe`. Nothing receives `notifications/progress`: progress
    is the outbound side, and a server would answer a client's progress
    notification with -32601. The registries it was given are hung on
    `session["data"]`, which is what the contract's session is for: a handler
    gets the session and nothing else, so it has to be able to find them.

    The solution imports ERRORS, ProtocolError and notification from stage 1.

TODO: implement

    class Subscriptions
        __init__(self, notify, *, known=None) -> None
            notify: notify(method, params=None) — `server.notify` in a real
                    server, a list-appender in a check.
            known:  a callable uri -> bool, or None (see above).
        .subscribed -> set[str]
        subscribe(params, session) -> dict        # params["uri"]; -> {}
            unknown uri: ProtocolError(-32002, "Resource not found",
                                       data={"uri": uri}); twice is a no-op.
        unsubscribe(params, session) -> dict      # -> {}; not subscribed is a no-op
        updated(uri) -> int
            One `notifications/resources/updated` per subscribed uri: 1 when the
            uri is subscribed, 0 otherwise.

    class Progress
        __init__(self, notify) -> None
        .sent -> list[dict]                       # every message it sent
        track(params) -> str | int | None
            params["_meta"]["progressToken"], only when it is a str or an int
            (a bool is not); None when the request did not ask for progress.
        report(token, progress, *, total=None, message=None) -> dict
            The `notifications/progress` message sent (and recorded in .sent):
            `progressToken` and `progress` always; `total` and `message` only
            when given. `progress` must increase for its token and `total` must
            not change, or ValueError names both values.

    class Cancellations
        __init__(self) -> None
        .cancelled -> set                         # ids cancelled while in flight
        .protected -> set                         # ids that must never be cancelled
        .ignored -> list[dict]                    # [{"requestId", "reason"}]
        .in_flight -> set                         # ids the server still owes an answer
        cancel(params, session) -> None
            params["requestId"], params["reason"]?. Marks the id when it is in
            flight; otherwise records why in .ignored. Never raises: it is a
            notification, and there is nobody to answer to.
        is_cancelled(request_id) -> bool
        answer_for(request_id, response) -> dict | None
            None when the id is cancelled; otherwise `response`. Either way the id
            leaves .in_flight: the request is over.

    install(server, *, subscriptions=None, progress=None, cancellations=None) -> None
"""


class Subscriptions:
    def __init__(self, notify, *, known=None):
        raise NotImplementedError("stage 6: implement Subscriptions()")

    def subscribe(self, params, session):
        raise NotImplementedError("stage 6: implement Subscriptions.subscribe()")

    def unsubscribe(self, params, session):
        raise NotImplementedError("stage 6: implement Subscriptions.unsubscribe()")

    def updated(self, uri):
        raise NotImplementedError("stage 6: implement Subscriptions.updated()")


class Progress:
    def __init__(self, notify):
        raise NotImplementedError("stage 6: implement Progress()")

    def track(self, params):
        raise NotImplementedError("stage 6: implement Progress.track()")

    def report(self, token, progress, *, total=None, message=None):
        raise NotImplementedError("stage 6: implement Progress.report()")


class Cancellations:
    def __init__(self):
        raise NotImplementedError("stage 6: implement Cancellations()")

    def cancel(self, params, session):
        raise NotImplementedError("stage 6: implement Cancellations.cancel()")

    def is_cancelled(self, request_id):
        raise NotImplementedError("stage 6: implement Cancellations.is_cancelled()")

    def answer_for(self, request_id, response):
        raise NotImplementedError("stage 6: implement Cancellations.answer_for()")


def install(server, *, subscriptions=None, progress=None, cancellations=None):
    raise NotImplementedError("stage 6: implement install()")
