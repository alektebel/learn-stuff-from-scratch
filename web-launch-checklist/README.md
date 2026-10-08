# Web launch checklist, from the failure side

Sixteen items that "every site should have before launch". The usual list says *what*;
these exercises make you find out *why*, by putting an observer in front of a site that
lacks the item and measuring the damage, then fixing it and measuring again.

**Status: exercises 1-12 are built.** `crawler.py`, `unfurl.py`, `visit.py`,
`reader.py` and `impatient.py` (the observers), `check.py`, the reference in
`solutions/` and a runnable broken variant in `_build/broken/` are here. The
eleventh check grades the cookies/consent exercise (13), and the twelfth grades
the analytics exercise (14) against `analytics.py`; the mobile exercise (9)
still needs `mobile.py` and Chromium, and exercises 12 and 15-16 are specified
only. No conceptual answers are written anywhere in this directory, on purpose:
each exercise ends with questions, and the observer's output is what answers
them.

## How it works

`serve.py`, a stdlib `http.server` with routing, over a site described in
`pages.py`. You do not get a framework, because frameworks do half of this list
silently, and then you never learn which half.

The **observers** are provided. Each one sees the site the way some real agent does:

| Observer | Plays the role of | Measures |
|---|---|---|
| `crawler.py` | a search-engine bot | status codes, titles, descriptions, robots.txt rules, sitemap, link graph |
| `unfurl.py` | a chat app turning a pasted link into a preview card | what the card shows |
| `reader.py` | a screen reader linearising the page | the text a blind user hears |
| `mobile.py` | a phone, through headless Chromium at 375 px | horizontal overflow, text size, tap targets |
| `visit.py` | a browser on a first visit over a slow network | requests made, bytes transferred, cookies set and when |
| `impatient.py` | a user on a slow API who clicks twice | duplicate submissions, what they saw while waiting |

`crawler.py`, `unfurl.py`, `visit.py`, `reader.py` and `impatient.py` exist today;
`mobile.py` is specified in the exercises below.

`check.py` runs the observers and grades each exercise, in this repo's usual format.
Exercises 1-12 are graded now (twelve checks); the rest are TODO until their observers
exist.

Runs on a CPU: Python standard library only for exercises 1-12. Later exercises warm
up the machine (Pillow with WebP, a Chromium binary) but there is no network.

## What is provided, what you build

The original plan was ambiguous about this. The smallest workable split:

| Part | Who | Why |
|---|---|---|
| `crawler.py` | **provided** | An observer is a measuring instrument; you would not learn the exercise by re-implementing the ruler. Read it, do not edit it. |
| `unfurl.py` | **provided** | The chat-app observer: what a pasted link's preview card shows, for exercise 7. |
| `reader.py` | **provided** | The screen-reader observer: the linear text, every image and the two `alt` mistakes, for exercise 8. |
| `visit.py` | **provided** | The per-visit browser observer: every request on a first load, the icon measurements and the cookies set, for exercise 4 (and 13). |
| `impatient.py` | **provided** | The slow-API observer: three clicks on an order form, the orders the server recorded, and the mechanism that disables the control, for exercise 10. Its `fetch`/`post_form` HTTP helpers are reused by the error-message check (exercise 11) and its `post_form_headers` by the cookie check (exercise 13). |
| `check.py` | **provided** | The grader. Never imports `solutions/`. |
| `serve.py` | **you** | Routing, the 404 status, the order API (dedup by idempotency key), the error path and the cookie policy: the decisions exercises 1, 10, 11 and 13 are about. |
| `pages.py` | **you** | The site's HTML: titles and descriptions, the icon link and the images' alt text, the order form, the consent banner, and the contact form with its error messages and 500 page: the subject of exercises 2, 3, 4, 8, 10, 11 and 13. |
| `analytics.py` | **you** | The page-view counter: filter out bots, prefetches, reloads, assets and unconsented requests, and store nothing personal: the subject of exercise 14. |
| `_build/broken/` | **provided** | A complete site with the three defects planted; run the crawler against it for the "Break" half. |
| `solutions/` | **reference** | Do not read it until `check.py` passes, or until you are stuck. |

