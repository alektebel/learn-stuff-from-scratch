"""
A minimal stdlib web server, from scratch.

WHAT IT IMPLEMENTS
    A `http.server` with explicit routing over the site in `pages.py`. A request
    for a known path gets its page and status 200; any other path gets the site's
    404 page and status 404. There is no framework: a framework would answer
    unknown paths with the app shell and status 200, silently, which is exactly
    the soft-404 this exercise is about.

DESIGN DECISION - route by an explicit map, not by "does the file exist".
    A file-based server (`SimpleHTTPRequestHandler`) blurs two different failures:
    a page that was never written and a page that was deleted. The map makes the
    site's public surface explicit, so the crawler and the server agree on what
    exists. The cost: static assets (CSS, images) need their own branch, which is
    why `/og-image.png`, `/favicon.ico`, `/logo.png` and `/chart.png` are routed
    here rather than found on disk. The body images reuse the two provided PNG
    helpers, `favicon_png` and `og_image_png`: exercise 8 is about the `alt`
    attribute, not about image encoding, and a route that serves a real `image/png`
    keeps the site honest without a second encoder.

DESIGN DECISION - the 404 status comes from the server, the 404 body from the
    site. `pages.not_found()` returns a helpful page that links home; the handler
    decides the status. This separation is what lets exercise 1 grade "real 404"
    and "body links home" as two independent things.

DESIGN DECISION - ThreadingHTTPServer, port 0 in tests.
    `make_server(port=0)` lets `check.py` start the server in-process, learn the
    port the OS assigned, crawl it, and shut it down. The CLI defaults to 8000.

DESIGN DECISION - `_respond` accepts bytes or text. Page bodies are strings, but
    the Open Graph image is raw PNG bytes. One responder that encodes strings and
    passes bytes through avoids a second copy of the headers logic.

DESIGN DECISION - the order API dedups on the idempotency key, not on the body.
    `POST /order` records `(product, key)` once per key; a repeat with the same
    key answers 200 with the same confirmation and records nothing. The exercise
    is a user who clicks three times: the three requests are identical because
    they share one form's key, and the server must tolerate the repeat without
    charging three times. Deduping on the body instead of the key is the classic
    mistake: two different keys with the same product would collapse into one.

DESIGN DECISION - the simulated API delay is a constant, and tests keep it zero.
    `ORDER_DELAY` is the three seconds a real order call might take. `check.py`
    leaves it at 0.0 so the suite runs in milliseconds; run `serve.py` by hand
    and set it to 3.0 to watch `impatient.py` show the wait. Grading the delay
    would make every check slow and flaky, and a stdlib observer cannot see the
    browser paint anyway, so the immediate-state half is graded structurally.

DESIGN DECISION - the order state is a module-level list and set behind one lock.
    `ThreadingHTTPServer` serves each request on its own thread, so the count and
    the seen-set are shared mutable state; a `threading.Lock` keeps a click and
    the callback that would duplicate it from interleaving. The alternative -
    per-connection state - would forget every key between requests and tolerate
    nothing. A process restart forgets the orders, which is fine for the toy: it
    is an idempotency key, not durable storage.
"""

import http.server
import json
import threading
import time
import urllib.parse
import uuid

from pages import (favicon_png, not_found, og_image_png, order_page, pages,
                   robots_txt, sitemap_xml)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# The simulated order-API latency, in seconds. Tests keep it 0 so the suite is
# fast; set it to 3.0 by hand to watch the impatient observer wait. See the
# "simulated API delay" design decision above.
ORDER_DELAY = 0.0

# Orders recorded as (product, key), and the keys already seen. Guarded by one
# lock because ThreadingHTTPServer handles requests on separate threads.
ORDERS = []
SEEN = set()
ORDERS_LOCK = threading.Lock()


class SiteHandler(http.server.BaseHTTPRequestHandler):
    server_version = "web-launch-checklist/1.0"

    def do_GET(self):  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        # TODO: route the request path: a path in pages() gets status 200 and its HTML; GET /og-image.png serves og_image_png() as image/png; GET /favicon.ico serves favicon_png() as image/png; GET /logo.png and /chart.png serve a real image/png (reuse favicon_png and og_image_png - no new image code); GET /robots.txt serves robots_txt(base) as text/plain; GET /sitemap.xml serves sitemap_xml over the page paths as application/xml (base = Host header); GET /order serves order_page(uuid.uuid4().hex) (a fresh key per form view); GET /orders serves {"count": len(ORDERS)} as application/json; anything else gets the 404 page with status 404 (no redirect to /)
        raise NotImplementedError("SiteHandler.do_GET")

    def do_POST(self):  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        # TODO: handle POST /order: read the urlencoded body, take `idempotency_key`; if the key was seen already answer 200 with the same confirmation and record nothing; otherwise record (product, key) and answer 200. Keep ORDERS and SEEN under ORDERS_LOCK, and a missing/empty key means no idempotency promise (record every click). Any other POST path is a 404
        raise NotImplementedError("SiteHandler.do_POST")

    def _respond(self, status, body, content_type="text/html; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # keep the check output readable
        pass


def make_server(host=DEFAULT_HOST, port=0):
    """Return a running-ready server bound to `host:port` (0 = ask the OS)."""
    # TODO: return an http.server that routes the paths in pages() to status 200, and every other path to the 404 page with status 404
    raise NotImplementedError("make_server")


def main():
    server = make_server(port=DEFAULT_PORT)
    host, port = server.server_address[0], server.server_address[1]
    print(f"serving http://{host}:{port}/ (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
