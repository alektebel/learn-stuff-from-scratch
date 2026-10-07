# Solutions — web launch checklist, exercises 1-3

The reference site. `serve.py` routes the pages in `pages.py` and answers every
unknown path with the 404 page and status 404. `crawler.py` is the provided
observer (symlinked from the module root so the mutation harness can carry it).

## Expected output

Copy these files next to `check.py` and run:

```
$ python3 check.py --all

Web launch checklist — progress check (exercises 1-3)
implement serve.py and pages.py, then run the observers

  ✓  1. serve.py  unknown paths return a real 404 page that links home
  ✓  2. pages.py  every page has a unique <title> within the length limit
  ✓  3. pages.py  every page has a <meta description> within snippet length

  3/3 passing

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
```

Against the broken variant (`_build/broken/`) the same crawl reports status 200
for the invented path (a soft 404), five identical titles, and no sitemap. That
is the "break" half of the exercise; `check.py` fails all three steps against it.

## The three planted bugs

`_build/mutations.py` plants one classic mistake per exercise; each is caught by
the named step (see the module README for the table). To reproduce any single
bug: mutate `solutions/`, copy `solutions/*.py` and `check.py` into a temporary
directory, and run `python3 check.py <step>` there.