There is no `site/` directory of loose `.html` files. The page HTML lives in
`pages.py` for one concrete reason: the mutation harness
(`.claude/skills/graded-module/scripts/mutate.py`) builds its sandbox by copying
`check.py` and every `solutions/*.py`, so a directory of HTML would not travel
with it and two of the three planted bugs would be untestable. The HTML inside
`pages.py` is ordinary HTML, and the observer still reads it over HTTP.

## How to run

```
cd web-launch-checklist
python3 check.py          # stop at the first step you have not written
python3 check.py --all    # run all twelve checks (exercises 1-12)
```

Start the reference site (swap `solutions` for `_build/broken` for the broken
variant), then observe it by hand to see what a bot, a chat app, a browser, a
screen reader and an impatient user see:

```
(cd solutions && python3 serve.py) &                 # http://127.0.0.1:8000/
python3 crawler.py http://127.0.0.1:8000/            # the search-bot report
python3 unfurl.py http://127.0.0.1:8000/             # the chat-app preview card
python3 visit.py http://127.0.0.1:8000/ /about       # the browser's first visit
python3 reader.py http://127.0.0.1:8000/ /about      # the screen-reader linear text
python3 impatient.py http://127.0.0.1:8000/          # three clicks on the order form
```

`serve.py` and `pages.py` are shipped as frozen stubs: every step reports TODO
(not ERROR) until you write it. To see the damage the checks catch, run the
crawler against the complete broken variant in `_build/broken/` first.

## The exercises

Every exercise has the same three moves. **Break**: run the observer against the version
without the item, and write down what it reports. **Fix**: implement the item. **Check**:
the graded check passes, and the observer's numbers changed in the way you predicted.

### 1. Custom 404 page
- **Break:** make the server answer every unknown path with your home page and status 200
  (what many single-page apps do by default). Crawl the site after deleting a page.
- **Fix:** a real 404 status, a page that helps (search, links home), no redirect to `/`.
- **Check:** unknown paths return 404 with a body that links back; the crawler reports
  zero "soft 404s"; deleted pages drop out of the crawler's index.
- **Questions:** What did the crawler index for a page that no longer exists? Why is
  "redirect everything to home" worse than a plain 404 for both users and bots?

### 2. A meta title on every page
- **Break:** every page with the same `<title>`. Ask the crawler for its results list.
- **Fix:** unique, descriptive titles; the check enforces uniqueness and a length limit.
- **Questions:** From the results list alone, could a user tell your pages apart? What
  does the browser tab show when ten of your pages are open?

### 3. Meta description
- **Break:** no description. Look at the snippet the crawler builds for each page.
- **Fix:** one description per page, within the length the crawler displays.
- **Questions:** Where did the crawler take the snippet from without one? Is a description
  a ranking signal or something else? (Find out what the observer actually uses it for.)

### 4. Favicon
- **Break:** no favicon. Run `visit.py` on ten pages and read the server log.
- **Fix:** an icon at `/favicon.ico` plus the `<link rel="icon">` sizes the observer asks for.
- **Check:** `/favicon.ico` is served as a real image at 32x32 (or 16x16), and every page's
  `<link rel="icon" sizes=...>` states the size the bytes actually are.
- **Questions:** How many requests did a browser make that you never linked to? What does
  each one cost the server when it returns your custom 404 page from exercise 1?

### 5. robots.txt
- **Break, twice.** (a) Deploy the staging `robots.txt` that disallows everything. (b) Hide
  `/admin` by listing it in `robots.txt`.
- **Fix:** serve a `robots.txt` that does what you mean. The longest-match
  `Allow`/`Disallow` parser is the provided observer (`crawler.parse_robots` /
  `crawler.allowed`); read it, do not rewrite it — the exercise is the site's file,
  not the ruler.
- **Check:** every public page is allowed over HTTP, a `Sitemap:` line points at
  `/sitemap.xml`, and no secret path (`/admin`) is named in the file.
