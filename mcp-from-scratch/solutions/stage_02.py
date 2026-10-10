"""MCP From Scratch — stage 2: the transports

SOLUTION. Two framings over in-memory streams: newline-delimited lines for
stdio, a POST for HTTP. The rules that matter are where the bytes go — messages
to `writer`, log lines to the sink — and that a partial line is a partial line
until its newline shows up.
"""

from stage_01 import ERRORS, decode, encode

_CHUNK = 65536


def _parse_error(message):
    """The one message `decode` fabricates: the -32700 response for text that is
    not JSON. Recognising it is how a transport sends it instead of handing it to
    the dispatcher as if it were a request."""
    if not isinstance(message, dict) or "method" in message:
        return False
    payload = message.get("error")
    return isinstance(payload, dict) and payload.get("code") == ERRORS["parse"]


def _write_log(sink, lines, level, text):
    """`[level] text` to the collected lines, and to the sink when there is one.
    A sink is a stream (anything with .write) or a callable taking the line."""
    line = f"[{level}] {text}"
    lines.append(line)
    if sink is not None:
        if hasattr(sink, "write"):
            sink.write(line + "\n")
        else:
            sink(line)
    return line


class LineTransport:
    def __init__(self, reader, writer, log=None):
        self.reader = reader
        self.writer = writer
        self.log_sink = log
        self.buffer = ""
        self.log_lines = []
        self.handled = 0
        self._done = False

    def send(self, message):
        """The one writer.write in the class: messages are the only thing that
        reaches stdout."""
        text = encode(message) + "\n"
        self.writer.write(text)
        return text

    def receive(self):
        """The next raw line, or None. A chunk boundary and a missing trailing
        newline are both just an incomplete buffer."""
        while True:
            if "\n" in self.buffer:
                line, self.buffer = self.buffer.split("\n", 1)
                return line[:-1] if line.endswith("\r") else line
            chunk = self._read()
            if chunk == "":
                if self.buffer:
                    line, self.buffer = self.buffer, ""
                    return line[:-1] if line.endswith("\r") else line
                return None
            self.buffer += chunk

    def _read(self):
        if self._done:
            return ""
        if callable(self.reader):
            chunk = self.reader()
        else:
            chunk = self.reader.read(_CHUNK)
        if chunk is None or chunk == "":
            self._done = True
            return ""
        return chunk

    def log(self, level, text):
        """Tagged, and to the sink — never to `writer`, which is stdout."""
        _write_log(self.log_sink, self.log_lines, level, text)

    def run(self, dispatcher, *, limit=None):
        count = 0
        while limit is None or count < limit:
            raw = self.receive()
            if raw is None:
                break
            message = decode(raw)
            if _parse_error(message):
                self.send(message)
                count += 1
                continue
            response = dispatcher.dispatch(message)
            if response is not None:
                self.send(response)
            count += 1
        self.handled += count
        return count


class SseWriter:
    def __init__(self):
        self.lines = []

    def event(self, message):
        chunk = f"event: message\ndata: {encode(message)}\n\n"
        self.lines.append(chunk)
        return chunk


class HttpTransport:
    def __init__(self, dispatcher, log=None):
        self.dispatcher = dispatcher
        self.log_sink = log
        self.log_lines = []
        self.sse = SseWriter()
        self.sse_events = self.sse.lines

    def log(self, level, text):
        """Same discipline as the stdio transport."""
        _write_log(self.log_sink, self.log_lines, level, text)

    def post(self, body):
        message = decode(body)
        if _parse_error(message):
            self.log("error", "a POST body that is not JSON")
            return 200, "application/json", encode(message)
        response = self.dispatcher.dispatch(message)
        if response is None:
            # a notification has nothing to send back, and a client waiting on a
            # body that will never come is the HTTP version of a hung stdio server.
            return 202, "", ""
        return 200, "application/json", encode(response)
