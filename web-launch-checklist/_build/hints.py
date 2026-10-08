"""Graded hints for the learner templates (exercises 1-9).

`make_templates.py` reads each `solutions/<file>` and replaces the listed
functions with a `# TODO` and `raise NotImplementedError`. The rest of the file
(imports, `_doc`, `NAV`, the handler and its `_respond`) is copied unchanged.
"""

HINTS = {
    "serve.py": {
        "SiteHandler.do_GET": (
            "route the request path: a path in pages() gets status 200 and its HTML; "
            "GET /og-image.png serves og_image_png() as image/png; "
            "GET /favicon.ico serves favicon_png() as image/png; "
            "GET /logo.png and /chart.png serve a real image/png (reuse favicon_png and "
            "og_image_png - no new image code); "
            "GET /robots.txt serves robots_txt(base) as text/plain; GET /sitemap.xml "
            "serves sitemap_xml over the page paths as application/xml (base = Host header); "
            "GET /order serves order_page(uuid.uuid4().hex) (a fresh key per form view); "
            "GET /orders serves {\"count\": len(ORDERS)} as application/json; "
            "anything else gets the 404 page with status 404 (no redirect to /)"
        ),
        "SiteHandler.do_POST": (
            "handle POST /order: read the urlencoded body, take `idempotency_key`; "
            "if the key was seen already answer 200 with the same confirmation and "
            "record nothing; otherwise record (product, key) and answer 200. Keep "
            "ORDERS and SEEN under ORDERS_LOCK, and a missing/empty key means no "
            "idempotency promise (record every click). Any other POST path is a 404"
        ),
        "make_server": (
            "return an http.server that routes the paths in pages() to status 200, "
            "and every other path to the 404 page with status 404"
        ),
    },
    "pages.py": {
        "og_tags": (
            "return the Open Graph and Twitter meta tags for one page: og:type, og:title, "
            "og:description, og:url (SITE_URL + path), og:image (an ABSOLUTE "
            "SITE_URL + \"/og-image.png\"), og:image:width, og:image:height and "
            "twitter:card=summary_large_image; HTML-escape title and description"
        ),
        "icon_link": (
            "return the <link rel=\"icon\"> tag: type=\"image/png\", href=\"/favicon.ico\", "
            "and sizes=\"32x32\" matching the icon the server really returns"
        ),
        "pages": (
            "return {path: html} for every public page; each page needs a <title> "
            "and a <meta name=\"description\">, and the home page must link to all of them; "
            "include across the site an informative image with a real description in alt, "
            "a decorative image with alt=\"\", and a link whose only content is an image "
            "whose alt describes the link's destination (its accessible name)"
        ),
        "not_found": (
            "return the 404 page as HTML; it must link back to the home page, not redirect to it"
        ),
        "order_page": (
            "return the /order form as HTML: method=\"post\" action=\"/order\", an "
            "onsubmit that disables the submit control the instant it is clicked, a "
            "hidden idempotency_key input carrying the given key, a submit button, "
            "and a visible \"Placing your order…\" status line. Build the page here, "
            "not through _doc, so it does not leak into the shared chrome"
        ),
        "robots_txt": (
            "return the /robots.txt body: `User-agent: *` and `Allow: /` (never list a "
            "secret path - the file is public), ending with a Sitemap: line for /sitemap.xml"
        ),
        "sitemap_xml": (
            "return XML listing every path in page_paths as <url><loc>base+path</loc>"
            "<lastmod>...</lastmod></url> with a fixed date, including pages nothing links to"
        ),
    },
}
