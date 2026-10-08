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
    return '<link rel="icon" type="image/png" sizes="32x32" href="/favicon.ico">'


def og_tags(title, description, path):
    """Return the Open Graph and Twitter meta tags for one page.

    `og:image` and `og:url` are absolute (built from `SITE_URL`): a chat app
    rendering the card later has no page to resolve a relative URL against, so a
    relative value fails the observer. `og:title` and `og:description` are
    HTML-escaped so a quote in a title cannot break out of the `content`
    attribute. `og:image:width`/`height` repeat the generated image's size so a
    card can reserve space before the bytes arrive.
    """
    image = SITE_URL + "/og-image.png"
    url = SITE_URL + path
    return (
        f'<meta property="og:type" content="website">\n'
        f'<meta property="og:title" content="{html.escape(title, quote=True)}">\n'
        f'<meta property="og:description" content="{html.escape(description, quote=True)}">\n'
        f'<meta property="og:url" content="{url}">\n'
        f'<meta property="og:image" content="{image}">\n'
        f'<meta property="og:image:width" content="{OG_IMAGE_WIDTH}">\n'
        f'<meta property="og:image:height" content="{OG_IMAGE_HEIGHT}">\n'
        f'<meta name="twitter:card" content="summary_large_image">\n'
    )


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
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        "<title>Place an order — Acme Tools</title>\n"
        "</head>\n"
        "<body>\n"
        f"{NAV}\n"
        "<h1>Order a widget</h1>\n"
        '<form method="post" action="/order" onsubmit="this.querySelector(\'button\').disabled = true">\n'
        f'<input type="hidden" name="idempotency_key" value="{key}">\n'
        '<input type="hidden" name="product" value="widget">\n'
        '<button type="submit">Place order</button>\n'
        "</form>\n"
        '<p role="status">Placing your order…</p>\n'
        f"{NAV}\n"
        "</body>\n"
        "</html>\n"
    )


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


def error_message(field, value):
    """Return a specific, actionable sentence for one invalid field.

    The message says *what* is wrong and *how* to fix it, and it is different
    for each field: one generic sentence ("invalid input") for every field is
    the framework default this exercise replaces, and it leaves the user with
    nothing to change. `value` is the submitted value, kept out of the message
    so the text can be rendered without echoing the user's input back at them.
    """
    if field == "name":
        return "Enter your name so we know who to reply to."
    if field == "email":
        return ("That is not an email address: use one @ with a domain after it, "
                "like you@example.com.")
    if field == "message":
        return (f"Your message is too short: write at least {MIN_MESSAGE} "
                "characters so we can help.")
    return f'Check the "{field}" field and try again.'


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
    values = values or {}
    errors = errors or {}

    def field_input(name, label, kind="text"):
        value = html.escape(str(values.get(name, "")), quote=True)
        rendered = (f'<label for="{name}">{label}</label>\n'
                    f'<input type="{kind}" id="{name}" name="{name}" value="{value}">\n')
        if name in errors:
            message = html.escape(str(errors[name]), quote=True)
            rendered += f'<p class="error" id="error-{name}">{message}</p>\n'
        return rendered

    message_value = html.escape(str(values.get("message", "")), quote=True)
    message_block = ('<label for="message">Message</label>\n'
                     '<textarea id="message" name="message" rows="5">'
                     f'{message_value}</textarea>\n')
    if "message" in errors:
        message = html.escape(str(errors["message"]), quote=True)
        message_block += f'<p class="error" id="error-message">{message}</p>\n'

    main = (
        "<h1>Contact</h1>\n"
        '<form method="post" action="/contact">\n'
        f'{field_input("name", "Name")}'
        f'{field_input("email", "Email", kind="email")}'
        f'{message_block}'
        '<button type="submit">Send message</button>\n'
        "</form>\n"
    )
    return _doc(
        "Contact Acme Tools",
        "Send the Acme Tools team a message: report a broken page or ask for a launch review.",
        main,
        path="/contact",
    )


def server_error():
    """Return the generic 500 page: a next step, never the detail.

    The traceback, the exception text, the request path, the source file paths,
    the Python version and any environment variable belong in the server log,
    not in this body. A user cannot act on a stack trace, and an attacker reads
    versions, paths and secrets out of one. So this page only says that
    something failed, that it was logged, and what the user can do next.
    """
    return _doc(
        "Something went wrong — Acme Tools",
        "We could not complete that request. The problem has been logged.",
        "<h1>Something went wrong</h1>\n"
        "<p>We hit a problem on our side and have logged it. Please try again in "
        "a moment; if it keeps happening, <a href=\"/contact\">tell us</a>.</p>\n",
        path="/",
    )


def pages():
    """Return {path: html} for every public page the site serves."""
    return {
        "/": _doc(
            "Acme Tools — ship a small site",
            "Acme Tools helps makers ship small websites and check them before launch.",
            "<h1>Acme Tools</h1>"
            "<p>Everything you need to launch a small, honest website.</p>"
            '<p><a href="/"><img src="/logo.png" alt="Home"></a></p>'
            '<img src="/chart.png" alt="Headcount by department, 2025">'
            '<img src="/chart.png" alt="">',
            path="/",
        ),
        "/about": _doc(
            "About Acme Tools",
            "Who builds Acme Tools, why the launch checklist exists, and how the observers work.",
            "<h1>About Acme Tools</h1>"
            "<p>We measure what a search bot, a chat card and a screen reader actually see.</p>",
            path="/about",
        ),
        "/pricing": _doc(
            "Pricing — Acme Tools",
            "Free while in beta. One plan, no seat limits, cancel whenever you like.",
            "<h1>Pricing</h1><p>One plan. It is free until we leave beta.</p>",
            path="/pricing",
        ),
        "/contact": contact_page(),
        "/docs": _doc(
            "Docs — Acme Tools",
            "Install Acme Tools, run the observers, and read every check the crawler makes.",
            "<h1>Docs</h1><p>Run <code>python3 check.py</code> after every step.</p>",
            path="/docs",
        ),
    }


def not_found():
    """Return the page shown for an unknown path. It must help and link home."""
    return _doc(
        "Page not found — Acme Tools",
        "That page is not here. The links below lead back into the site.",
        "<h1>404 — page not found</h1>"
        "<p>We could not find that page. Try the <a href=\"/\">home page</a>, "
        "the <a href=\"/docs\">docs</a>, or <a href=\"/contact\">tell us</a> what you "
        "were looking for.</p>",
    )


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
    base = base_url.rstrip("/")
    return (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )


def sitemap_xml(page_paths, base_url):
    """Return a valid XML sitemap listing every path in `page_paths`.

    Each path becomes `<url><loc><base_url><path></loc><lastmod>...</lastmod></url>`,
    including pages the navigation never links to. `page_paths` may arrive in any
    order; the output is sorted so it is deterministic. `lastmod` is the fixed
    `LASTMOD`; URLs are XML-escaped (`&`, `<`, `>` must not appear raw).
    """
    base = base_url.rstrip("/")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in sorted(page_paths):
        loc = xml.sax.saxutils.escape(base + path)
        lines.append(f"  <url><loc>{loc}</loc><lastmod>{LASTMOD}</lastmod></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"
