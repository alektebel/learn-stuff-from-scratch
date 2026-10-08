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
    why `/og-image.png` is routed here rather than found on disk.

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
"""

import http.server
import urllib.parse

from pages import not_found, og_image_png, pages, robots_txt, sitemap_xml

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


class SiteHandler(http.server.BaseHTTPRequestHandler):
    server_version = "web-launch-checklist/1.0"

    def do_GET(self):  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        # TODO: route the request path: a path in pages() gets status 200 and its HTML; GET /og-image.png serves og_image_png() as image/png; GET /robots.txt serves robots_txt(base) as text/plain; GET /sitemap.xml serves sitemap_xml over the page paths as application/xml (base = Host header); anything else gets the 404 page with status 404 (no redirect to /)
        raise NotImplementedError("SiteHandler.do_GET")

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
