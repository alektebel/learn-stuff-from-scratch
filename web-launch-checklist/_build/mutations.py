"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

Each entry is (description, file, exact text in solutions/<file>, replacement,
check step). One classic mistake per exercise:

1. soft 404        - the server answers an unknown path with status 200.
2. duplicate titles - every page gets the home page's <title>.
3. missing description - the description tag is never emitted.
4. robots.txt disallows the site, or names /admin, or omits the Sitemap line.
5. sitemap.xml is missing lastmod, or lists a URL that 404s.
6. Open Graph: a relative og:image, a missing image, a card title that does not
   match the page, no /og-image.png route, the image served as HTML, or an
   image below the recommended height.
"""

MUTATIONS = [
    (
        "soft 404: unknown path served with status 200",
        "serve.py",
        "            self._respond(404, not_found())",
        "            self._respond(200, not_found())",
        "1",
    ),
    (
        "duplicate titles: every page uses the home page's <title>",
        "pages.py",
        '        f"<title>{title}</title>\\n"',
        '        "<title>Acme Tools — ship a small site</title>\\n"',
        "2",
    ),
    (
        "missing description: the meta description is never emitted",
        "pages.py",
        "    if description:\n",
        "    if False:\n",
        "3",
    ),
    (
        "robots.txt disallows the whole public site",
        "pages.py",
        '"Allow: /\\n"',
        '"Disallow: /\\n"',
        "4",
    ),
    (
        "robots.txt names a secret path (/admin) instead of protecting it",
        "pages.py",
        '        "Allow: /\\n"\n',
        '        "Allow: /\\n"\n        "Disallow: /admin/\\n"\n',
        "4",
    ),
    (
        "sitemap entries carry no <lastmod> date",
        "pages.py",
        "<url><loc>{loc}</loc><lastmod>{LASTMOD}</lastmod></url>",
        "<url><loc>{loc}</loc></url>",
        "5",
    ),
    (
        "sitemap lists a URL that 404s",
        "pages.py",
        '    lines.append("</urlset>")',
        '    lines.append(f"  <url><loc>{base}/nope</loc><lastmod>{LASTMOD}</lastmod></url>")\n'
        '    lines.append("</urlset>")',
        "5",
    ),
    (
        "og:image is a relative URL instead of an absolute one",
        "pages.py",
        '    image = SITE_URL + "/og-image.png"',
        '    image = "/og-image.png"',
        "6",
    ),
    (
        "the og:image meta tag is never emitted",
        "pages.py",
        "        f'<meta property=\"og:image\" content=\"{image}\">\\n'\n",
        "",
        "6",
    ),
    (
        "the card title is hard-coded and does not match the page <title>",
        "pages.py",
        "        f'<meta property=\"og:title\" content=\"{html.escape(title, quote=True)}\">\\n'",
        "        '<meta property=\"og:title\" content=\"Acme Tools\">\\n'",
        "6",
    ),
    (
        "there is no route for /og-image.png, so the card image 404s",
        "serve.py",
        '        if route == "/og-image.png":\n'
        '            self._respond(200, og_image_png(), "image/png")\n'
        '        elif route == "/robots.txt":',
        '        if route == "/robots.txt":',
        "6",
    ),
    (
        "the og:image is served as text/html instead of image/png",
        "serve.py",
        '            self._respond(200, og_image_png(), "image/png")',
        '            self._respond(200, og_image_png(), "text/html; charset=utf-8")',
        "6",
    ),
    (
        "the og:image is too short for a preview card",
        "pages.py",
        "OG_IMAGE_HEIGHT = 630",
        "OG_IMAGE_HEIGHT = 100",
        "6",
    ),
]
