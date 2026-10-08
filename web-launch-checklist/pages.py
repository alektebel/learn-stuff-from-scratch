"""
The site's pages, as HTML.

DESIGN DECISION - why a Python module instead of a `site/` directory of `.html`
files. The plan in the module README says "build a `site/` directory served by
`serve.py`". The mutation harness (`_build/mutations.py` through
`.claude/skills/graded-module/scripts/mutate.py`) builds its sandbox by copying
`check.py` plus every `solutions/*.py` into a temporary directory; a directory of
HTML never travels with it, so planted bugs in the pages would be unreachable and
the checks would grade a stale copy. Keeping the page HTML in one importable
module makes the copy complete and the bugs testable. The alternative - a static
directory plus a manual before/after for every page mutation - hides two of the
three exercises from the mutation test. The cost: the learner edits Python string
literals instead of `.html` files. The HTML inside them is still real HTML, and
the observer still crawls it over HTTP.

DESIGN DECISION - one `_doc` helper, `NAV` shared. Every page carries the same
navigation, so the crawler can discover the whole site from the home page alone.
If a page were only reachable from `sitemap.xml` the link graph would miss it; the
sitemap is a later exercise and must not be what makes a page findable.

DESIGN DECISION - robots.txt allows everything and names no secret. A `Disallow`
line is public: well-behaved bots obey it, everyone else reads it as an index of
what you would rather they not see. `/admin` is "protected" by an access check on
the path, never by asking crawlers to look away. The only URL we publish is the
sitemap, which is meant to be read.

DESIGN DECISION - `lastmod` is a fixed constant, not "now". A build whose sitemap
changes on every request tells the bot the site changed when nothing did, and the
checker could not be deterministic. When the pages actually change, the constant
is bumped.

DESIGN DECISION - Open Graph URLs are absolute, and the image is generated, not
stored. `og:image` and `og:url` are absolute against the canonical `SITE_URL`
origin because a chat app rendering the card has no page to resolve a relative
path against; a relative value fails the observer. The image itself is built at
import time by `og_image_png` from `zlib` + `struct` instead of shipping a binary
asset: the mutation harness copies only `.py` files, so a checkout image would not
travel with the sandbox, and the recommended 1200x630 size is stated by a constant
the checker can grade. The cost: a flat single-colour card, which is enough to
prove the tag, the route and the dimensions.

DESIGN DECISION - the favicon is linked at the size it is served, and built, not
stored. Every page carries `<link rel="icon" type="image/png" sizes="32x32"
href="/favicon.ico">`; the `sizes` attribute is a promise the browser can check,
and a page that declares 16x16 while the server returns 32x32 is caught. The
icon itself is a real 32x32 PNG built by `favicon_png` from `zlib` + `struct` for
the same reason as the Open Graph image: a `.py`-only sandbox still carries it,
and the checker measures the bytes against the declared size. `/favicon.ico` is
also the URL a browser guesses when a page declares no icon, so the linked request
and the implicit one hit the same route.
"""

import html
import struct
import xml.sax.saxutils
import zlib

# The canonical production origin. `og:image` and `og:url` must be absolute, so
# every Open Graph URL is built from this and a path.
SITE_URL = "https://example.com"

# The size a link-preview card wants (the 1.91:1 ratio chat apps crop to).
OG_IMAGE_WIDTH = 1200
OG_IMAGE_HEIGHT = 630

NAV = (
    '<nav><a href="/">Home</a> · <a href="/about">About</a> · '
    '<a href="/pricing">Pricing</a> · <a href="/contact">Contact</a> · '
    '<a href="/docs">Docs</a></nav>'
)


def _png_bytes(width, height, color):
    """Return a real RGB PNG of `width` x `height` filled with `color`, by hand.

    `zlib` and `struct` are in the standard library, so the image is deterministic
    and a few kilobytes, not the megabytes a raw screenshot would be. Filter-0
    scanlines keep the encoder three lines long. Shared by the Open Graph card and
    the favicon, which differ only in size and colour.
    """
    r, g, b = color
    row = b"\x00" + bytes((r, g, b)) * width
    raw = row * height

    def chunk(tag, payload):
        checksum = zlib.crc32(tag + payload) & 0xFFFFFFFF
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", checksum))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def og_image_png(width=OG_IMAGE_WIDTH, height=OG_IMAGE_HEIGHT, color=(15, 42, 74)):
    """Return a real RGB PNG of the recommended card size, built by hand.

    Provided helper, not graded: the exercise is the tag, the route and the size,
    not PNG encoding. See `_png_bytes`.
    """
    return _png_bytes(width, height, color)


