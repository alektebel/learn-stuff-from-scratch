"""MCP From Scratch — stage 6: out-of-band messages — who hears what

SOLUTION. Three registries with their `notify` callback injected, so each is
testable without a transport, and the two rules that are easy to get backwards:
a cancelled request gets no response at all, and a cancellation nobody is
waiting for is recorded, never answered with an error.
"""

from stage_01 import ERRORS, ProtocolError, notification


def _valid_request_id(value):
    # bool first: isinstance(True, int) is True, and a boolean is not a request
    # id, not a progress token, and not a key in any of these registries.
    if isinstance(value, bool):
        return False
    return isinstance(value, (str, int))


class Subscriptions:
    def __init__(self, notify, *, known=None):
        self._notify = notify
        self._known = known
        self.subscribed = set()

    def _uri(self, params):
        uri = params.get("uri")
        if not isinstance(uri, str) or not uri:
            raise ProtocolError(ERRORS["invalid_params"],
                                "resources/subscribe needs a uri string")
        return uri

    def subscribe(self, params, session):
        uri = self._uri(params)
        if self._known is not None and not self._known(uri):
            raise ProtocolError(ERRORS["resource_not_found"], "Resource not found",
                                data={"uri": uri})
        self.subscribed.add(uri)
        return {}

    def unsubscribe(self, params, session):
        self.subscribed.discard(self._uri(params))
        return {}

    def updated(self, uri):
        if uri not in self.subscribed:
            return 0
        self._notify("notifications/resources/updated", {"uri": uri})
        return 1


class Progress:
    def __init__(self, notify):
        self._notify = notify
        self.sent = []
        self.progress = {}
        self.totals = {}

    def track(self, params):
        meta = params.get("_meta")
        if not isinstance(meta, dict):
            return None
        token = meta.get("progressToken")
        if not _valid_request_id(token):
            return None
        return token

    def report(self, token, progress, *, total=None, message=None):
        last = self.progress.get(token)
        if last is not None and progress <= last:
            raise ValueError(
                f"progress for token {token!r} must increase: {last!r} then "
                f"{progress!r} — a progress value that does not go up is a bug "
                f"in the server, not a message to send")
        recorded = self.totals.get(token)
        if total is not None and recorded is not None and total != recorded:
            raise ValueError(
                f"total for token {token!r} must not change: {recorded!r} then "
                f"{total!r} — the client has already drawn the axis")
        params = {"progressToken": token, "progress": progress}
        if total is not None:
            params["total"] = total
        if message is not None:
            params["message"] = message
        sent = notification("notifications/progress", params)
        self.progress[token] = progress
        if total is not None:
            self.totals[token] = total
        self.sent.append(sent)
        self._notify("notifications/progress", params)
        return sent


class Cancellations:
    def __init__(self):
        self.cancelled = set()
        self.protected = set()
        self.ignored = []
        self.in_flight = set()

    def _ignore(self, request_id, reason):
        self.ignored.append({"requestId": request_id, "reason": reason})
        return None

    def cancel(self, params, session):
        request_id = params.get("requestId")
        if not _valid_request_id(request_id):
            return self._ignore(
                request_id,
                "requestId must be a string or an integer: a notification about "
                "a request that cannot be identified is dropped, not answered")
        if request_id in self.protected:
            return self._ignore(
                request_id,
                "the request is protected: a client MUST NOT cancel its "
                "initialize request, and a server that lets it be cancelled has "
                "a session with no handshake")
        if request_id in self.cancelled:
            return self._ignore(request_id,
                                "the request was already cancelled: the second "
                                "notification is a no-op")
        if request_id not in self.in_flight:
            return self._ignore(
                request_id,
                "the request is not in flight: it was never started, or it was "
                "already answered — the notification may arrive after the work "
                "finished, which the spec allows, and nobody is left to answer")
        self.cancelled.add(request_id)
        return None

    def is_cancelled(self, request_id):
        return request_id in self.cancelled

    def answer_for(self, request_id, response):
        # The request is over either way, so it leaves the in-flight registry:
        # that is what makes a late notification/cancelled ignored.
        self.in_flight.discard(request_id)
        if request_id in self.cancelled:
            return None
        return response


def install(server, *, subscriptions=None, progress=None, cancellations=None):
    if cancellations is None:
        cancellations = Cancellations()
    server.add("notifications/cancelled", cancellations.cancel)
    data = server.session.setdefault("data", {})
    data["cancellations"] = cancellations
    if subscriptions is not None:
        server.add("resources/subscribe", subscriptions.subscribe)
        server.add("resources/unsubscribe", subscriptions.unsubscribe)
        data["subscriptions"] = subscriptions
    if progress is not None:
        data["progress"] = progress
