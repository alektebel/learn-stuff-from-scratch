# Web launch checklist, from the failure side

Fifteen items that "every site should have before launch". The usual list says *what*;
these exercises make you find out *why*, by putting an observer in front of a site that
lacks the item and measuring the damage, then fixing it and measuring again.

**Status: planned.** The exercises below are specified; the graded module (observers and
`check.py`) is not built yet. No answers are written anywhere in this directory, on purpose:
each exercise ends with questions, and the observer's output is what answers them.

## How it will work

You build a small site: `site/` (HTML, CSS, images) served by `serve.py`, a stdlib
`http.server` with routing. You do not get a framework, because frameworks do half of this
list silently, and then you never learn which half.

The **observers** are provided. Each one sees the site the way some real agent does:

| Observer | Plays the role of | Measures |
|---|---|---|
| `crawler.py` | a search-engine bot | status codes, titles, descriptions, robots.txt rules, sitemap, link graph |
| `unfurl.py` | a chat app turning a pasted link into a preview card | what the card shows |
| `reader.py` | a screen reader linearising the page | the text a blind user hears |
| `mobile.py` | a phone, through headless Chromium at 375 px | horizontal overflow, text size, tap targets |
| `visit.py` | a browser on a first visit over a slow network | requests made, bytes transferred, cookies set and when |
| `impatient.py` | a user on a slow API who clicks twice | duplicate submissions, what they saw while waiting |

`check.py` runs the observers and grades each exercise, in this repo's usual format.

Runs on a CPU: Python standard library, Pillow (with WebP) and the Chromium binary that
is already installed. No network.

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
