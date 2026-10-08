"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

Each entry is (description, file, exact text in solutions/<file>, replacement,
check step). One classic mistake per exercise:

1. soft 404        - the server answers an unknown path with status 200.
2. duplicate titles - every page gets the home page's <title>.
3. missing description - the description tag is never emitted.
4. robots.txt disallows the site, or names /admin, or omits the Sitemap line.
5. sitemap.xml is missing lastmod, or lists a URL that 404s.
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
]
