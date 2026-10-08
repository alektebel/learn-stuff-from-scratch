"""Graded hints for the learner templates (exercises 1-5).

`make_templates.py` reads each `solutions/<file>` and replaces the listed
functions with a `# TODO` and `raise NotImplementedError`. The rest of the file
(imports, `_doc`, `NAV`, the handler and its `_respond`) is copied unchanged.
"""

HINTS = {
    "serve.py": {
        "SiteHandler.do_GET": (
            "route the request path: a path in pages() gets status 200 and its HTML; "
            "GET /robots.txt serves robots_txt(base) as text/plain; GET /sitemap.xml "
            "serves sitemap_xml over the page paths as application/xml (base = Host header); "
            "anything else gets the 404 page with status 404 (no redirect to /)"
        ),
        "make_server": (
            "return an http.server that routes the paths in pages() to status 200, "
            "and every other path to the 404 page with status 404"
        ),
    },
    "pages.py": {
        "pages": (
            "return {path: html} for every public page; each page needs a <title> "
            "and a <meta name=\"description\">, and the home page must link to all of them"
        ),
        "not_found": (
            "return the 404 page as HTML; it must link back to the home page, not redirect to it"
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