- **Questions:** In (b), who reads `robots.txt` besides well-behaved bots? What actually
  protects `/admin`? (Compare with `web-scraping/`, which implements the crawler's side.)

### 6. sitemap.xml
- **Break:** add a page nothing links to. Crawl.
- **Fix:** generate `sitemap.xml` from the site's pages, with `lastmod`, and reference it
  from `robots.txt`.
- **Check:** valid XML, every public page listed, no 404s and no disallowed URLs in it;
  the orphan page is discovered.
- **Questions:** Does a sitemap make a page rank, or only make it findable? What goes wrong
  when the sitemap lists URLs that redirect?

### 7. Open Graph image (and tags)
- **Break:** no `og:` tags. Paste a page URL into `unfurl.py`.
- **Fix:** `og:title`, `og:description`, `og:image` (absolute URL, recommended size), `og:url`.
- **Check:** the card shows your title, description and image; a relative `og:image` fails.
- **Questions:** What did the card show without the tags? Why must the image URL be
  absolute? What does a 5 MB image do to the card?

### 8. Alt text on images
- **Break:** images without `alt`. Run `reader.py`.
- **Fix:** meaningful `alt` on informative images, `alt=""` on decorative ones.
- **Check:** no image read out as a filename; decorative images are silent; an image that
  is the only content of a link has alt text describing the link's destination.
- **Questions:** What did the reader say for `IMG_2041.jpg`? Why is `alt=""` different from
  a missing `alt`? Which law applies to your site's accessibility where you live? (Look it
  up; do not guess.)

### 9. Responsive on mobile
- **Break:** remove the viewport meta tag; add one fixed-width 900 px element. Run `mobile.py`.
- **Fix:** viewport tag, fluid layout, readable base font size, tap targets of usable size.
- **Check:** no horizontal overflow at 375 px; body text at least the observer's minimum;
  tap targets above its minimum size and not overlapping.
- **Questions:** At what width did the phone render the page without the viewport tag, and
  why that number? Which single element caused the overflow?

### 10. Loading states
- **Break:** `impatient.py` submits an order form against an API that takes 3 s.
- **Fix:** an immediate visual state, a disabled control, and a server that tolerates a
  repeat (an idempotency key).
- **Check:** one order recorded however many clicks; the user sees feedback within 100 ms.
- **Questions:** How many orders did the impatient user place? Which part of the fix is
  UX and which part is correctness? Would the UX fix alone have been enough?

> A standard-library observer cannot watch the browser paint, so `impatient.py`
> grades the immediate state *structurally*: it reads the form's `onsubmit` (or a
> script) and requires that it disables the submit control, rather than timing a
> repaint. `serve.py` keeps `ORDER_DELAY` at `0.0` so the checks stay fast; set it
> to `3.0` by hand to watch the observer wait three seconds per click.

### 11. Error messages
- **Break:** let a form error surface as the framework default; make the server raise.
- **Fix:** messages that say what went wrong and how to fix it, next to the field; a
  generic 500 page for users and the detail in the server log only.
- **Check:** each invalid input yields a specific, field-level message; the 500 page leaks
  no stack trace, file path, version or environment variable.
- **Questions:** What could an attacker learn from your original 500 page? What does a user
  do with "Error: invalid input"?

### 12. Terms and conditions
- **Not graded by code.** Legal requirements depend on jurisdiction and on what the site
  does. Exercise: list what your site actually does with users (accounts, payments, user
  content, data collected), then find which documents the law where you operate requires
  (in Spain: LSSI-CE and the GDPR, at least), from the official texts, not from a template
  generator.
- **Questions:** Which clause of a template you were going to copy does not apply to your
  site, and what would it promise that you cannot keep?

### 13. Cookies, if they apply
- **Break:** load analytics that set cookies on the first visit.
- **Fix:** no non-essential cookie before consent; consent recorded; rejecting as easy as
  accepting.
- **Check:** `visit.py` sees only strictly necessary cookies before any choice; analytics
  cookies appear only after "accept"; "reject" leaves none.
- **Questions:** Which of your cookies are "strictly necessary", by what definition? What
  does the Spanish data-protection authority's cookie guide say about a "reject" button?
  (Find the guide; do not guess.)

### 14. Analytics
- **Break:** count every request to a page as a view.
- **Fix:** a minimal page-view counter: bots filtered, reloads and prefetches handled,
  consent respected, no personal data stored.
