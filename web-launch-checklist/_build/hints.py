"""Graded hints for the learner templates (exercises 1-12).

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
            "GET /messages serves {\"count\": len(MESSAGES)} as application/json; "
            "GET /messages/<id> serves the stored message as application/json, or the "
            "404 page when the id is unknown; "
            "anything else gets the 404 page with status 404 (no redirect to /). "
            "The shared `_respond` already sets the strictly-necessary SESSION_COOKIE "
            "on every response, so no route needs to set it; and no GET route may "
            "set the analytics cookie. "
            "Wrap the whole body in try/except and call self._server_error() on any "
            "exception, so a raised route leaves through the one error path"
        ),
        "SiteHandler.do_POST": (
            "handle POST /contact, POST /consent and POST /order. POST /contact: read "
            "the urlencoded "
            "body, keep the name/email/message values, validate them (name non-empty; "
            "email with exactly one @ and a dot after it; message at least MIN_MESSAGE "
            "characters). On failure answer 200 with contact_page(values, errors) where "
            "errors maps each bad field to error_message(field, value) - field-level "
            "messages, not a bare error page. On success mint a receipt id, store the "
            "message in MESSAGES under it and answer 200 with contact_sent(receipt). "
            "Two spam filters run first: discard a submission whose honeypot field "
            "(fields[CONTACT_HONEYPOT]) is non-empty (store nothing, answer 200), and "
            "refuse with status 429 when _rate_limited(the client's IP) is true. "
            "POST /consent: read `choice`; on accept pass "
            "`ANALYTICS_COOKIE=1; Path=/` to _respond, on reject set no analytics cookie "
            "(expire one only if the request already carried it), then answer 200 with "
            "the home page. POST /order: read the urlencoded body, take "
            "`idempotency_key`; if the key was seen already answer 200 with the same "
            "confirmation and record nothing; otherwise record (product, key) and "
            "answer 200. Keep ORDERS and SEEN under ORDERS_LOCK, and a missing/empty "
            "key means no idempotency promise (record every click). Any other POST "
            "path is a 404. Wrap the whole body in try/except and call "
            "self._server_error() on any exception"
        ),
        "_rate_limited": (
            "return True when this IP has posted to /contact CONTACT_RATE_LIMIT or "
            "more times within the last CONTACT_RATE_WINDOW_S seconds, and record "
            "this attempt as well (so a fast burst cannot outrun the limit); it is "
            "called at the top of POST /contact and the caller answers 429 when it "
            "is true"
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
        "consent_banner": (
            "return the cookie-consent banner: a <form method=\"post\" action=\"/consent\"> "
            "with two real submit buttons of the SAME element type and equal prominence - "
            "<button type=\"submit\" name=\"choice\" value=\"accept\"> and <button "
            "type=\"submit\" name=\"choice\" value=\"reject\"> - each with a visible "
            "label, neither disabled (nor inside a disabled fieldset), plus a short "
            "explanatory line. It is already called from _doc, so it appears on every "
            "page; rejecting must be as easy as accepting (no plain link, no hidden "
            "reject), and a POST form is not a crawlable link"
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
            "<p class=\"error\" id=\"error-email\">...</p>. Include the honeypot: a "
            "real text input named CONTACT_HONEYPOT (NOT type=hidden, so a bot will "
            "fill it) hidden from people with display:none, tabindex=\"-1\" and "
            "aria-hidden=\"true\". Keep it out of _doc/NAV; re-render the same page for "
            "an invalid submission"
        ),
        "contact_sent": (
            "return the receipt page shown after a valid submission: an HTML page that "
            "confirms receipt and carries the given receipt id as "
            "data-receipt=\"<id>\" so the user (and the check) can quote a reference. "
            "Build it here, not through _doc, so it does not leak into the shared chrome"
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
    "analytics.py": {
        "is_bot": (
            "return True when the user-agent is an explicit blank string or contains any "
            "marker from BOT_MARKERS, case-insensitively; a missing user-agent (None) is "
            "not a bot"
        ),
        "is_prefetch": (
            "return True when the Purpose, X-Purpose or X-Moz header is a prefetch or "
            "preview value"
        ),
        "is_reload": (
            "return True when Cache-Control contains no-cache or max-age=0, or Pragma "
            "contains no-cache"
        ),
        "consented": (
            "return True when the cookie header carries a non-empty ANALYTICS_COOKIE value"
        ),
        "count_views": (
            "keep only GET records whose path is not an asset, whose user-agent is not a "
            "bot, that are neither prefetch nor reload, and that carry consent; tally per "
            "path and return {\"views\": {sorted path: int}, \"total\": int} - stored paths "
            "and integers only, no user-agent, IP or cookie"
        ),
    },
}