def favicon_png(width=32, height=32, color=(220, 60, 60)):
    """Return a real RGB PNG favicon, built by hand.

    Provided helper, not graded: the exercise is the tag, the route and the
    declared size. The default is the 32x32 a browser's high-density tab wants;
    `visit.py` reads the true size out of the IHDR bytes rather than trusting the
    `<link>`.
    """
    return _png_bytes(width, height, color)


def icon_link():
    """Return the page's `<link rel="icon">` tag.

    `href="/favicon.ico"` names the same URL a browser guesses when no link is
    present, so the declared request and the implicit one are one route.
    `sizes="32x32"` must state the icon's real size: a wrong value makes the
    browser skip the icon or fetch a second one.
    """
    # TODO: return the <link rel="icon"> tag: type="image/png", href="/favicon.ico", and sizes="32x32" matching the icon the server really returns
    raise NotImplementedError("icon_link")


def og_tags(title, description, path):
    """Return the Open Graph and Twitter meta tags for one page.

    `og:image` and `og:url` are absolute (built from `SITE_URL`): a chat app
    rendering the card later has no page to resolve a relative URL against, so a
    relative value fails the observer. `og:title` and `og:description` are
    HTML-escaped so a quote in a title cannot break out of the `content`
    attribute. `og:image:width`/`height` repeat the generated image's size so a
    card can reserve space before the bytes arrive.
    """
    # TODO: return the Open Graph and Twitter meta tags for one page: og:type, og:title, og:description, og:url (SITE_URL + path), og:image (an ABSOLUTE SITE_URL + "/og-image.png"), og:image:width, og:image:height and twitter:card=summary_large_image; HTML-escape title and description
    raise NotImplementedError("og_tags")


def _doc(title, description, main, path="/"):
    """Return a complete HTML document. `description` empty means: omit the tag."""
    head = ""
    if description:
        head = f'<meta name="description" content="{description}">\n'
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{title}</title>\n"
        f"{icon_link()}\n"
        f"{head}"
        f"{og_tags(title, description, path)}"
        "</head>\n"
        "<body>\n"
        f"{NAV}\n"
        f"{main}\n"
        f"{NAV}\n"
        "</body>\n"
        "</html>\n"
    )


def pages():
    """Return {path: html} for every public page the site serves."""
    # TODO: return {path: html} for every public page; each page needs a <title> and a <meta name="description">, and the home page must link to all of them
    raise NotImplementedError("pages")


def not_found():
    """Return the page shown for an unknown path. It must help and link home."""
    # TODO: return the 404 page as HTML; it must link back to the home page, not redirect to it
    raise NotImplementedError("not_found")


# Fixed date for every <lastmod>; bump it when the pages change. See the
# "fixed constant, not now" design decision in the module docstring.
LASTMOD = "2026-01-01"


def robots_txt(base_url):
    """Return the /robots.txt body: allow the public site, name no secret path.

    `User-agent: *` plus `Allow: /` says "crawl everything", and the trailing
    `Sitemap:` line points the bot at /sitemap.xml. There is deliberately no
    `Disallow:` for `/admin` or `/tmp`: naming a path in a public file is how
    you advertise it, not how you protect it. Access control belongs on the path
    itself. The body stays parseable by `crawler.parse_robots`.
    """
    # TODO: return the /robots.txt body: `User-agent: *` and `Allow: /` (never list a secret path - the file is public), ending with a Sitemap: line for /sitemap.xml
    raise NotImplementedError("robots_txt")


def sitemap_xml(page_paths, base_url):
    """Return a valid XML sitemap listing every path in `page_paths`.

    Each path becomes `<url><loc><base_url><path></loc><lastmod>...</lastmod></url>`,
    including pages the navigation never links to. `page_paths` may arrive in any
    order; the output is sorted so it is deterministic. `lastmod` is the fixed
    `LASTMOD`; URLs are XML-escaped (`&`, `<`, `>` must not appear raw).
    """
    # TODO: return XML listing every path in page_paths as <url><loc>base+path</loc><lastmod>...</lastmod></url> with a fixed date, including pages nothing links to
    raise NotImplementedError("sitemap_xml")