- **Check:** against a synthetic traffic log with known ground truth, the counts fall
  within tolerance; the crawler's visits are not counted.
- **Questions:** How far off was the naive count? What can you not measure once consent is
  respected, and how does that bias the numbers that remain?

### 15. Real contact methods
- **Break:** a contact form that posts nowhere, and a `mailto:` that does not exist.
- **Fix:** a form that stores or sends each message, validates its input, resists trivial
  spam (a honeypot field, a rate limit) and confirms receipt to the user.
- **Check:** a submitted message can be retrieved; spam-bot submissions are rejected; a
  human submission is not; the user sees confirmation.
- **Questions:** How would you find out, without the check, that your contact form had been
  silently broken for a month?

### 16. Compressed images (WebP)
- **Break:** serve camera-size JPEG/PNG photos scaled down in CSS. Run `visit.py` slow.
- **Fix:** resize to display size, encode WebP (Pillow), serve `srcset`, set width and height.
- **Check:** bytes transferred drop by the observer's threshold; no image is served larger
  than twice its displayed size; layout does not shift when images load.
- **Questions:** Was WebP smaller for every image? Try a screenshot with flat colours and
  text against PNG. What did resizing save, compared with changing the format?

## Mutation table (exercises 1-12)

`_build/mutations.py`, run through
`.claude/skills/graded-module/scripts/mutate.py`, plants the classic mistake for
each exercise (fifty-nine in all). Every one must be CAUGHT by the named step.

