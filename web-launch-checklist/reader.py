"""
reader.py — the provided observer. Plays the role of a screen reader.

A screen reader does not show a page; it linearises it into the text a blind
user hears. Where an image has an `alt` attribute it reads that text; where the
attribute is missing it falls back to the file name, so the user hears
"chart dot p n g" where the author meant a picture. This observer fetches a
running site and reports the linear text, every image it found, and the two
mistakes that make an image unusable to a screen-reader user. It is the
measuring instrument for exercise 8 (alt text); read it, do not edit it. It is
symlinked into `solutions/` so the mutation harness can carry it.

DESIGN DECISION - `alt=""` is silence, a missing `alt` is a file name.
    The two look similar in source and behave differently. An empty `alt` is the
    author saying "this image is decoration, skip it"; a missing `alt` leaves the
    screen reader no text to read, so it announces the `src` file name instead.
    The observer records `has_alt` separately from `alt` so the checker can tell
    them apart, and it keeps a decoration out of the linear text while a missing
    alt still puts the file name in.

DESIGN DECISION - a file name in `alt` is a warning, not a pass.
    `alt="chart.png"` is not text a person would say; it is the fallback output
    of a tool that could not describe the image. The observer flags any alt that
    looks like an image file name (`\\w` plus dots, a known image extension), so
    the fix is a real description, not a renamed file.

DESIGN DECISION - an image that is the only content of a link is its name.
    A link is announced by the text inside it. Put an image there and the alt
    becomes the link's accessible name: `<a href="/"><img alt="Home"></a>` is
    "Home, link", while the same image with `alt=""` is an unnamed link a
    screen reader can only announce as "link". The parser therefore tracks the
    anchor it is inside and marks an image `in_link` only when it was the sole
    content of the enclosing `<a>`.

Standard library only (`urllib.request`, `urllib.parse`, `html.parser`, `re`,
`argparse`). No network beyond the server it is given.
"""

import argparse
import html.parser
import re
import urllib.parse
import urllib.request

USER_AGENT = "web-launch-checklist-reader/1.0"

# An `alt` that is really a file name: an optional path plus an image extension.
FILENAME_ALT = re.compile(
    r"^/?(?:[\w.-]+/)*[\w.-]+\.(png|jpe?g|gif|webp|svg|ico)$", re.IGNORECASE)


class Image:
    """One `<img>` on a page: what it points at, and how it is described."""

    def __init__(self, src, alt, has_alt, in_link):
        self.src = src
        self.alt = alt
        self.has_alt = has_alt
        self.in_link = in_link

    def __repr__(self):
        return f"Image({self.src!r}, alt={self.alt!r}, has_alt={self.has_alt}, in_link={self.in_link})"


class Reading:
    """What a screen reader would say for one page."""

    def __init__(self, text, images, warnings):
        self.text = text
        self.images = images
        self.warnings = warnings


def _file_name(src):
    """The file name a screen reader falls back to when `alt` is missing."""
    path = urllib.parse.urlparse(src).path
    return path.rsplit("/", 1)[-1] or src


def _heard(image):
    """The words one image contributes to the linear text ('' when decorative)."""
    if image.has_alt:
        return image.alt or ""
    return _file_name(image.src)


class _ReaderParser(html.parser.HTMLParser):
    """Build the linear text, collect images, and track anchor context."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []
        self.parts = []
        self._anchors = []  # one frame per open <a>: {"images": [...], "other": bool}
        self._skip = 0  # inside <script>/<style>: neither text nor images count

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
            return
        if self._skip:
            return
        if tag == "img":
            attr = {key.lower(): (value or "") for key, value in attrs}
            has_alt = "alt" in attr
            image = Image(attr.get("src", ""), attr.get("alt") if has_alt else None,
                          has_alt, False)
            self.images.append(image)
            if self._anchors:
                self._anchors[-1]["images"].append(image)
            heard = _heard(image)
            if heard:
                self.parts.append(heard)
            return
        if tag == "a":
            self._anchors.append({"images": [], "other": False})
            return
        # A wrapper element (<span>, <picture>, ...) is allowed around a lone image;
        # only real text makes the image something other than the link's content.

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag == "a" and self._anchors:
            frame = self._anchors.pop()
            if len(frame["images"]) == 1 and not frame["other"]:
                frame["images"][0].in_link = True

    def handle_data(self, data):
        if self._skip:
            return
        text = data.strip()
        if not text:
            return
        if self._anchors:
            self._anchors[-1]["other"] = True
        self.parts.append(text)


def _warnings(images):
    """The two ways an image fails a screen-reader user."""
    found = []
    for image in images:
        if not image.has_alt:
            found.append(f"{image.src} has no alt; a screen reader announces the file name")
        elif FILENAME_ALT.match((image.alt or "").strip()):
            found.append(f"{image.src} alt is a file name: '{image.alt}'")
    return found


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


def read_page(base_url, path="/"):
    """Fetch `path` and return the `Reading` a screen reader would produce."""
    _status, body, _content_type = _get(base_url, path)
    parser = _ReaderParser()
    parser.feed(body.decode("utf-8", "replace"))
    parser.close()
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    return Reading(text, parser.images, _warnings(parser.images))


def _main():
    parser = argparse.ArgumentParser(
        description="Read a page the way a screen reader linearises it.")
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:8000/")
    parser.add_argument("paths", nargs="*", help="extra page paths to read")
    args = parser.parse_args()
    parsed = urllib.parse.urlparse(args.url)
    base = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else args.url
    paths = (parsed.path or "/",) + tuple(args.paths)
    for path in paths:
        reading = read_page(base, path)
        print(f"page {path} — linearised text:")
        print(f"  {reading.text}")
        print("  images:")
        if not reading.images:
            print("    (none)")
        for image in reading.images:
            alt = repr(image.alt) if image.has_alt else "(missing)"
            role = " image-only link" if image.in_link else ""
            print(f"    {image.src} alt={alt}{role}")
        if reading.warnings:
            for warning in reading.warnings:
                print(f"  warning: {warning}")
        else:
            print("  warnings: none")


if __name__ == "__main__":
    _main()
