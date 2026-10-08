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

DESIGN DECISION - every image is either described or explicitly silent, and the
images live in `pages()`, not in `_doc` or `NAV`. `alt` is a promise about the
image: a real description when the picture carries meaning, `alt=""` when it is
decoration, and never a file name. Putting the images in the shared chrome would
copy the same `alt` values into every page and into the learner template, where
they would leak the answer, so the samples sit in the home page body: an
informative image, a decorative one, and an image that is the only content of a
link, whose alt is therefore the link's accessible name.

DESIGN DECISION - a form error is a 200 page next to the field, and a server
error is a generic 500. `contact_page` re-renders the form with the user's
`values` and one `error_message` per bad field, placed right after that field's
input; the status stays 200 because an invalid form is the user's mistake, not a
request the server failed to handle. `server_error` is the other half: a page a
user can act on, carrying no traceback, exception, path, version or environment
variable, because all of that is detail for the log. A framework's default (a
bare error, or the same "invalid input" for every field) is the thing these
replace.

DESIGN DECISION - consent is a POST form, and the two choices share one element
type. A `GET /consent?choice=accept` link is crawlable: the search bot would
follow it, the sitemap would have to list it, and every bot pass would "accept"
analytics for a visitor who never chose. A `method="post"` form is not a link,
so the choice stays with a person. Both controls are `<button>` elements of
equal prominence, because a consent screen that makes accepting one click and
rejecting two (or hides reject in grey text) is not a free choice. The banner
lives in `_doc`, so it appears on every page until the server records a choice;
the strictly necessary session cookie is set by `serve.py` on every response,
never the analytics one.
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

# The shortest message the contact form accepts, in characters. `error_message`
# names this same number in the message the user reads, and `serve.py` validates
# against it: one constant, so the rule and the sentence cannot drift apart.
MIN_MESSAGE = 10

# The two cookies exercise 13 is about. `SESSION_COOKIE` is strictly necessary:
# the server sets it on every response so the site can remember the visitor's
# choice, and it carries no tracking value. `ANALYTICS_COOKIE` is non-essential:
# it may be set only after the visitor accepts, and never on a plain page load.
SESSION_COOKIE = "wlc_session"
ANALYTICS_COOKIE = "wlc_analytics"

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


def order_page(key):
    """Return the `/order` form: immediate feedback, a disabling control, a key.

    The page is built whole, not through `_doc`: it is not part of the crawlable
    site (no navigation link points at it), and keeping it out of `_doc`/`NAV`
    means the learner templates do not leak its answer into the shared chrome.
    The form carries three things exercise 10 grades:

    - an `onsubmit` that disables the submit control the instant the user clicks,
      so a slow API cannot be clicked twice by accident. A standard-library
      observer cannot watch the paint; it reads this mechanism;
    - a hidden `idempotency_key` minted once per form view. A multi-click sends
      the same key, so the server can collapse the repeats into one order;
    - a visible status line ("Placing your order…") so the user sees that
      something is happening while the request is in flight.
    """
    # TODO: return the /order form as HTML: method="post" action="/order", an onsubmit that disables the submit control the instant it is clicked, a hidden idempotency_key input carrying the given key, a submit button, and a visible "Placing your order…" status line. Build the page here, not through _doc, so it does not leak into the shared chrome
    raise NotImplementedError("order_page")


def consent_banner():
    """Return the cookie-consent banner: two equally easy choices.

    The banner is a `POST` form, not two links. A link such as
    `/consent?choice=accept` is an `<a href>` and a search bot would follow and
    "accept" it for a visitor who never gave consent; a form with
    `method="post"` is not a crawlable link, so the choice can only be made by a
    person. Both controls are `<button>` elements of equal prominence: rejecting
    must be exactly as easy as accepting, so neither choice may be a plain link
    or visually hidden. The single field `choice` carries `accept` or `reject`,
    and the server records which one arrived.

    GRADED: `check.py` step 11 requires two real `<button type="submit">`
    controls of the same element type, neither disabled (nor inside a disabled
    fieldset), each with a visible label.
    """
    # TODO: return the cookie-consent banner: a <form method="post" action="/consent"> with two real submit buttons of the SAME element type and equal prominence - <button type="submit" name="choice" value="accept"> and <button type="submit" name="choice" value="reject"> - each with a visible label, neither disabled (nor inside a disabled fieldset), plus a short explanatory line. It is already called from _doc, so it appears on every page; rejecting must be as easy as accepting (no plain link, no hidden reject), and a POST form is not a crawlable link
    raise NotImplementedError("consent_banner")


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
        f"{consent_banner()}\n"
        f"{NAV}\n"
        f"{main}\n"
        f"{NAV}\n"
        "</body>\n"
        "</html>\n"
    )


def error_message(field, value):
    """Return a specific, actionable sentence for one invalid field.

    The message says *what* is wrong and *how* to fix it, and it is different
    for each field: one generic sentence ("invalid input") for every field is
    the framework default this exercise replaces, and it leaves the user with
    nothing to change. `value` is the submitted value, kept out of the message
    so the text can be rendered without echoing the user's input back at them.
    """
    # TODO: return a specific, actionable sentence for one invalid field: say what is wrong and how to fix it, and make it different for each field (the email message mentions an address and the @; the message one names the minimum MIN_MESSAGE length). One generic string for every field is the framework default this exercise replaces
    raise NotImplementedError("error_message")


def contact_page(values=None, errors=None):
    """Return the `/contact` form, re-rendered with the user's input and errors.

    `values` refills every input, so a user who got one field wrong does not
    retype the rest; `errors` maps a field name to its `error_message`, rendered
    right after that field's input (`<p class="error" id="error-email">`), so
    the complaint sits where the mistake is. The form posts to itself: the
    server validates, and an invalid submission comes back as this same page
    with the messages attached and status 200. The opposite - a bare framework
    error, or a silent red border - tells the user nothing about what to change.
    """
    # TODO: return the /contact form as HTML: method="post" action="/contact" with a name, an email and a message field and a submit button; prefill every input from `values` and, for each field named in `errors`, render that field's message right after its input, e.g. <p class="error" id="error-email">...</p>. Keep it out of _doc/NAV; re-render the same page for an invalid submission
    raise NotImplementedError("contact_page")


def server_error():
    """Return the generic 500 page: a next step, never the detail.

    The traceback, the exception text, the request path, the source file paths,
    the Python version and any environment variable belong in the server log,
    not in this body. A user cannot act on a stack trace, and an attacker reads
    versions, paths and secrets out of one. So this page only says that
    something failed, that it was logged, and what the user can do next.
    """
    # TODO: return the generic 500 page: something went wrong, it has been logged, try again later, plus a way to reach the team. It must contain no traceback, exception text, source file path, Python version, environment variable or the request path - all of that belongs in the server log
    raise NotImplementedError("server_error")


def pages():
    """Return {path: html} for every public page the site serves."""
    # TODO: return {path: html} for every public page; each page needs a <title> and a <meta name="description">, and the home page must link to all of them; include across the site an informative image with a real description in alt, a decorative image with alt="", and a link whose only content is an image whose alt describes the link's destination (its accessible name)
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