| Planted bug | File | Caught by | Why it is a classic mistake |
|---|---|---|---|
| Unknown path answered with status 200 | `serve.py` | step 1 | The soft 404: a bot indexes a deleted URL forever. |
| Every page uses the home page's `<title>` | `pages.py` | step 2 | Copy-paste the layout, forget the title: ten identical tabs. |
| The description tag is never emitted | `pages.py` | step 3 | The snippet silently falls back to an arbitrary sentence. |
| `robots.txt` disallows the whole public site | `pages.py` | step 4 | A staging file ships to production and schools every bot away. |
| `robots.txt` names `/admin` | `pages.py` | step 4 | The file is public: naming a secret advertises it, it does not protect it. |
| Sitemap entries carry no `<lastmod>` | `pages.py` | step 5 | Without a date the bot cannot tell how fresh a page is. |
| The sitemap lists a URL that 404s | `pages.py` | step 5 | A sitemap full of dead URLs teaches the bot to distrust the whole file. |
| `og:image` is a relative URL | `pages.py` | step 6 | A card is rendered away from the page, with no base to resolve a relative path against, so the image vanishes. |
| No `og:image` tag is emitted | `pages.py` | step 6 | The shared link unfurls as bare text with no picture. |
| The card title is hard-coded, not the page's `<title>` | `pages.py` | step 6 | Every shared link is mislabelled, and the card disagrees with the page. |
| No `/og-image.png` route | `serve.py` | step 6 | The tag promises an image the server never serves, so the card shows a broken image. |
| The image is served as `text/html` | `serve.py` | step 6 | The type says HTML, so the chat app refuses to render it as a picture. |
| The image is too short for a card | `pages.py` | step 6 | A below-recommended image is upscaled or cropped; the card looks broken. |
| No page emits a `<link rel="icon">` | `pages.py` | step 7 | The browser guesses `/favicon.ico`; the page never says which icon it uses. |
| The declared `sizes="32x32"` is a lie (`16x16`) | `pages.py` | step 7 | A wrong size makes the browser skip the icon or fetch a second one. |
| The favicon is a 1x1 pixel | `pages.py` | step 7 | A single pixel is scaled to a blur or ignored. |
| No `/favicon.ico` route | `serve.py` | step 7 | Every page's implicit request 404s, paying for a full 404 page. |
| The favicon is served as `text/html` | `serve.py` | step 7 | The browser refuses to render it as an icon. |
| The decorative image's `alt=""` becomes a description | `pages.py` | step 8 | Without the empty `alt` the decoration is announced as if it carried meaning. |
| The informative image's `alt` is its file name | `pages.py` | step 8 | A screen reader then says "chart dot p n g"; a file name describes nothing. |
| The image-only link's `alt=""` | `pages.py` | step 8 | With no text inside the `<a>`, the alt is the link's label; empty leaves it unnamed. |
| An image's `alt` attribute is dropped | `pages.py` | step 8 | Missing alt is the fallback to the file name; the reader announces the `src`. |
| Every `<img>` is removed from the pages | `pages.py` | step 8 | The informative images are gone and none of the alt rules is exercised. |
| The order server records every repeat | `serve.py` | step 9 | Three clicks become three orders and three charges. |
| The form ships no idempotency key | `pages.py` | step 9 | Repeats cannot be collapsed: the server has nothing to dedup on. |
| The submit control is never disabled | `pages.py` | step 9 | The button stays live through a slow call, inviting the second click. |
| The server dedups on the body, not the key | `serve.py` | step 9 | Two distinct submissions with the same product collapse into one, dropping an order. |
| The `/orders` count route is missing | `serve.py` | step 9 | No one can tell how many orders a burst of clicks actually placed. |
| The 500 page leaks the traceback | `pages.py` | step 10 | A stack trace tells an attacker your paths, versions and secrets, and helps no user. |
| One generic error message for every field | `pages.py` | step 10 | "Invalid input" leaves the user with nothing to change. |
| An invalid POST gets the generic error page | `serve.py` | step 10 | The user loses what they typed and never learns which field was wrong. |
| The bad email is accepted with no message | `serve.py` | step 10 | The form "succeeds" with input the backend cannot use. |
| The 500 path never logs the detail | `serve.py` | step 10 | The user sees nothing useful and the team sees nothing at all: the bug is invisible. |
| A version number on the 500 page | `pages.py` | step 10 | A version tells an attacker which exploits to try. |
| An environment value on the 500 page | `pages.py` | step 10 | An environment value can be a token or a path: a secret leaked to the user. |
| The analytics cookie is set on the first GET | `serve.py` | step 11 | Loading analytics before consent is the tracking the exercise removes. |
| Reject also sets the analytics cookie | `serve.py` | step 11 | Recording a refusal is not permission; rejecting must leave none. |
| The banner has no reject control | `pages.py` | step 11 | Consent is not valid if the visitor cannot decline as easily as accept. |
| Accept is a `<button>`, reject a plain `<a>` | `pages.py` | step 11 | A button beside a faint link makes rejecting harder than accepting. |
| Accept never sets the analytics cookie | `serve.py` | step 11 | Consent that is not recorded cannot be honoured. |
| Accept's cookie is already expired | `serve.py` | step 11 | An empty or expired cookie is not consent recorded. |
| A third non-essential cookie on the first GET | `serve.py` | step 11 | A tracker set before any choice is exactly what consent forbids. |
| Reject is a `type="button"` that never submits | `pages.py` | step 11 | A control that does not submit the form does not record the choice. |
| The reject control is inside a disabled fieldset | `pages.py` | step 11 | A disabled ancestor makes the control unusable, disabled attribute or not. |
| Accept's cookie is already expired by date | `serve.py` | step 11 | A past `Expires` is as dead as `Max-Age=0`, so no consent was recorded. |
| Reject redirects and sets the cookie anyway | `serve.py` | step 11 | A cookie set on the redirect still tracks the visitor who refused. |
| Reject clears then re-sets the analytics cookie | `serve.py` | step 11 | Browsers keep the last `Set-Cookie`, so a clear followed by a value is consent the visitor never gave. |
| Reject sets a differently named tracking cookie | `serve.py` | step 11 | Any live non-session cookie on reject is tracking, whatever its name. |
| Reject is an unquoted `type=button` | `pages.py` | step 11 | An unquoted `type=button` still never submits; quoting is not required in HTML. |
| `is_bot` never filters a crawler | `analytics.py` | step 12 | The crawler's visits are counted as human page views, inflating every number. |
| `count_views` counts every GET | `analytics.py` | step 12 | With the filters gone, the naive length is the answer: bots, assets and reloads all count. |
| `count_views` ignores consent | `analytics.py` | step 12 | Counting people who never agreed turns analytics into tracking. |
| `is_prefetch` never fires | `analytics.py` | step 12 | Speculative fetches are counted before the user ever arrives. |
| `is_reload` never fires | `analytics.py` | step 12 | A refresh doubles the count of one real visit. |
| The result keeps the user-agent | `analytics.py` | step 12 | A view count that stores the user-agent is personal data, not an aggregate. |
| The asset test ignores the query string | `analytics.py` | step 12 | `/site.css?v=2` is still a stylesheet, not a page view. |
| `is_prefetch` needs one exact token | `analytics.py` | step 12 | A `Purpose` header can carry several tokens; any of them means speculative. |
| The result keeps a timestamp | `analytics.py` | step 12 | A timestamp per view is request metadata, not an aggregate count. |
| A blank user-agent counts as a human | `analytics.py` | step 12 | An explicit blank user-agent is a bot, unlike a missing one. |

