"""Graded hints for the learner templates (exercises 1-3).

`make_templates.py` reads each `solutions/<file>` and replaces the listed
functions with a `# TODO` and `raise NotImplementedError`. The rest of the file
(imports, `_doc`, `NAV`, the handler and its `_respond`) is copied unchanged.
"""

HINTS = {
    "serve.py": {
        "SiteHandler.do_GET": (
            "route the request path: a path in pages() gets status 200 and its HTML; "
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
    },
}
