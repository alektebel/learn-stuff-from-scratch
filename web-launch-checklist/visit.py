"""
visit.py — the provided observer. Plays the role of a browser's first visit.

Point a browser at a page and it fetches more than the page: the favicon, the
Open Graph image, anything the markup links to. Some of those requests are for
URLs the page never names — the browser guesses `/favicon.ico` for every origin —
and each guess that 404s is a full round trip that ends in the site's custom 404
page. This observer records every request one visit makes, what each cost in
bytes, the cookies the response set, and the actual pixel size of the icons it
fetched. It is the measuring instrument for exercise 4 (favicon) and the cookie
half of exercise 13; read it, do not edit it. It is symlinked into `solutions/`
so the mutation harness can carry it.

DESIGN DECISION - the implicit `/favicon.ico` request is the point, so it is
    recorded, not hidden. A page that declares no `<link rel="icon">` still makes
    a real browser ask for `/favicon.ico` at the origin root: the browser guesses.
    Dropping that request would hide the exercise. The observer issues it with
    `from_link=False`, while an icon the markup actually declared is recorded with
    `from_link=True`, so a report can separate "the page asked for this" from "the
    browser invented it".

DESIGN DECISION - a declared icon is fetched once per unique href, from the origin
    under test. Two pages linking the same `/favicon.ico` are one request, the way
    a browser caches it. A declared absolute URL is reduced to its path and fetched
    locally, because the pages name the canonical `SITE_URL`
    ("https://example.com"), which is not reachable without a network here.

DESIGN DECISION - an icon is measured from its own header bytes, not trusted from
    the `sizes` attribute. The `sizes` the page declares is a claim; the observer
    reads the real width and height out of the PNG/ICO/GIF bytes, so a page that
    declares 16x16 while serving 32x32 is caught.

Standard library only (`urllib.request`, `urllib.parse`, `html.parser`, `struct`,
`argparse`). No network beyond the server it is given.
"""

import argparse
import html.parser
import struct
import urllib.parse
import urllib.request

USER_AGENT = "web-launch-checklist-visit/1.0"

# The icon sizes this observer asks for: the two that a browser's implicit favicon
# request and a `<link rel="icon" sizes=...>` are allowed to declare. The checker
# accepts an icon at either size, and a page's declared size must match the bytes.
ICON_SIZES = ((32, 32), (16, 16))


class Request:
    """One HTTP request a first visit made, and what came back."""

    def __init__(self, path, status, body, content_type, from_link):
        self.path = path
        self.status = status
        self.body = body
        self.bytes = len(body)
        self.content_type = content_type or ""
        self.from_link = from_link


class Visit:
    """Everything a browser's first visit did: requests, pages, cookies."""

    def __init__(self):
        self.requests = []
        self.pages = []
        self.cookies = {}

    @property
    def total_bytes(self):
        return sum(request.bytes for request in self.requests)


class _IconParser(html.parser.HTMLParser):
    """Collect `<link>` elements whose `rel` includes the `icon` token."""

    def __init__(self):
        super().__init__()
        self.icons = []

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        attr = {key.lower(): (value or "") for key, value in attrs}
        if "icon" in attr.get("rel", "").lower().split():
            self.icons.append((attr.get("href", ""), attr.get("sizes", "")))


def declared_icons(html_text):
    """Return [(href, sizes)] for every `<link rel="icon">` in one page."""
    parser = _IconParser()
    parser.feed(html_text)
    parser.close()
    return parser.icons


def measure_icon(data):
    """Return (width, height, format) from the icon's own header bytes.

    No Pillow: every icon format states its size in the first bytes. PNG keeps
    width/height big-endian in the IHDR chunk at offset 16. An ICO keeps a 16-byte
    directory entry at offset 6 whose first two bytes are width and height, with 0
    standing for 256. GIF keeps them little-endian at offset 6.
    """
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return width, height, "png"
    if data[:3] == b"GIF" and len(data) >= 10:
        width, height = struct.unpack("<HH", data[6:10])
        return width, height, "gif"
    if len(data) >= 22:
        reserved, kind, count = struct.unpack("<HHH", data[:6])
        if reserved == 0 and kind == 1 and count >= 1:
            width = data[6] or 256
            height = data[7] or 256
            return width, height, "ico"
    return None, None, "unknown"


