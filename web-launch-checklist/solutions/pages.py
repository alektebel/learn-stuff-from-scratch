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
"""

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
