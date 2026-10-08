# Solutions — web launch checklist, exercises 1-11

The reference site. `serve.py` routes the pages in `pages.py` and answers every
unknown path with the 404 page and status 404. It also serves `robots.txt` from
`pages.robots_txt`, `sitemap.xml` from `pages.sitemap_xml`, the Open Graph image
from `pages.og_image_png` at `/og-image.png` as `image/png`, the favicon from
`pages.favicon_png` at `/favicon.ico` as `image/png`, the two body images at
`/logo.png` and `/chart.png` as `image/png` (reusing the same two helpers), the
order form from `pages.order_page` at `/order`, the recorded-order count at
`/orders`, and the contact form from `pages.contact_page` at `/contact`.
`POST /order` records `(product, idempotency_key)` once per key, under
a lock, so a multi-click on one form is one order. `POST /contact` validates the
name, email and message and re-renders the form at status 200 with one
`pages.error_message` next to each bad field; a valid submission gets a short
confirmation. Every response carries the strictly-necessary `wlc_session` cookie;
`POST /consent` with `choice=accept` adds the analytics cookie `wlc_analytics`,
and `choice=reject` adds no analytics cookie at all. `GET /boom` deliberately
raises: the handler catches it, appends the traceback to `SERVER_LOG` and answers
500 with the generic `pages.server_error()`, which carries no detail.
`crawler.py`, `unfurl.py`, `visit.py`, `reader.py` and `impatient.py` are the
provided observers (symlinked from the module root so the mutation harness can
carry them).

## Expected output

Copy these files next to `check.py` and run:

```
$ python3 check.py --all

Web launch checklist — progress check (exercises 1-11)
implement serve.py and pages.py, then run the observers

  ✓  1. serve.py  unknown paths return a real 404 page that links home
  ✓  2. pages.py  every page has a unique <title> within the length limit
  ✓  3. pages.py  every page has a <meta description> within snippet length
  ✓  4. serve.py/pages.py robots.txt allows the public site and names no secret
  ✓  5. pages.py  sitemap.xml is valid, complete and fetches 200
  ✓  6. pages.py/serve.py the unfurled card shows the page title, description and an absolute, real image
      icon /favicon.ico (linked=True): 32x32 png
  ✓  7. pages.py/serve.py every page points at a real favicon the browser can fetch
  ✓  8. pages.py  images carry alt text, decorative ones are silent
      order attempt key=912aaf11 -> 200 in 0.5 ms
      order attempt key=912aaf11 -> 200 in 0.5 ms
      order attempt key=912aaf11 -> 200 in 0.5 ms
  ✓  9. pages.py/serve.py a double submit records one order and the control disables on submit
      invalid email -> 'That is not an email address: use one @ with a domain after it, like you@example.com.'
      short message  -> 'Your message is too short: write at least 10 characters so we can help.'
      valid input    -> accepted, no field error
      500 page leaks nothing; the log holds the detail
  ✓ 10. pages.py/serve.py invalid input gets a field-level message; a 500 leaks nothing
      cookies before any choice: wlc_session
      consent controls: accept=<button> reject=<button>
      accept -> wlc_session=...; Path=/; HttpOnly; SameSite=Lax wlc_analytics=1; Path=/
      reject -> analytics cookie absent
  ✓ 11. pages.py/serve.py no analytics cookie before consent; accept sets it, reject does not

  11/11 passing

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
declare, and records the cookies set. Every response sets the strictly-necessary
`wlc_session` cookie, and before the visitor has chosen anything there is no
analytics cookie. Both pages declare the same `/favicon.ico`, so it is one linked
request, and the size read from the PNG bytes agrees with the declared
`sizes="32x32"`.

```
$ python3 visit.py http://127.0.0.1:8000/ /about
visited 2 page(s) on http://127.0.0.1:8000
  200  /                           1830 B  text/html; charset=utf-8 page
  200  /about                      1708 B  text/html; charset=utf-8 page
  200  /favicon.ico                  99 B  image/png                linked
  icon: /favicon.ico -> 32x32 png
  cookies: {'wlc_session': '488685ef60494fde8395a2026a054f68'}
  total: 3637 bytes in 3 request(s)