## Design decisions

- **The 404 status is the server's, the 404 body is the site's.** `pages.not_found()`
  returns a helpful page that links home; `do_GET` chooses status 404. Grading them
  separately is what keeps "real 404" and "links home" from hiding each other.
- **Route by an explicit map, not by "does the file exist".** A file-based server
  blurs "never written" and "deleted"; the map makes the public surface explicit.
- **The observer probes an invented path.** Soft-404 detection is a request for a
  path that cannot exist: status 404 is real, status 200 is soft. No heuristics on
  the body, which would flag a page that merely says "not found".
- **The pages module, not a `site/` directory** (see "What is provided" above).
- **Open Graph URLs are absolute, and the image is generated.** `og:image` and
  `og:url` are built from the canonical `SITE_URL`; a chat app rendering the card
  has no page to resolve a relative path against. The image is a real PNG built by
  `og_image_png` from `zlib` + `struct`, so a `.py`-only sandbox still has it, and
  `unfurl.py` measures the bytes the origin under test actually serves.
- **The favicon is linked at the size it is served, and measured from its bytes.**
  Every page carries `<link rel="icon" type="image/png" sizes="32x32" href="/favicon.ico">`;
  `visit.py` reads the real size out of the PNG header rather than trusting `sizes`,
  so a page that declares 16x16 while serving 32x32 is caught. The icon is built by
  `favicon_png` for the same `.py`-only-sandbox reason as the card image, and it is
  served at the one URL a browser also guesses when a page declares no icon.
- **Every image is described or explicitly silent.** `alt` is a real description on
  an informative image and `alt=""` on decoration; a missing `alt` makes the screen
  reader fall back to the file name, and `reader.py` flags an alt that *is* a file
  name. An image that is the only content of a link takes its alt as the link's
  accessible name. The body images reuse `favicon_png`/`og_image_png` through the
  `/logo.png` and `/chart.png` routes, so no new image code is needed.
- **Consent is a POST form, and the analytics cookie is set in one place.**
  `pages.consent_banner` renders a `<form method="post" action="/consent">` with two
  `<button>` controls of equal prominence, so a bot cannot follow an accept link and
  the sitemap surface does not grow. `serve.py` sets the strictly-necessary
  `SESSION_COOKIE` in `_respond` on every response, and the non-essential
  `ANALYTICS_COOKIE` only in the `choice=accept` branch of `POST /consent`; a plain
  `GET` never sets it, and `reject` sets nothing.
- **The page-view counter filters the log; it does not trust its length.**
  `analytics.count_views` drops bots, prefetches, reloads, assets, non-GET requests and
  unconsented visitors, and returns `{"views": {path: count}, "total": n}` with no
  user-agent, IP or cookie, so what is stored is aggregate counts only. A missing
  user-agent is not a bot (plenty of privacy-preserving clients send none); an explicit
  blank one is. `check.py` step 12 grades it against a hand-built log with known ground
  truth and against the provided crawler's user-agent.

## Already in the repo

- `web-scraping/` implements robots.txt from the crawler's side (exercise 5 is the
  site owner's side).
- `http-server/` (C) builds the server itself; status codes and headers there are the
  lower layer of exercises 1 and 11.
- `system-design/idempotency_keys.py` is the server half of exercise 10.

## Order

