"""MCP From Scratch — stage 2: two transports, one of them made of lines

DESIGN DECISION — stdout carries messages and nothing else.
    MCP's spec is blunt: "The server MUST NOT write anything to its stdout that
    is not a valid MCP message." A `print()` left in a handler, a warning, a
    progress line — any one of them corrupts the stream, and it does not fail
    loudly: the client reads half a message, or reads a "message" that is prose,
    and then waits forever for the rest of a response that will never come. So
    this stage draws the line in code, not in a convention: `send` is the ONLY
    method that touches `writer`, and `log` writes to a separate sink (stderr in
    real life). When those two cannot be confused, the whole class of bug is
    impossible rather than merely discouraged.

DESIGN DECISION — a line is a message, and a message is exactly one line.
    stdio framing is newline-delimited, which makes the newline a RESERVED byte:
    `encode` (stage 1) never emits one inside a message, and `receive` splits on
    it. The interesting part is what arrives on the way in, because a reader hands
    over arbitrary chunks: one message can arrive split across two reads, several
    messages can arrive in one read, a `\\r\\n` ending may be in use, and the last
    line may have no trailing newline at all. All four are the same fix — keep the
    tail in `.buffer` until a `\\n` shows up — and all four are invisible until a
    real stream does them to you.

DESIGN DECISION — the transport owns no parsing policy.
    A line that is not JSON is not the transport's business to diagnose: stage 1's
    `decode` already returns the -32700 response the server owes the client, and
    the transport just sends it. If the transport parsed, it would also have to
    choose a code and a message, and those decisions would live in two places and
    eventually disagree. So `run` is a loop, `send` is one `encode`, and every
    error the caller sees came from stage 1.

DESIGN DECISION — HTTP is where "the client must not wait" becomes a status code.
    A POST that carries a request gets `200` and the encoded response. A POST that
    carries a notification gets `202` and an EMPTY body: there is nothing to send
    back, and a client waiting for a body that will never exist is the HTTP
    version of the hanging stdio server. A body that is not JSON still gets `200`
    with the -32700 error — the transport is alive, the message was not. Streaming
    (SSE, `text/event-stream`) is a choice the CLIENT makes with its `Accept`
    header, and `post(body)` never sees that header, so this stage answers JSON
    either way: it produces SSE framing only through `SseWriter`, the exact
    "event: message / data: {json} / blank line" block SSE is made of.

Duck typing this stage accepts:
    - `reader`: anything with `.read(n)` (a text stream), OR a zero-argument
      callable returning the next chunk as a `str`; `""` or `None` means the
      stream is over. The callable is how a check models a chunk boundary.
    - `writer`: anything with `.write(text)` — `sys.stdout`, `io.StringIO`, a
      small recorder. Messages go here and nothing else does.
    - `log`: the sink for log lines — anything with `.write(text)`, or a callable
      taking the finished line. `sys.stderr` in real life; `None` means the lines
      are collected in `.log_lines` only.

TODO: implement

    class LineTransport                       # stdio-shaped: newline-delimited
        __init__(self, reader, writer, log=None)
        .buffer -> str                        # read, but not yet a complete line
        .log_lines -> list[str]               # "[level] text" for every log() call
        .handled -> int                       # messages handled over its life
        send(message) -> str
            encode(message) + "\\n" written to `writer`; returns what was written.
            The only writer.write in the class.
        receive() -> str | None
            The next RAW line with its newline stripped, or None once the reader
            is exhausted. Splits on "\\n", accepts a trailing "\\r", keeps a
            partial tail in `.buffer`, and returns a final line that arrived
            without a trailing newline.
        log(level, text) -> None
            "[level] text" to `.log_lines` and to the sink only — never `writer`.
        run(dispatcher, *, limit=None) -> int
            Read until the reader is exhausted (or `limit` messages have been
            handled), decode each line, dispatch it, send the response when there
            is one (a notification has none), and return how many were handled. A
            line `decode` rejects is sent as its -32700 response, not dispatched
            a second time.

    class SseWriter                           # "event: message\\ndata: {json}\\n\\n"
        __init__(self)
        .lines -> list[str]                   # the framed events written so far
        event(message) -> str                 # the framed event, and it is appended

    class HttpTransport                       # streamable HTTP, for a POST
        __init__(self, dispatcher, log=None)
        .sse_events -> list[str]              # the SSE events written so far
        post(body) -> tuple[int, str, str]    # (status, content_type, body_text)
            request      -> 200, "application/json", the encoded response
            notification -> 202, "", ""
            not JSON     -> 200, "application/json", the -32700 error
"""


class LineTransport:
    def __init__(self, reader, writer, log=None):
        raise NotImplementedError("stage 2: implement LineTransport.__init__()")

    def send(self, message):
        raise NotImplementedError("stage 2: implement LineTransport.send()")

    def receive(self):
        raise NotImplementedError("stage 2: implement LineTransport.receive()")

    def log(self, level, text):
        raise NotImplementedError("stage 2: implement LineTransport.log()")

    def run(self, dispatcher, *, limit=None):
        raise NotImplementedError("stage 2: implement LineTransport.run()")


class SseWriter:
    def __init__(self):
        raise NotImplementedError("stage 2: implement SseWriter.__init__()")

    def event(self, message):
        raise NotImplementedError("stage 2: implement SseWriter.event()")


class HttpTransport:
    def __init__(self, dispatcher, log=None):
        raise NotImplementedError("stage 2: implement HttpTransport.__init__()")

    def log(self, level, text):
        raise NotImplementedError("stage 2: implement HttpTransport.log()")

    def post(self, body):
        raise NotImplementedError("stage 2: implement HttpTransport.post()")
