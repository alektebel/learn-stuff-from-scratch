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
7. favicon: no <link rel="icon">, a declared size that lies, a 1x1 icon, no
   /favicon.ico route, or the icon served as text/html.
8. alt text: the decorative image loses alt="", the informative alt is a file
   name, the image-only link's alt is empty, an alt attribute is dropped, or
   every image is removed.
9. loading states: the server records every repeat, the form ships no
   idempotency key, the control is never disabled, the server dedups on the
   body instead of the key, or the order count route is missing.
10. error messages: the 500 page leaks the traceback, one generic string is
    returned for every field, an invalid POST gets the generic error page
    instead of the field-level form, bad input is accepted with no message, or
    the exception detail never reaches the server log.
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
        '            elif route == "/og-image.png":\n'
        '                self._respond(200, og_image_png(), "image/png")\n'
        '            elif route == "/favicon.ico":',
        '            elif route == "/favicon.ico":',
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
    (
        "no page emits a <link rel=\"icon\"> tag",
        "pages.py",
        '        f"{icon_link()}\\n"\n',
        "",
        "7",
    ),
    (
        "the declared favicon size (16x16) lies about the 32x32 icon",
        "pages.py",
        '<link rel="icon" type="image/png" sizes="32x32" href="/favicon.ico">',
        '<link rel="icon" type="image/png" sizes="16x16" href="/favicon.ico">',
        "7",
    ),
    (
        "the favicon is a 1x1 pixel",
        "pages.py",
        "def favicon_png(width=32, height=32, color=(220, 60, 60)):",
        "def favicon_png(width=1, height=1, color=(220, 60, 60)):",
        "7",
    ),
    (
        "there is no route for /favicon.ico, so the icon 404s",
        "serve.py",
        '            elif route == "/favicon.ico":\n'
        '                self._respond(200, favicon_png(), "image/png")\n',
        "",
        "7",
    ),
    (
        "the favicon is served as text/html instead of image/png",
        "serve.py",
        '            self._respond(200, favicon_png(), "image/png")',
        '            self._respond(200, favicon_png(), "text/html; charset=utf-8")',
        "7",
    ),
    (
        "the decorative image stops being silent (alt=\"\" becomes a description)",
        "pages.py",
        '<img src="/chart.png" alt="">',
        '<img src="/chart.png" alt="chart">',
        "8",
    ),
    (
        "the informative image uses its file name as alt",
        "pages.py",
        'alt="Headcount by department, 2025"',
        'alt="chart.png"',
        "8",
    ),
    (
        "the image-only link has no accessible name (alt=\"\")",
        "pages.py",
        '<img src="/logo.png" alt="Home">',
        '<img src="/logo.png" alt="">',
        "8",
    ),
    (
        "an image's alt attribute is removed entirely",
        "pages.py",
        '<img src="/chart.png" alt="Headcount by department, 2025">',
        '<img src="/chart.png">',
        "8",
    ),
    (
        "every <img> is removed from the pages",
        "pages.py",
        '            \'<p><a href="/"><img src="/logo.png" alt="Home"></a></p>\'\n'
        '            \'<img src="/chart.png" alt="Headcount by department, 2025">\'\n'
        '            \'<img src="/chart.png" alt="">\'',
        "",
        "8",
    ),
    (
        "the order server records every repeat instead of deduping on the key",
        "serve.py",
        "            new = not key or identity not in SEEN",
        "            new = True",
        "9",
    ),
    (
        "the form ships no idempotency key, so repeats cannot be collapsed",
        "pages.py",
        '        f\'<input type="hidden" name="idempotency_key" value="{key}">\\n\'\n',
        "",
        "9",
    ),
    (
        "the submit control is never disabled, so the click stays live",
        "pages.py",
        '        \'<form method="post" action="/order" '
        'onsubmit="this.querySelector(\\\'button\\\').disabled = true">\\n\'',
        "        '<form method=\"post\" action=\"/order\">\\n'",
        "9",
    ),
    (
        "the server dedups on the body's other fields instead of the key",
        "serve.py",
        "        identity = key",
        "        identity = hash(str(sorted(\n"
        "            (name, value) for name, values in fields.items()\n"
        "            if name != \"idempotency_key\" for value in values)))",
        "9",
    ),
    (
        "there is no /orders route, so the observer cannot count orders",
        "serve.py",
        '            elif route == "/orders":\n'
        '                self._respond(200, json.dumps({"count": len(ORDERS)}),\n'
        '                              "application/json; charset=utf-8")\n',
        "",
        "9",
    ),
    (
        "the 500 page leaks the traceback instead of logging it",
        "pages.py",
        '        "<h1>Something went wrong</h1>\\n"',
        '        "Traceback (most recent call last):\\n"'
        '        "<h1>Something went wrong</h1>\\n"',
        "10",
    ),
    (
        "every field gets the same generic error message",
        "pages.py",
        '    if field == "email":\n'
        '        return ("That is not an email address: use one @ with a domain after it, "\n'
        '                "like you@example.com.")\n',
        '    return "Invalid input: check this field and try again."\n',
        "10",
    ),
    (
        "an invalid POST gets the generic error page, not the field-level form",
        "serve.py",
        "                    self._respond(200, contact_page(values, errors))",
        "                    self._respond(200, server_error())",
        "10",
    ),
    (
        "the bad email is accepted, so no field-level message appears",
        "serve.py",
        '                if email.count("@") != 1 or not local or "." not in domain:\n'
        '                    errors["email"] = error_message("email", values["email"])\n',
        '                if False:\n'
        '                    errors["email"] = error_message("email", values["email"])\n',
        "10",
    ),
    (
        "the 500 path never writes the exception detail to SERVER_LOG",
        "serve.py",
        "        SERVER_LOG.append(traceback.format_exc())\n",
        "        pass\n",
        "10",
    ),
    # A version number on the page tells an attacker which exploits to try; step 10 now
    # scans for a dotted version, so this is caught even without the word "python".
    (
        "the 500 page leaks a version number",
        "pages.py",
        '        "<h1>Something went wrong</h1>\\n"',
        '        "<h1>Something went wrong</h1><p>3.14.7</p>\\n"',
        "10",
    ),
    # A real environment value is a secret; step 10 plants a sentinel and scans for it,
    # so this is caught deterministically whatever HOME happens to be.
    (
        "the 500 page leaks an environment value",
        "pages.py",
        '        "<h1>Something went wrong</h1>\\n"',
        '        "<h1>Something went wrong</h1>"\n'
        '        + __import__("os").environ.get("WLC_LEAK_PROBE", "") + "\\n"',
        "10",
    ),
]