def _get(base_url, path):
    """Return (status, body_bytes, content_type, headers). 4xx/5xx body is read, not raised."""
    url = base_url.rstrip("/") + (path or "/")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return (response.status, response.read(),
                    response.headers.get("Content-Type", ""), response.headers)
    except OSError as error:  # HTTPError and URLError both subclass OSError
        body = error.read() if hasattr(error, "read") else b""
        headers = getattr(error, "headers", None)
        content_type = headers.get("Content-Type", "") if headers else ""
        return getattr(error, "code", 0), body, content_type, headers


def _as_path(href):
    """The path part of a declared href, so an absolute SITE_URL can be fetched locally."""
    return urllib.parse.urlparse(href).path or "/"


def _collect_cookies(cookies, headers):
    """Record each `Set-Cookie`'s name=value in `cookies`; headers may be None on a transport error."""
    if headers is None:
        return
    for value in headers.get_all("Set-Cookie") or []:
        name, sep, rest = value.split(";", 1)[0].partition("=")
        if sep:
            cookies[name.strip()] = rest.strip()


def visit(base_url, paths=("/",), follow_assets=True):
    """Visit `paths` like a browser's first load and record every request it makes.

    Each page is fetched and recorded. Its declared icons are fetched once each
    (`from_link=True`). A page with no declared icon still triggers the browser's
    implicit guess at `/favicon.ico` (`from_link=False`): that unlinked request is
    what exercise 4 measures. `follow_assets=False` records the page requests only.
    """
    result = Visit()
    declared, seen_href, no_icon_pages = [], set(), []
    for path in paths:
        status, body, content_type, headers = _get(base_url, path)
        result.requests.append(Request(path, status, body, content_type, from_link=False))
        result.pages.append(path)
        _collect_cookies(result.cookies, headers)
        icons = declared_icons(body.decode("utf-8", "replace"))
        if not icons:
            no_icon_pages.append(path)
        for href, _sizes in icons:
            if href and href not in seen_href:
                seen_href.add(href)
                declared.append(href)
    if follow_assets:
        for href in declared:
            icon_path = _as_path(href)
            status, body, content_type, headers = _get(base_url, icon_path)
            result.requests.append(
                Request(icon_path, status, body, content_type, from_link=True))
            _collect_cookies(result.cookies, headers)
        for _path in no_icon_pages:
            status, body, content_type, headers = _get(base_url, "/favicon.ico")
            result.requests.append(
                Request("/favicon.ico", status, body, content_type, from_link=False))
            _collect_cookies(result.cookies, headers)
    return result


def _main():
    parser = argparse.ArgumentParser(
        description="Show every request a browser makes on a first visit.")
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:8000/")
    parser.add_argument("paths", nargs="*", help="extra page paths to visit")
    parser.add_argument("--no-assets", action="store_true",
                        help="visit the pages only, do not fetch icons")
    args = parser.parse_args()
    parsed = urllib.parse.urlparse(args.url)
    base = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else args.url
    paths = (parsed.path or "/",) + tuple(args.paths)
    result = visit(base, paths, follow_assets=not args.no_assets)
    print(f"visited {len(result.pages)} page(s) on {base}")
    for request in result.requests:
        if request.from_link:
            origin = "linked"
        elif request.path in result.pages:
            origin = "page"
        else:
            origin = "guessed"
        content_type = request.content_type or "(none)"
        print(f"  {request.status:>3}  {request.path:<24} {request.bytes:>7} B  "
              f"{content_type:<24} {origin}")
    for request in result.requests:
        if request.content_type.startswith("image/") or request.path == "/favicon.ico":
            width, height, fmt = measure_icon(request.body)
            print(f"  icon: {request.path} -> {width}x{height} {fmt}")
    print(f"  cookies: {result.cookies or 'none'}")
    print(f"  total: {result.total_bytes} bytes in {len(result.requests)} request(s)")


if __name__ == "__main__":
    _main()
