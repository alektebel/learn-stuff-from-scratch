# Solutions — web launch checklist, exercises 1-7

The reference site. `serve.py` routes the pages in `pages.py` and answers every
unknown path with the 404 page and status 404. It also serves `robots.txt` from
`pages.robots_txt`, `sitemap.xml` from `pages.sitemap_xml`, the Open Graph image
from `pages.og_image_png` at `/og-image.png` as `image/png`, and the favicon from
`pages.favicon_png` at `/favicon.ico` as `image/png`. `crawler.py`, `unfurl.py`
and `visit.py` are the provided observers (symlinked from the module root so the
mutation harness can carry them).

## Expected output

Copy these files next to `check.py` and run:

```
$ python3 check.py --all

Web launch checklist — progress check (exercises 1-7)
implement serve.py and pages.py, then run the observers

  ✓  1. serve.py  unknown paths return a real 404 page that links home
  ✓  2. pages.py  every page has a unique <title> within the length limit
  ✓  3. pages.py  every page has a <meta description> within snippet length
  ✓  4. serve.py/pages.py robots.txt allows the public site and names no secret
  ✓  5. pages.py  sitemap.xml is valid, complete and fetches 200
  ✓  6. pages.py/serve.py the unfurled card shows the page title, description and an absolute, real image
      icon /favicon.ico (linked=True): 32x32 png
  ✓  7. pages.py/serve.py every page points at a real favicon the browser can fetch

  7/7 passing

  All checks pass — the crawler sees a launchable site.
  Run crawler.py against it, then compare with solutions/.
```

## Seeing the crawler's report

Start the server, then point the observer at it:

```
$ python3 serve.py &            # serves http://127.0.0.1:8000/
$ python3 crawler.py http://127.0.0.1:8000/
crawled 5 pages from http://127.0.0.1:8000
  200  /            30 chars  Acme Tools — ship a small site
  200  /about       16 chars  About Acme Tools
  200  /pricing     20 chars  Pricing — Acme Tools
  200  /contact     18 chars  Contact Acme Tools
  200  /docs        17 chars  Docs — Acme Tools
  404  /this-page-does-not-exist-9f3a  (soft 404s: 0)
  sitemap lists 5 URLs
```

## Seeing the unfurled card

The same server, through the chat-app observer. A card is built per page: the
`/about` card differs from `/` in its title, description and `og:url`, while both
share the same absolute `og:image`.

```
$ python3 unfurl.py http://127.0.0.1:8000/
title:       Acme Tools — ship a small site
description: Acme Tools helps makers ship small websites and check them before launch.
url:         https://example.com/
type:        website
twitter:     summary_large_image
image:       https://example.com/og-image.png
image size:  1200x630, 3162 bytes, image/png
problems:    none
```

`unfurl.py` fetches `/og-image.png` from the server it was pointed at, not from
`https://example.com` (see the design decisions in `unfurl.py`): the declared
absolute URL is checked on the tag, and the bytes it names are measured on the
origin under test.

## Seeing the first visit

`visit.py` plays the browser: it fetches the pages, follows the icons they
declare, and records the cookies set. Both pages declare the same `/favicon.ico`,
so it is one linked request, and the size read from the PNG bytes agrees with the
declared `sizes="32x32"`.

```
$ python3 visit.py http://127.0.0.1:8000/ /about
visited 2 page(s) on http://127.0.0.1:8000
  200  /                           1228 B  text/html; charset=utf-8 page
  200  /about                      1248 B  text/html; charset=utf-8 page
  200  /favicon.ico                  99 B  image/png                linked
  icon: /favicon.ico -> 32x32 png
  cookies: none
  total: 2575 bytes in 3 request(s)
```

Remove the `<link rel="icon">` and a page still makes the browser guess
`/favicon.ico` (`guessed`): that unlinked request is the one exercise 4 is about,
and against the broken variant it lands on the exercise-1 404 page.

Against the broken variant (`_build/broken/`) the same crawl reports status 200
for the invented path (a soft 404), five identical titles, and no sitemap. That
is the "break" half of the first three exercises; `check.py` fails them. Steps 4-5
also fail there: the broken server answers `/robots.txt` with that same soft-404
HTML (status 200 with no `Sitemap:` line), and its `pages.py` has no `sitemap_xml`,
so step 5 reports ERROR (ImportError) rather than a clean FAIL. Step 6 fails too:
the broken pages carry no `og:` tags, so the card has no title, description or
image. Step 7 fails as well: the broken pages have no `<link rel="icon">`, and the
server has no `/favicon.ico` route, so the browser's guess 404s.

## The planted bugs

`_build/mutations.py` plants classic mistakes across the exercises; each is caught
by the named step (see the module README for the table). **Eighteen** mutations
are planted in total: seven across the first five check steps (exercises 1, 2, 3,
5 and 6), six more for Open Graph (exercise 7, check step 6), and five for the
favicon (exercise 4, check step 7). To reproduce any single bug: mutate
`solutions/`, copy `solutions/*.py` and `check.py` into a temporary directory, and
run `python3 check.py <step>` there.
