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

DESIGN DECISION - an invalid form is a 200 page, a raised exception is a 500 page.
    `POST /contact` validates the fields and, on failure, re-renders the form
    with `pages.contact_page(values, errors)`, one field-level message per bad
    input. That is the user's mistake, so the status stays 200 and the user keeps
    everything they typed. A route that raises (the deliberate `/boom`) takes the
    one error path instead: `_server_error` appends the full traceback to
    `SERVER_LOG` and answers with `pages.server_error()`, a generic 500 page. The
    detail never touches the response, and the two halves stay separate: a 4xx
    for wrong input, a 5xx for a broken server. Answering a bad form with the
    generic 500 (or with the framework's default error) is the mistake exercise
    11 removes.
"""

import http.server
import json
import threading
import time
import traceback
import urllib.parse
import uuid

from pages import (MIN_MESSAGE, contact_page, error_message, favicon_png,
                   not_found, og_image_png, order_page, pages, robots_txt,
                   server_error, sitemap_xml)

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

# The full traceback text of every exception the server caught. The user gets a
# generic 500 page; the detail lives here, the way a real server writes it to a
# log file. `check.py` can then prove the detail left the response without
# vanishing: it is in the log, not in the page.
SERVER_LOG = []


class SiteHandler(http.server.BaseHTTPRequestHandler):
    server_version = "web-launch-checklist/1.0"

    def do_GET(self):  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        try:
            path = urllib.parse.urlparse(self.path).path
            route = path.rstrip("/") or "/"
            base = "http://" + self.headers.get("Host", "")
            if route == "/contact":
                self._respond(200, contact_page())
            elif route == "/boom":
                # The deliberate failure: a route whose backend code raises. It
                # must leave through the one error path below, not crash the
                # connection and not print its traceback to the user.
                raise RuntimeError("boom: simulated backend failure")
            elif route == "/og-image.png":
                self._respond(200, og_image_png(), "image/png")
            elif route == "/favicon.ico":
                self._respond(200, favicon_png(), "image/png")
            elif route == "/logo.png":
                self._respond(200, favicon_png(), "image/png")
            elif route == "/chart.png":
                self._respond(200, og_image_png(), "image/png")
            elif route == "/robots.txt":
                self._respond(200, robots_txt(base), "text/plain; charset=utf-8")
            elif route == "/sitemap.xml":
                xml = sitemap_xml(sorted(pages().keys()), base)
                self._respond(200, xml, "application/xml; charset=utf-8")
            elif route == "/order":
                # One fresh key per form view; the page hands it to every click.
                self._respond(200, order_page(uuid.uuid4().hex))
            elif route == "/orders":
                self._respond(200, json.dumps({"count": len(ORDERS)}),
                              "application/json; charset=utf-8")
            else:
                site = pages()
                if route in site:
                    self._respond(200, site[route])
                else:
                    self._respond(404, not_found())
        except Exception:  # noqa: BLE001 - one error path for every exception
            self._server_error()

    def do_POST(self):  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        try:
            route = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
            length = int(self.headers.get("Content-Length", 0) or 0)
            fields = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))

            if route == "/contact":
                # Read the three fields; keep what the user typed so the page can
                # be re-rendered with it. Validation is the server's job, the
                # message text is `pages.error_message`'s, and rendering the
                # message next to the field is `pages.contact_page`'s.
                values = {name: (fields.get(name) or [""])[0]
                          for name in ("name", "email", "message")}
                errors = {}
                if not values["name"].strip():
                    errors["name"] = error_message("name", values["name"])
                email = values["email"].strip()
                local, _at, domain = email.partition("@")
                if email.count("@") != 1 or not local or "." not in domain:
                    errors["email"] = error_message("email", values["email"])
                if len(values["message"].strip()) < MIN_MESSAGE:
                    errors["message"] = error_message("message", values["message"])
                if errors:
                    # The user's mistake: same page, status 200, with the values
                    # kept and one message next to each bad field.
                    self._respond(200, contact_page(values, errors))
                else:
                    self._respond(200, (
                        "<!DOCTYPE html>\n"
                        '<html lang="en">\n'
                        "<head><meta charset=\"utf-8\">"
                        "<title>Message sent — Acme Tools</title></head>\n"
                        "<body>\n"
                        "<h1>Thanks — your message is on its way</h1>\n"
                        "<p>We will reply to the address you gave us.</p>\n"
                        "<p><a href=\"/\">Back to the home page</a></p>\n"
                        "</body>\n"
                        "</html>\n"))
                return

            if route != "/order":
                self._respond(404, not_found())
                return

            key = (fields.get("idempotency_key") or [""])[0]
            product = (fields.get("product") or ["widget"])[0]
            # No key means no idempotency promise: a client that sent none gets
            # one order per click. With a key, the key is the identity.
            identity = key
            if ORDER_DELAY:
                time.sleep(ORDER_DELAY)
            with ORDERS_LOCK:
                new = not key or identity not in SEEN
                if new:
                    SEEN.add(identity)
                    ORDERS.append((product, key))
                count = len(ORDERS)
            self._respond(200, json.dumps({"recorded": new, "count": count}),
                          "application/json; charset=utf-8")
        except Exception:  # noqa: BLE001 - one error path for every exception
            self._server_error()

    def _server_error(self):
        """Log the full detail and answer with the generic 500 page.

        The traceback goes to `SERVER_LOG` only; the response body is
        `pages.server_error()`, which carries no traceback, exception, path,
        version or environment variable. Every route that raises comes through
        here, so a deliberate `/boom` and an unexpected bug are handled alike.
        """
        SERVER_LOG.append(traceback.format_exc())
        self._respond(500, server_error())

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
    return http.server.ThreadingHTTPServer((host, port), SiteHandler)


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
