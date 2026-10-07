# Web launch checklist, from the failure side

Sixteen items that "every site should have before launch". The usual list says *what*;
these exercises make you find out *why*, by putting an observer in front of a site that
lacks the item and measuring the damage, then fixing it and measuring again.

**Status: exercises 1-3 are built.** `crawler.py` (the observer), `check.py`, the
reference in `solutions/` and a runnable broken variant in `_build/broken/` are
here. Exercises 4-16 and the other observers are still specified only. No conceptual
answers are written anywhere in this directory, on purpose: each exercise ends with
questions, and the observer's output is what answers them.

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

Only `crawler.py` exists today; the rest are specified in the exercises below.

`check.py` runs the observers and grades each exercise, in this repo's usual format.
Exercises 1-3 are graded now; the rest are TODO until their observers exist.

Runs on a CPU: Python standard library only for exercises 1-3. Later exercises warm
up the machine (Pillow with WebP, a Chromium binary) but there is no network.

## What is provided, what you build

The original plan was ambiguous about this. The smallest workable split:

| Part | Who | Why |
|---|---|---|
| `crawler.py` | **provided** | An observer is a measuring instrument; you would not learn the exercise by re-implementing the ruler. Read it, do not edit it. |
| `check.py` | **provided** | The grader. Never imports `solutions/`. |
| `serve.py` | **you** | Routing and the 404 status: the decision exercise 1 is about. |
| `pages.py` | **you** | The site's HTML: titles and descriptions, the subject of exercises 2 and 3. |
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
python3 check.py --all    # run all three
```

Start the reference site (swap `solutions` for `_build/broken` for the broken
variant), then crawl it by hand to see what a bot sees:

```
(cd solutions && python3 serve.py) &                 # http://127.0.0.1:8000/
python3 crawler.py http://127.0.0.1:8000/            # the report
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
- **Questions:** How many requests did a browser make that you never linked to? What does
  each one cost the server when it returns your custom 404 page from exercise 1?

### 5. robots.txt
- **Break, twice.** (a) Deploy the staging `robots.txt` that disallows everything. (b) Hide
  `/admin` by listing it in `robots.txt`.
- **Fix:** write the parser the crawler uses (longest-match `Allow`/`Disallow`, user-agent
  groups), then a `robots.txt` that does what you mean.
- **Check:** the parser agrees with the observer on a table of tricky rules; production
  allows crawling; nothing secret appears in the file.
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

## Mutation table (exercises 1-3)

`_build/mutations.py`, run through
`.claude/skills/graded-module/scripts/mutate.py`, plants one classic mistake per
exercise. Every one must be CAUGHT by the named step.

| Planted bug | File | Caught by | Why it is a classic mistake |
|---|---|---|---|
| Unknown path answered with status 200 | `serve.py` | step 1 | The soft 404: a bot indexes a deleted URL forever. |
| Every page uses the home page's `<title>` | `pages.py` | step 2 | Copy-paste the layout, forget the title: ten identical tabs. |
| The description tag is never emitted | `pages.py` | step 3 | The snippet silently falls back to an arbitrary sentence. |

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

## Already in the repo

- `web-scraping/` implements robots.txt from the crawler's side (exercise 5 is the
  site owner's side).
- `http-server/` (C) builds the server itself; status codes and headers there are the
  lower layer of exercises 1 and 11.
- `system-design/idempotency_keys.py` is the server half of exercise 10.

## Order

1 → 2 → 3 → 6 → 5 → 7 → 4 (crawler and unfurl first: cheapest observers, fastest feedback),
then 8 → 9 → 16 (what users see), then 10 → 11 → 15 (what users do), then 13 → 14 → 12
(law and measurement).

## Limits

- **Only exercises 1-3 are built.** The rest are specified, not graded; `check.py`
  reports them as absent rather than pretending they pass. The remaining observers
  (`unfurl.py`, `reader.py`, `mobile.py`, `visit.py`, `impatient.py`) do not exist yet.
- The crawler is a single-threaded stdlib fetcher. It follows same-origin links only and
  does not execute JavaScript, so a client-rendered site would be measured wrong.
- Soft-404 detection probes one invented path per host. A site that 404s some paths but
  rewrites others to 200 needs more probes than this makes.
- Graded against the local reference and broken servers, never the network: the numbers
  are the toy server's, not a real site's.
- The title and description length limits (60 and 160 characters) are conventions, not
  hard rules; they are graded so a learner can see a page cross the line, not because a
  longer one is wrong.