```

Remove the `<link rel="icon">` and a page still makes the browser guess
`/favicon.ico` (`guessed`): that unlinked request is the one exercise 4 is about,
and against the broken variant it lands on the exercise-1 404 page.

## Seeing the cookie consent

The banner is a `POST` form with two `<button>` controls of equal prominence, so
a search bot cannot follow an "accept" link and the sitemap surface does not grow.
A plain `GET` sets only the strictly-necessary `wlc_session` cookie; the
non-essential `wlc_analytics` cookie appears only on the response to
`choice=accept`, and never on `choice=reject`.

```
$ python3 - <<'PY'
import urllib.request, urllib.parse
def post(choice):
    data = urllib.parse.urlencode({"choice": choice}).encode()
    req = urllib.request.Request("http://127.0.0.1:8000/consent", data=data,
        method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    r = urllib.request.urlopen(req)
    print(choice, "->", r.status, r.headers.get_all("Set-Cookie"))

r = urllib.request.urlopen("http://127.0.0.1:8000/")
print("GET / ->", r.status, r.headers.get_all("Set-Cookie"))
post("accept")
post("reject")
PY
GET / -> 200 ['wlc_session=3db41f61...; Path=/; HttpOnly; SameSite=Lax']
accept -> 200 ['wlc_session=d8166150...; Path=/; HttpOnly; SameSite=Lax', 'wlc_analytics=1; Path=/']
reject -> 200 ['wlc_session=5d8f3ce9...; Path=/; HttpOnly; SameSite=Lax']
```

The reject response carries no `wlc_analytics` at all: recording a refusal is not
permission, so there is nothing to expire for a visitor who never had one.
`check.py` step 11 reads the same three responses.

## Seeing the screen reader

`reader.py` linearises each page and lists the images it heard. The home page
carries three images: a logo that is the only content of its link, so its `alt`
becomes the link's name; an informative chart with a real description; and a
decorative chart whose `alt=""` keeps it out of the text. The linear text contains
the two spoken alts and no file name, and the `/about` page has no images.

```
$ python3 reader.py http://127.0.0.1:8000/ /about
page / — linearised text:
  Acme Tools — ship a small site Home · About · Pricing · Contact · Docs Acme Tools Everything you need to launch a small, honest website. Home Headcount by department, 2025 Home · About · Pricing · Contact · Docs
  images:
    /logo.png alt='Home' image-only link
    /chart.png alt='Headcount by department, 2025'
    /chart.png alt=''
  warnings: none
page /about — linearised text:
  About Acme Tools Home · About · Pricing · Contact · Docs About Acme Tools We measure what a search bot, a chat card and a screen reader actually see. Home · About · Pricing · Contact · Docs
  images:
    (none)
  warnings: none
```

Break an image — drop its `alt`, or set `alt="chart.png"` — and the observer
prints a warning naming the `src` and the two mistakes the fix removes: a missing
alt falls back to the file name, and an alt that is a file name is not a
description.

Against the broken variant (`_build/broken/`) the same crawl reports status 200
for the invented path (a soft 404), five identical titles, and no sitemap. That
is the "break" half of the first three exercises; `check.py` fails them. Steps 4-5
also fail there: the broken server answers `/robots.txt` with that same soft-404
HTML (status 200 with no `Sitemap:` line), and its `pages.py` has no `sitemap_xml`,
so step 5 reports ERROR (ImportError) rather than a clean FAIL. Step 6 fails too:
the broken pages carry no `og:` tags, so the card has no title, description or
image. Step 7 fails as well: the broken pages have no `<link rel="icon">`, and the
server has no `/favicon.ico` route, so the browser's guess lands on the soft-404
HTML (status 200, `text/html`), not an image. Step 8 fails for
the same reason its "break" half describes: the broken pages carry no images at
all, so none of the alt rules can pass.

## Seeing the impatient user

`impatient.py` loads `/order`, reads the form's hidden `idempotency_key` and its
`onsubmit`, then submits the form three times with that one key. The three clicks
are one form view, so the server records one order; the count is read from
`/orders` before and after, not trusted from the response. `ORDER_DELAY` is `0.0`
here so the run is instant; set it to `3.0` in `serve.py` to see the three-second
API the exercise is about.

```
$ python3 impatient.py http://127.0.0.1:8000/
submitted the order form 3 time(s) on http://127.0.0.1:8000
  click 1: key=97362c36 status=200 0.3 ms
  click 2: key=97362c36 status=200 0.5 ms
  click 3: key=97362c36 status=200 0.4 ms
  disables the control on submit: True
  submit control label: 'Place order'
  orders before: 0  after: 1  recorded: 1
```

A standard-library observer cannot watch the browser paint, so `disable_on_submit`
is read structurally from the form's `onsubmit` (or an inline script): it is the
stand-in for "the user sees feedback within 100 ms". With `ORDER_DELAY = 3.0` the
same run reports each click at about `3.00 s` and still one recorded order — the
UX half (feedback, a disabled control) and the correctness half (the idempotency
key) are separate, and the check grades both.

## Seeing the error messages and the 500 page

The contact form validates on the server and comes back as the same page with a
message next to each bad field. `GET /boom` raises on purpose: the handler keeps
the traceback in `SERVER_LOG` and returns the generic 500 page, whose body carries
none of it.

```
$ python3 - <<'PY'
import threading, urllib.request, urllib.parse
import serve
server = serve.make_server(port=0)
base = "http://127.0.0.1:%d" % server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

def post(fields):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(base + "/contact", data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status, r.read().decode()
    except OSError as e:
        return e.code, e.read().decode()

def get(path):
    try:
        r = urllib.request.urlopen(base + path, timeout=5)
        return r.status, r.read().decode()
    except OSError as e:
        return e.code, e.read().decode()

status, body = post({"name": "Ada", "email": "not-an-email",
                     "message": "Please help me launch the site."})
print("POST /contact email=not-an-email ->", status)
print("  ", [l.strip() for l in body.splitlines() if 'class="error"' in l][0])

status, body = post({"name": "Ada", "email": "ada@example.com", "message": "x"})
print("POST /contact message=x ->", status)
print("  ", [l.strip() for l in body.splitlines() if 'class="error"' in l][0])

status, body = get("/boom")
print("GET /boom ->", status, "leaks:",
      [t for t in ("Traceback", "RuntimeError", "boom", ".py")
       if t.lower() in body.lower()] or "none")
print("  log tail:", serve.SERVER_LOG[-1].strip().splitlines()[-1])
server.shutdown(); server.server_close()
PY
POST /contact email=not-an-email -> 200
   <p class="error" id="error-email">That is not an email address: use one @ with a domain after it, like you@example.com.</p>
POST /contact message=x -> 200
   <p class="error" id="error-message">Your message is too short: write at least 10 characters so we can help.</p>
GET /boom -> 500 leaks: none
  log tail: RuntimeError: boom: simulated backend failure
```

The two field errors are different strings: the email message names the `@` and a
domain, the message one names the minimum length. The 500 body names none of
`Traceback`, `RuntimeError`, `boom`, `.py` or a Python version; the last line of
`SERVER_LOG` names the exception. `check.py` step 10 asserts exactly that.

## The planted bugs

`_build/mutations.py` plants classic mistakes across the exercises; each is caught
by the named step (see the module README for the table). **Forty-nine** mutations
are planted in total: seven across check steps 1-5 (the 404, titles,
descriptions, robots and sitemap), six for Open Graph (check step 6), five for the
favicon (check step 7), five for alt text (check step 8), five for loading
states (check step 9), seven for error messages (check step 10) and fourteen for
cookies (check step 11). To reproduce
any single bug: mutate `solutions/`, copy `solutions/*.py` and `check.py` into a
temporary directory, and run `python3 check.py <step>` there.
