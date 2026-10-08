"""Graded hints for the learner templates (exercises 1-10).

`make_templates.py` reads each `solutions/<file>` and replaces the listed
functions with a `# TODO` and `raise NotImplementedError`. The rest of the file
(imports, `_doc`, `NAV`, the handler's `_respond`) is copied unchanged.
"""

HINTS = {
    "serve.py": {
        "SiteHandler.do_GET": (
            "route the request path: GET /contact serves contact_page() as HTML "
            "(the form, empty); GET /boom deliberately raises "
            "RuntimeError(\"boom: simulated backend failure\"); a path in pages() gets "
            "status 200 and its HTML; "
            "GET /og-image.png serves og_image_png() as image/png; "
            "GET /favicon.ico serves favicon_png() as image/png; "
            "GET /logo.png and /chart.png serve a real image/png (reuse favicon_png and "
            "og_image_png - no new image code); "
            "GET /robots.txt serves robots_txt(base) as text/plain; GET /sitemap.xml "
            "serves sitemap_xml over the page paths as application/xml (base = Host header); "
            "GET /order serves order_page(uuid.uuid4().hex) (a fresh key per form view); "
            "GET /orders serves {\"count\": len(ORDERS)} as application/json; "
            "anything else gets the 404 page with status 404 (no redirect to /). "
            "Wrap the whole body in try/except and call self._server_error() on any "
            "exception, so a raised route leaves through the one error path"
        ),
        "SiteHandler.do_POST": (
            "handle POST /contact and POST /order. POST /contact: read the urlencoded "
            "body, keep the name/email/message values, validate them (name non-empty; "
            "email with exactly one @ and a dot after it; message at least MIN_MESSAGE "
            "characters). On failure answer 200 with contact_page(values, errors) where "
            "errors maps each bad field to error_message(field, value) - field-level "
            "messages, not a bare error page. On success answer 200 with a short "
            "confirmation page. POST /order: read the urlencoded body, take "
            "`idempotency_key`; if the key was seen already answer 200 with the same "
            "confirmation and record nothing; otherwise record (product, key) and "
            "answer 200. Keep ORDERS and SEEN under ORDERS_LOCK, and a missing/empty "
            "key means no idempotency promise (record every click). Any other POST "
            "path is a 404. Wrap the whole body in try/except and call "
            "self._server_error() on any exception"
        ),
        "SiteHandler._server_error": (
            "the one error path: append the full traceback text "
            "(traceback.format_exc()) to the module-level SERVER_LOG list, then "
            "respond 500 with pages.server_error(). Nothing from the detail may "
            "reach the response body"
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
        "contact_page": (
            "return the /contact form as HTML: method=\"post\" action=\"/contact\" with a "
            "name, an email and a message field and a submit button; prefill every input "
            "from `values` and, for each field named in `errors`, render that field's "
            "message right after its input, e.g. "
            "<p class=\"error\" id=\"error-email\">...</p>. Keep it out of _doc/NAV; "
            "re-render the same page for an invalid submission"
        ),
        "error_message": (
            "return a specific, actionable sentence for one invalid field: say what is "
            "wrong and how to fix it, and make it different for each field (the email "
            "message mentions an address and the @; the message one names the minimum "
            "MIN_MESSAGE length). One generic string for every field is the framework "
            "default this exercise replaces"
        ),
        "server_error": (
            "return the generic 500 page: something went wrong, it has been logged, try "
            "again later, plus a way to reach the team. It must contain no traceback, "
            "exception text, source file path, Python version, environment variable or "
            "the request path - all of that belongs in the server log"
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