1 → 2 → 3 → 5 → 6 → 7 → 4 (crawler and unfurl first: cheapest observers, fastest feedback),
then 8 → 9 → 16 (what users see), then 10 → 11 → 15 (what users do), then 13 → 14 → 12
(law and measurement).

Exercises 5 and 6 are built in that order (robots before sitemap), which swaps them
relative to the first draft: the sitemap is referenced from `robots.txt` and validated
against it, so the file that publishes the reference has to exist first.

## Limits

- **Only the exercises 1-12 checks are built.** The rest are specified, not graded;
  `check.py` reports them as absent rather than pretending they pass. The remaining
  observer, `mobile.py`, does not exist yet, so exercise 9 (responsive on mobile)
  is not graded even though the loading-states exercise (10), the error-messages
  exercise (11), the cookies/consent exercise (13) and the analytics exercise (14) are.
- **The analytics check grades a synthetic log, not live traffic.** `check.py` step 12
  builds a hand-made request log with known ground truth and runs `analytics.count_views`
  over it; it does not wire the counter into the server's request path, so a site that
  never calls it would still pass. The reload signal is the deterministic header stand-in
  (`Cache-Control: no-cache`/`max-age=0`, `Pragma: no-cache`), because a stdlib observer
  cannot see a real refresh server-side. A forged user-agent defeats the bot filter: a
  crawler that sends a browser string is counted as a human, and robots.txt or rate limiting
  is the server-side defence, not this counter's. What the counter stores is aggregate counts
  only — per-path integers and a total, never a user-agent, IP, cookie or timestamp.
- **The error-message check reads the body, not the screenshot.** It submits the
  contact form and asserts the message string the server turns into the field-level
  error is present next to the input, and that the 500 page's body carries none of
  the detail tokens (the detail is asserted in `serve.SERVER_LOG` instead). It does
  not render the page, so a message that is present in the HTML but hidden with CSS
  would still pass; the drawing half belongs to a browser.
- **The loading-state check is structural.** A standard-library observer cannot watch
  the browser paint, so `impatient.py` reads the form's `onsubmit` instead of timing a
  repaint, and `serve.py`'s simulated `ORDER_DELAY` is `0.0` in the tests. Grade a real
  repaint with a browser (exercise 16's territory), not here.
- **Idempotency is graded sequentially.** `impatient.py`'s clicks are serial, so a server
  that records under a lock and one that records without one pass alike; the check does
  not exercise a true race. The reference guards `ORDERS`/`SEEN` with a lock anyway,
  because a real double click can be concurrent.
- **The cookie check uses a stateless observer.** `visit.py`/`impatient.py` keep no cookie
  jar, so the consent check grades the accept response's own `Set-Cookie` rather than a
  follow-up request that carries the stored choice; a server that records consent and only
  sets the cookie on the next request would fail. `post_form_headers` does not follow
  redirects, so the graded headers are the endpoint's; a cookie line is live only with a real
  value, no `Max-Age<=0`, and no past `Expires`, and when a name appears twice the last line
  wins (as a browser applies them). It visits every crawled page and allows only
  `serve.SESSION_COOKIE`, so "strictly necessary" is the reference's one session cookie, not
  a general judgment of necessity; and it counts two controls, not their visual weight, so a
  third same-value button would not be flagged as a dark pattern. The controls may be
  `<button type="submit">` or `<input type="submit">`; a `type=button`, a `disabled` control,
  a control in a disabled `fieldset`, or one with no visible label is rejected. A
  client-side route to a cookie setter (a `<meta http-equiv="refresh">`, JavaScript) is out
  of scope: the observer follows neither.
- The crawler is a single-threaded stdlib fetcher. It follows same-origin links only and
  does not execute JavaScript, so a client-rendered site would be measured wrong.
- Soft-404 detection probes one invented path per host. A site that 404s some paths but
  rewrites others to 200 needs more probes than this makes.
- Graded against the local reference and broken servers, never the network: the numbers
  are the toy server's, not a real site's.
- The title and description length limits (60 and 160 characters) are conventions, not
  hard rules; they are graded so a learner can see a page cross the line, not because a
  longer one is wrong.
