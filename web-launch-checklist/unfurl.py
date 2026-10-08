"""
unfurl.py — the provided observer. Plays the role of a chat app building a preview.

Paste a link into a chat app and it fetches the page, reads its Open Graph tags
and renders a card: title, description, image. This observer does the same against
a running site and reports what the card would show, plus the size and type of the
picture it would display. It is the measuring instrument for exercise 7 (Open
Graph); read it, do not edit it. It is symlinked into `solutions/` so the mutation
harness can carry it.

DESIGN DECISION - a relative `og:image` is a problem, not something to resolve.
    The Open Graph protocol requires `og:image` and `og:url` to be absolute URLs.
    A chat app has no page context when it later renders the card and no base to
    resolve a relative path against, so a relative value is recorded in
    `Card.problems` rather than silently joined to the page URL. That is the limit
    case exercise 7 grades.

DESIGN DECISION - the image is fetched from the origin under test, not from its
    declared origin. The pages carry `og:image = SITE_URL + "/og-image.png"`, and
    `SITE_URL` is the canonical production origin ("https://example.com"), which
    cannot be reached without a network here. A real chat app would fetch that
    absolute URL; the observer instead fetches the declared URL's *path*
    ("/og-image.png") from the server it was pointed at. That is the same stand-in
    exercise 16's byte measurements need: the observer grades the bytes the site
    serves now, not the ones a DNS record points at later. The absolute-URL rule
    above is still checked on the declared value, so a relative value is caught.

Standard library only (`urllib.request`, `urllib.parse`, `html.parser`, `struct`,
`argparse`). No network beyond the server it is given.
"""

import argparse
import html.parser
import struct
import urllib.parse
import urllib.request

USER_AGENT = "web-launch-checklist-unfurl/1.0"


class Card:
    """Everything a chat app would show for one pasted link."""

    def __init__(self):
        self.title = None
        self.description = None
        self.image = None
        self.url = None
        self.site_name = None
        self.og_type = None
        self.twitter_card = None
        self.image_bytes = 0
        self.image_width = None
        self.image_height = None
        self.image_content_type = ""
        self.problems = []


class _CardParser(html.parser.HTMLParser):
    """Collect `<meta>` tags whose key is an `og:` or `twitter:` property."""

    def __init__(self):
        super().__init__()
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        attr = {key.lower(): (value or "") for key, value in attrs}
        content = attr.get("content")
        for key in (attr.get("property", "").lower(), attr.get("name", "").lower()):
            if key.startswith(("og:", "twitter:")):
                self.meta.setdefault(key, content)


def _absolute(value):
    """True when `value` is an absolute http(s) URL."""
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def parse_card(html_text, page_url):
    """Turn one page's HTML into a `Card`, recording problems it cannot fix."""
    parser = _CardParser()
    parser.feed(html_text)
    parser.close()
    meta = parser.meta
    card = Card()
    card.title = meta.get("og:title")
    card.description = meta.get("og:description")
    card.image = meta.get("og:image")
    card.url = meta.get("og:url") or page_url
    card.site_name = meta.get("og:site_name")
    card.og_type = meta.get("og:type")
    card.twitter_card = meta.get("twitter:card")
    for key in ("og:image", "og:url"):
        value = meta.get(key)
        if value and not _absolute(value):
            card.problems.append(f"{key} is not an absolute URL: {value!r}")
    return card


def measure_image(data):
    """Return (width, height, format) from the file's header bytes.

    No Pillow: a card only needs to know how big the picture is, and every web
    image format states that in its first bytes. PNG stores width/height in the
    IHDR chunk, GIF in its header, JPEG in the first Start-Of-Frame marker.
    """
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return width, height, "png"
    if data[:3] == b"GIF" and len(data) >= 10:
        width, height = struct.unpack("<HH", data[6:10])
        return width, height, "gif"
    if data[:2] == b"\xff\xd8":
        width, height = _jpeg_size(data)
        if width and height:
            return width, height, "jpeg"
    return None, None, "unknown"


def _jpeg_size(data):
    """Walk JPEG markers to the first Start-Of-Frame and read its dimensions."""
    i, end = 2, len(data)
    while i + 9 <= end:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if marker == 0xD9:
            break
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        is_sof = 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC)
        if is_sof:
            height = struct.unpack(">H", data[i + 5:i + 7])[0]
            width = struct.unpack(">H", data[i + 7:i + 9])[0]
            return width, height
        i += 2 + length
    return None, None


def _get(base_url, path):
    """Return (status, body_bytes, content_type). A 4xx/5xx body is read, not raised."""
    url = base_url.rstrip("/") + (path or "/")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return (response.status, response.read(),
                    response.headers.get("Content-Type", ""))
    except OSError as error:  # HTTPError and URLError both subclass OSError
        body = error.read() if hasattr(error, "read") else b""
        headers = getattr(error, "headers", None)
        content_type = headers.get("Content-Type", "") if headers else ""
        return getattr(error, "code", 0), body, content_type


def unfurl(base_url, path="/"):
    """Fetch a page, read its card tags, then fetch and measure the image."""
    status, body, _ = _get(base_url, path)
    page_url = base_url.rstrip("/") + (path or "/")
    card = parse_card(body.decode("utf-8", "replace"), page_url)
    if status != 200:
        card.problems.append(f"the page returned status {status}")
    if not card.image:
        card.problems.append("no og:image tag: the card would have no picture")
    elif _absolute(card.image):
        image_path = urllib.parse.urlparse(card.image).path or "/"
        image_status, image_body, content_type = _get(base_url, image_path)
        card.image_content_type = content_type
        if image_status != 200 or not image_body:
            card.problems.append(
                f"og:image {card.image!r} is unreachable "
                f"(status {image_status}, {len(image_body)} bytes)")
        else:
            card.image_bytes = len(image_body)
            card.image_width, card.image_height, _format = measure_image(image_body)
            if not content_type.startswith("image/"):
                card.problems.append(
                    f"og:image is served as {content_type!r}, not an image type")
    return card


def _main():
    parser = argparse.ArgumentParser(description="Show the card a chat app would build.")
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:8000/")
    args = parser.parse_args()
    parsed = urllib.parse.urlparse(args.url)
    base = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else args.url
    card = unfurl(base, parsed.path or "/")
    size = f"{card.image_width}x{card.image_height}" if card.image_width else "unmeasured"
    print(f"title:       {card.title}")
    print(f"description: {card.description}")
    print(f"url:         {card.url}")
    print(f"type:        {card.og_type}")
    print(f"twitter:     {card.twitter_card}")
    print(f"image:       {card.image}")
    print(f"image size:  {size}, {card.image_bytes} bytes, {card.image_content_type}")
    if card.problems:
        for problem in card.problems:
            print(f"problem:     {problem}")
    else:
        print("problems:    none")


if __name__ == "__main__":
    _main()
