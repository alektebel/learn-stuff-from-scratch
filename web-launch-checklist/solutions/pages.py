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
"""

import xml.sax.saxutils

NAV = (
    '<nav><a href="/">Home</a> · <a href="/about">About</a> · '
    '<a href="/pricing">Pricing</a> · <a href="/contact">Contact</a> · '
    '<a href="/docs">Docs</a></nav>'
)


def _doc(title, description, main):
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
        f"{head}"
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
    return {
        "/": _doc(
            "Acme Tools — ship a small site",
            "Acme Tools helps makers ship small websites and check them before launch.",
            "<h1>Acme Tools</h1>"
            "<p>Everything you need to launch a small, honest website.</p>",
        ),
        "/about": _doc(
            "About Acme Tools",
            "Who builds Acme Tools, why the launch checklist exists, and how the observers work.",
            "<h1>About Acme Tools</h1>"
            "<p>We measure what a search bot, a chat card and a screen reader actually see.</p>",
        ),
        "/pricing": _doc(
            "Pricing — Acme Tools",
            "Free while in beta. One plan, no seat limits, cancel whenever you like.",
            "<h1>Pricing</h1><p>One plan. It is free until we leave beta.</p>",
        ),
        "/contact": _doc(
            "Contact Acme Tools",
            "Email the team, report a broken page, or ask for a launch review.",
            "<h1>Contact</h1><p>Write to <a href=\"mailto:team@example.com\">team@example.com</a>.</p>",
        ),
        "/docs": _doc(
            "Docs — Acme Tools",
            "Install Acme Tools, run the observers, and read every check the crawler makes.",
            "<h1>Docs</h1><p>Run <code>python3 check.py</code> after every step.</p>",
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
