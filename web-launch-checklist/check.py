"""
Progress checker for the web launch checklist, exercises 1-11.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 2         # run only step 2
    python3 check.py 1 3       # run steps 1 through 3
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that
is simply the next thing to write. Nothing here imports solutions/. It tests YOUR
`serve.py` and `pages.py` by starting a server and observing it with the provided
`crawler.py` (a search bot), `unfurl.py` (a chat app building a preview),
`visit.py` (a browser's first visit, implicit favicon and all), `reader.py`
(a screen reader linearising the page) and `impatient.py` (a user who clicks a
slow order form too many times, and whose HTTP helpers this checker reuses to
submit the contact form, read the 500 page, and read the consent response's
`Set-Cookie` headers).
"""

import shutil
import sys
import threading
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
shutil.rmtree(Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


class _RunningSite:
    """Start the learner's server in a thread; yield its base URL; shut it down."""

    def __enter__(self):
        from serve import make_server

        self.server = make_server(port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


def _duplicates(pairs):
    """{value: [keys]} for values that appear more than once."""
    seen = {}
    for path, value in pairs.items():
        seen.setdefault(value, []).append(path)
    return {value: paths for value, paths in seen.items() if len(paths) > 1}


# ---------------------------------------------------------------------------
# Step 1: a custom 404 page
# ---------------------------------------------------------------------------

def check_custom_404():
    from crawler import SOFT_404_PROBE, crawl, fetch, internal_targets

    with _RunningSite() as base:
        site = crawl(base)
        missing = site.missing
        assert missing.status == 404, (
            f"an unknown path ({SOFT_404_PROBE}) returned status {missing.status}, not 404. "
            "The server is serving a page for a path that does not exist: that is a soft 404, "
            "and a bot will index it. Route unknown paths to the 404 page with a real 404 status.")
        assert not site.soft_404s, f"soft 404s detected: {[p.path for p in site.soft_404s]}"
        assert "/" in internal_targets(base, missing), (
            "the 404 page does not link back to the home page (expected href=\"/\"). "
            "A dead end gives a lost visitor no way forward.")
        deleted = fetch(base, "/old-news")
        assert deleted.status == 404 and "/old-news" not in site.paths, (
            f"a deleted page (/old-news) came back {deleted.status}: deleted pages must drop "
            "out of the crawler's index, not answer as if they still exist.")


# ---------------------------------------------------------------------------
# Step 2: a unique, bounded meta title on every page
# ---------------------------------------------------------------------------

def check_titles():
    from crawler import TITLE_MAX, crawl

    with _RunningSite() as base:
        site = crawl(base)
        pages = [page for page in site.pages if page.status == 200]
        assert pages, "the crawler found no page: does the home page exist and link anywhere?"
        untitled = [page.path for page in pages if not page.title]
        assert not untitled, (
            f"pages without a <title>: {untitled}. A browser tab, a bookmark and a search "
            "result all show the title; without one the crawler invents a snippet.")
        duplicates = site.duplicate_titles()
        assert not duplicates, (
            "these pages share a <title>: "
            + "; ".join(f"{v!r} -> {p}" for v, p in duplicates.items())
            + ". With ten tabs open the user cannot tell the pages apart.")
        too_long = [(page.path, len(page.title)) for page in pages if len(page.title) > TITLE_MAX]
        assert not too_long, (
            f"titles longer than {TITLE_MAX} characters: {too_long}. The results list truncates "
            "them, so the end of the title is never seen.")


# ---------------------------------------------------------------------------
# Step 3: a meta description on every page, within snippet length
# ---------------------------------------------------------------------------

def check_descriptions():
    from crawler import DESC_MAX, crawl

    with _RunningSite() as base:
        site = crawl(base)
        pages = [page for page in site.pages if page.status == 200]
        assert pages, "the crawler found no page: does the home page exist and link anywhere?"
        missing = [page.path for page in pages if not page.description]
        assert not missing, (
            f"pages without a <meta name=\"description\">: {missing}. Without one the crawler "
            "takes an arbitrary sentence from the body as the snippet.")
        too_long = [(page.path, len(page.description)) for page in pages
                    if len(page.description) > DESC_MAX]
        assert not too_long, (
            f"descriptions longer than {DESC_MAX} characters: {too_long}. The snippet is cut "
            "at that length, so the end of the description is never read.")


# ---------------------------------------------------------------------------
# Step 4: robots.txt allows the public site and names no secret
# ---------------------------------------------------------------------------

def check_robots():
    from crawler import allowed, crawl, parse_robots

    with _RunningSite() as base:
        site = crawl(base)
        status, body = site.robots
        assert status == 200, (
            f"/robots.txt returned status {status}, not 200. A bot reads it to learn the "
            "rules; a missing file means the site never said what it wanted crawled.")
        groups = parse_robots(body)
        blocked = [path for path in site.paths if not allowed(groups, path)]
        assert not blocked, (
            f"robots.txt disallows public pages: {blocked}. Production must allow crawling "
            "the public site (`User-agent: *` with `Allow: /`), not push bots away from it.")
        assert "/admin" not in body.lower(), (
            "robots.txt names a secret path (/admin). A Disallow line is an advertisement: "
            "well-behaved bots skip the path and everyone else reads the file as an index. "
            "Access control belongs on /admin itself, not in a public file.")
        assert any(line.strip().lower().startswith("sitemap:") and "/sitemap.xml" in line
                   for line in body.splitlines()), (
            "robots.txt has no `Sitemap:` line pointing at /sitemap.xml. The sitemap is "
            "found efficiently only because robots.txt names it.")


# ---------------------------------------------------------------------------
# Step 5: sitemap.xml is valid, complete and fetches 200
# ---------------------------------------------------------------------------

def check_sitemap():
    import xml.etree.ElementTree as ET
    from urllib.parse import urlparse

    from crawler import allowed, crawl, fetch, parse_robots
    from pages import sitemap_xml

    with _RunningSite() as base:
        site = crawl(base)
        assert site.sitemap, (
            "/sitemap.xml yielded no URLs: it is absent, not status 200, or not well-formed "
            "XML. An unparseable sitemap is worse than none at all - the bot reads it and "
            "finds nothing.")
        listed = list(site.sitemap)
        missing = [base + path for path in site.paths if base + path not in listed]
        assert not missing, (
            f"pages the sitemap does not list: {missing}. The sitemap is the site's full "
            "public surface, including any page the navigation never links to.")
        for loc in listed:
            page = fetch(base, urlparse(loc).path)
            assert page.status == 200, (
                f"the sitemap lists {loc}, which returned status {page.status}. A sitemap "
                "full of 404s teaches the bot to distrust every URL in it.")

        # Cross-check against the served robots.txt: a sitemap must not advertise a URL
        # the site tells bots to skip. This catches a page that is unlinked (so the crawl
        # never sees it) but disallowed.
        robots_status, robots_body = site.robots
        robots_groups = parse_robots(robots_body) if robots_status == 200 else {}
        disallowed = [loc for loc in listed
                      if not allowed(robots_groups, urlparse(loc).path or "/")]
        assert not disallowed, (
            f"the sitemap lists URLs that robots.txt disallows: {disallowed}. The sitemap "
            "and robots.txt must agree; do not submit to the bot a URL you told it to skip.")

        raw = fetch(base, "/sitemap.xml")
        root = ET.fromstring(raw.html)
        for url in [e for e in root.iter() if e.tag.endswith("url")]:
            lastmod = [e.text for e in url if e.tag.endswith("lastmod")]
            assert lastmod and lastmod[0] and lastmod[0].strip(), (
                "a <url> in the sitemap has no non-empty <lastmod>. Without a date the bot "
                "cannot tell how fresh the page is.")

        generated = sitemap_xml(["/", "/orphan"], base)
        orphan_root = ET.fromstring(generated)
        locs = {e.text for e in orphan_root.iter() if e.tag.endswith("loc")}
        for wanted in (base + "/", base + "/orphan"):
            assert wanted in locs, (
                f"sitemap_xml([\"/\", \"/orphan\"]) does not list {wanted}. The generator "
                "must include every path it is given, linked from the navigation or not.")


# ---------------------------------------------------------------------------
# Step 6: Open Graph tags so a chat app unfurls a preview card
# ---------------------------------------------------------------------------

def check_open_graph():
    from crawler import fetch
    from unfurl import unfurl

    with _RunningSite() as base:
        card = unfurl(base, "/")
        assert not card.problems, (
            "the card for / has problems: " + "; ".join(card.problems)
            + ". The site must carry Open Graph tags for its title, description and image, "
            "and the image must be an absolute URL to a real image the server serves.")

        page = fetch(base, "/")
        assert card.title, (
            "the card shows no title: the page has no usable `og:title`. A chat app "
            "pasting the link shows the URL alone instead of a named card.")
        assert card.title == page.title, (
            f"the card title {card.title!r} does not match the page <title> {page.title!r}. "
            "`og:title` must repeat the page's real title, not a hard-coded one, or every "
            "shared link is mislabelled.")
        assert card.description == page.description, (
            f"the card description {card.description!r} does not match the page's meta "
            f"description {page.description!r}. `og:description` is what the chat app shows "
            "under the title; it must come from the page.")

        assert card.image and card.image.startswith("http"), (
            f"og:image is {card.image!r}, not an absolute http(s) URL. A chat app rendering "
            "the card later has no page to resolve a relative path against, so the image "
            "silently disappears.")
        assert card.image_content_type.startswith("image/"), (
            f"the og:image was served as {card.image_content_type!r}, not an image type. "
            "Browsers and unfurlers trust the content type; an HTML page in an <img> shows "
            "a broken-image icon.")
        assert card.image_width >= 600 and card.image_height >= 315, (
            f"the og:image measures {card.image_width}x{card.image_height}; a preview card "
            "wants at least 600x315 (the 1.91:1 ratio), or the picture is upscaled or cropped.")
        assert 0 < card.image_bytes <= 5 * 1024 * 1024, (
            f"the og:image is {card.image_bytes} bytes. It must be non-empty and at most "
            "5 MB: a huge image delays the card or makes the chat app skip it.")

        about = unfurl(base, "/about")
        assert about.title != card.title, (
            f"the / and /about cards share the title {card.title!r}. Each page must pass its "
            "own path to the tags, so its card describes that page and not the home page.")
        assert about.url and about.url.rstrip("/").endswith("/about"), (
            f"the /about card's og:url is {about.url!r}, which does not point at /about. "
            "The page's own path has to reach the tag helper; a default path makes every "
            "card claim to be the home page.")
        assert about.image and about.image.startswith("http"), (
            f"the /about card's og:image is {about.image!r}, not absolute. Every page needs "
            "the same absolute image URL.")


# ---------------------------------------------------------------------------
# Step 7: a favicon the browser can fetch
# ---------------------------------------------------------------------------

def check_favicon():
    import re

    from visit import ICON_SIZES, measure_icon, visit

    wanted = " or ".join(f"{w}x{h}" for w, h in ICON_SIZES)
    with _RunningSite() as base:
        result = visit(base, ["/", "/about"])
        icons = [r for r in result.requests if r.path.rstrip("/") == "/favicon.ico"]
        assert icons, (
            "a browser's first visit produced no request for /favicon.ico. The exercise "
            "asks for the icon at that path: the browser guesses it for every page that "
            "declares no link, and the link must point at it. Every page must also carry "
            "a `<link rel=\"icon\" ...>`.")
        icon = icons[0]
        assert icon.status == 200, (
            f"the icon request {icon.path!r} returned status {icon.status}, not 200. The "
            "tab shows a broken-image glyph, and every one of those requests pays for a "
            "full custom 404 page.")
        assert icon.content_type.startswith("image/"), (
            f"the icon was served as {icon.content_type!r}, not an image type. Browsers "
            "trust the content type and refuse to render it as an icon.")
        width, height, fmt = measure_icon(icon.body)
        print(f"      {GREY}icon {icon.path} (linked={icon.from_link}): "
              f"{width}x{height} {fmt}{RESET}")
        assert (width, height) in ICON_SIZES, (
            f"the icon measures {width}x{height}, not {wanted}. A browser only uses a "
            "favicon at one of the sizes it asks for; anything else is scaled to a blur "
            "or ignored.")

        for path in result.pages:
            page = next((r for r in result.requests
                         if r.path == path and not r.from_link), None)
            assert page is not None, f"the visit recorded no response for {path}"
            html_text = page.body.decode("utf-8", "replace")
            tags = re.findall(r"<link\b[^>]*>", html_text, re.IGNORECASE)
            icon_tags = [t for t in tags
                         if re.search(r'rel\s*=\s*"[^"]*\bicon\b', t, re.IGNORECASE)]
            assert icon_tags, (
                f"{path} has no `<link rel=\"icon\">`. Without the link the browser "
                "falls back to guessing /favicon.ico; the page never says which icon it "
                "uses.")
            sizes = re.search(r'sizes\s*=\s*"([^"]*)"', icon_tags[0], re.IGNORECASE)
            declared = sizes.group(1).split() if sizes else []
            assert f"{width}x{height}" in declared, (
                f"{path} declares favicon sizes {declared or '(none)'}, but the icon the "
                f"server actually returns is {width}x{height}. A size that does not match "
                "the bytes makes the browser skip the icon or fetch a second one.")


# ---------------------------------------------------------------------------
# Step 8: alt text on every image, and silence for decoration
# ---------------------------------------------------------------------------

def check_alt_text():
    from crawler import crawl
    from reader import read_page

    with _RunningSite() as base:
        # Read every page the crawler can reach, not one sample: a bad alt on a page
        # someone forgot to check is exactly the bug this exercise is about.
        pages = [(path, read_page(base, path)) for path in sorted(crawl(base).paths)]

        warnings = [f"{path}: {warning}"
                    for path, reading in pages for warning in reading.warnings]
        assert not warnings, (
            "the screen reader reports: " + "; ".join(warnings) + ". Every image needs an "
            "alt attribute: a real description on an informative image, alt=\"\" on a "
            "decorative one, and never a file name. A missing alt makes the reader "
            "announce the src file name instead.")

        images = [image for _path, reading in pages for image in reading.images]
        texts = "\n".join(reading.text for _path, reading in pages)

        decorative = [image for image in images if image.has_alt and image.alt == ""]
        assert decorative, (
            "no image carries alt=\"\". A decorative image (a divider, a spacer, a chart "
            "that repeats nearby text) must be explicitly silent, or the screen reader "
            "reads it out as if it carried meaning.")
        for image in decorative:
            assert image.src not in texts, (
                f"the decorative image {image.src!r} is not silent: its src still reaches "
                "the linear text. Decoration must contribute nothing the reader can hear.")

        informative = [image for image in images if image.has_alt and image.alt]
        assert informative, (
            "no image carries a real description. At least one informative image needs a "
            "non-empty alt that describes what it shows (and that is not just its file "
            "name).")
        assert any(image.alt in texts for image in informative), (
            "no informative alt text reaches the linear text. The description must be "
            "part of what the screen reader reads, not only an attribute on the tag.")

        link_images = [image for image in images if image.in_link]
        assert link_images, (
            "no image is the only content of a link. The exercise wants a link whose whole "
            "label is an image, so that image's alt is the only text a screen reader can "
            "announce for the link.")
        assert any(image.has_alt and image.alt for image in link_images), (
            "an image-only link has no accessible name: its alt is missing or empty. With "
            "no text inside the <a>, the alt is the link's label; alt=\"\" leaves a screen "
            "reader announcing only \"link\".")


# ---------------------------------------------------------------------------
# Step 9: one order however many clicks, and the control disables on submit
# ---------------------------------------------------------------------------

def check_loading_state():
    from impatient import get_order_count, impatient, post_order

    with _RunningSite() as base:
        try:
            report = impatient(base, clicks=3)
        except ValueError as exc:
            raise AssertionError(
                f"the order API is not observable: {exc}. GET /orders must report the "
                "recorded count.") from exc

        assert report.attempts and report.attempts[0].key, (
            "the order form ships no idempotency_key. The clicks then carry an empty "
            "key and the server has nothing to dedup on: either every click records, "
            "or an empty-key shortcut merges every user's order into one. The key must "
            "be generated per form view and submitted as a hidden field.")

        # A standard-library observer cannot watch the browser paint: there is no
        # rendering engine here. What it can read is the mechanism that produces
        # the immediate state, so `disable_on_submit` stands in for it.
        assert report.disable_on_submit, (
            "the order form does not disable its submit control when submitted. A "
            "standard-library observer cannot see the browser paint, so this is a "
            "STRUCTURAL check: the form needs an `onsubmit` handler (or a script) "
            "that disables the button the instant it is clicked. Without it, a slow "
            "API leaves the button live and the user clicks again, which is exactly "
            "what puts a second order on the account.")

        recorded = report.orders_after - report.orders_before
        assert recorded == 1, (
            f"three clicks on submit recorded {recorded} order(s), not 1. The three "
            "clicks are one form view sharing one idempotency key: the server must "
            "dedup by that key and answer the repeats with the same confirmation, "
            "without recording again. Deduping by the request body, or only when a "
            "key is present, still lets the repeats through.")

        statuses = [attempt.status for attempt in report.attempts]
        assert all(status == 200 for status in statuses), (
            f"the repeated submissions returned {statuses}, not all 200. A repeat "
            "must be tolerated, not rejected: the client is retrying, not attacking, "
            "and an error would make the user think the first order failed.")

        # The key, not the body, is the identity. Two DIFFERENT keys with the SAME
        # body are two orders: if they collapse, the server is deduping on content.
        before = get_order_count(base)
        post_order(base, "key-A")
        post_order(base, "key-B")
        after = get_order_count(base)
        assert after - before == 2, (
            f"two requests with different idempotency keys and the same body "
            f"recorded {after - before} order(s), not 2. The key is the identity: "
            "deduping on a hash of the body would treat two distinct submissions as "
            "one, silently dropping the second order.")

        for attempt in report.attempts:
            shown = attempt.key[:8] if attempt.key else "(none)"
            print(f"      {GREY}order attempt key={shown} -> {attempt.status} "
                  f"in {attempt.seconds * 1000:.1f} ms{RESET}")


# ---------------------------------------------------------------------------
# Step 10: an invalid form gets a field-level message; a 500 leaks nothing
# ---------------------------------------------------------------------------

_LEAK_SENTINEL_NAME = "WLC_LEAK_PROBE"
_LEAK_SENTINEL_VALUE = "wlc-probe-2f9c-secret"


def check_error_messages():
    import os
    import re

    import serve
    from impatient import fetch, post_form
    from pages import error_message

    # Plant a long, known value so the environment-leak proof is deterministic and does
    # not depend on whatever HOME happens to be on this machine.
    os.environ[_LEAK_SENTINEL_NAME] = _LEAK_SENTINEL_VALUE

    bad_email = "not-an-email"
    valid = {"name": "Ada", "email": "ada@example.com",
             "message": "Please help me launch the site."}
    with _RunningSite() as base:
        # An invalid email is the user's mistake: status 200, the form comes back
        # with what they typed, and the specific message sits next to the field.
        status, body, _content_type = post_form(base, "/contact", {
            "name": valid["name"], "email": bad_email, "message": valid["message"]})
        assert status == 200, (
            f"POST /contact with an invalid email returned {status}, not 200. An "
            "invalid form is the user's mistake, not a request the server failed to "
            "handle: re-render the form with the field-level message and keep 200.")
        expected_email = error_message("email", bad_email)
        assert 'name="email"' in body, (
            "the invalid POST did not re-render the contact form: the email input is "
            "gone, so the user loses the rest of their input and has nothing to fix.")
        assert bad_email in body, (
            "the re-rendered form dropped the submitted email value: the user has to "
            "retype the field they were already editing.")
        assert expected_email in body, (
            f"the invalid email did not produce its field-level message "
            f"{expected_email!r} next to the field. A bare framework error, or a "
            "silent red border, tells the user nothing about what to change.")
        print(f"      {GREY}invalid email -> {expected_email!r}{RESET}")

        # A too-short message gets its OWN message, not the email one: the errors
        # are field-level, so a field that is fine is never blamed.
        status, body, _content_type = post_form(base, "/contact", {
            "name": valid["name"], "email": valid["email"], "message": "x"})
        assert status == 200, (
            f"POST /contact with a too-short message returned {status}, not 200.")
        expected_message = error_message("message", "x")
        assert expected_message in body, (
            f"a too-short message did not produce its own field-level message "
            f"{expected_message!r}. Each field must say what it wants.")
        assert expected_message != expected_email, (
            f"the email and message errors are the same string {expected_message!r}: "
            "one generic message for every field is exactly the framework default "
            "this exercise replaces. Name the field and the fix.")
        assert expected_email not in body, (
            "a too-short message also showed the email error: the messages are not "
            "field-level, so the user is told to fix a field that is fine.")
        print(f"      {GREY}short message  -> {expected_message!r}{RESET}")

        # A valid submission shows no validation error at all.
        status, body, _content_type = post_form(base, "/contact", valid)
        assert status == 200, (
            f"POST /contact with valid input returned {status}, not 200.")
        assert expected_email not in body and expected_message not in body, (
            "a valid submission still showed a validation error: the form rejects "
            "input that is correct.")
        print(f"      {GREY}valid input    -> accepted, no field error{RESET}")

        # A raised exception is the server's mistake: status 500, a generic page a
        # user can act on, and the detail only in SERVER_LOG.
        status, body, _content_type = fetch(base, "/boom")
        assert status == 500, (
            f"GET /boom returned {status}, not 500. A raised exception must surface "
            "as a server error, with the detail kept out of the response.")
        import os
        import re

        leaks = [token for token in ("Traceback", "RuntimeError", "boom", ".py",
                                     "version_info", "environ")
                 if token.lower() in body.lower()]
        version = re.search(r"\b\d+\.\d+\.\d+\b", body)
        if version:
            leaks.append(f"a version number ({version.group(0)})")
        # A real secret on the page is a leak. Scan the sentinel this check plants (so
        # the proof is deterministic) and the values of secret-looking variables;
        # scanning every environment value would flag an ordinary word that merely
        # happens to be one variable's value (e.g. SOME_SERVICE=contact).
        secret_names = re.compile(r"(SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|CREDENTIAL|"
                                  r"AUTH|PRIVATE)", re.IGNORECASE)
        secret_values = {os.environ.get(_LEAK_SENTINEL_NAME, _LEAK_SENTINEL_VALUE)}
        secret_values |= {value for name, value in os.environ.items()
                          if secret_names.search(name) and value and len(value) > 3}
        env_leaks = sorted({value for value in secret_values if value and value in body})
        if env_leaks:
            leaks.append(f"a secret or environment value ({env_leaks[0]!r})")
        assert not leaks, (
            f"the 500 page leaks {leaks}: the traceback, the exception, the request "
            "path, a source path, a version or an environment value reached the user. "
            "Keep the detail in the server log and show a generic page.")
        assert "python" not in body.lower(), (
            "the 500 page leaks a Python version banner. A version tells an attacker "
            "which exploits to try; it belongs in the log, not the page.")
        assert serve.SERVER_LOG, (
            "no exception was logged on the /boom path: the detail the user must not "
            "see still has to reach the server log, or the bug is invisible to the "
            "team.")
        assert "boom" in serve.SERVER_LOG[-1].lower(), (
            "the server log's last entry does not mention the exception raised by "
            "/boom: the catch logged something else, or swallowed the error.")
        print(f"      {GREY}500 page leaks nothing; the log holds the detail{RESET}")


# ---------------------------------------------------------------------------
# Step 11: no analytics cookie before consent; accept sets it, reject does not
# ---------------------------------------------------------------------------

def _consent_form(html_text):
    """The consent form on a page, or None: its method, action and choice buttons.

    Parsed structurally so the check can tell a real, equal, working banner from a
    decorative one: both controls sit in one form that POSTs to /consent; both are
    real submit buttons (not ``type="button"``, not inside a disabled ``fieldset``);
    and both carry a visible label.
    """
    import re

    for form in re.finditer(r"<form\b([^>]*)>(.*?)</form>", html_text,
                            re.IGNORECASE | re.DOTALL):
        attrs, inner = form.group(1), form.group(2)
        if not re.search(r"\bname\s*=\s*[\"']choice[\"']", inner, re.IGNORECASE):
            continue

        def attr(name):
            match = re.search(name + r"\s*=\s*[\"']([^\"']*)[\"']", attrs, re.IGNORECASE)
            return match.group(1).strip() if match else ""

        controls = {}
        fieldset_disabled = []

        def attribute(attrs, name):
            match = re.search(name + r"""\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
                              attrs, re.IGNORECASE)
            if not match:
                return None
            return next(group for group in match.groups() if group is not None).strip()

        token = re.compile(r"<fieldset\b([^>]*)>|</fieldset\s*>"
                           r"|<button\b([^>]*)>(.*?)</button>"
                           r"|<input\b([^>]*)>",
                           re.IGNORECASE | re.DOTALL)
        for event in token.finditer(inner):
            piece = event.group(0).lower()
            if piece.startswith("</fieldset"):
                if fieldset_disabled:
                    fieldset_disabled.pop()
                continue
            if piece.startswith("<fieldset"):
                fieldset_disabled.append(bool(re.search(r"\bdisabled\b",
                                                        event.group(1) or "",
                                                        re.IGNORECASE)))
                continue
            if event.group(4) is not None:  # <input ...>, a void element
                tag, element_attrs, text = "input", event.group(4), ""
            else:  # <button ...>…</button>
                tag, element_attrs, text = "button", event.group(2) or "", event.group(3) or ""
            if not re.search(r"\bname\s*=\s*[\"']choice[\"']", element_attrs,
                             re.IGNORECASE):
                continue

            element_type = attribute(element_attrs, "type")
            if tag == "button":
                element_type = (element_type or "submit").lower()
                label = " ".join(re.sub(r"<[^>]+>", " ", text).split())
            else:
                # An <input> with no type is a text field, not a submit control; its
                # accessible name is the value attribute (what it submits).
                element_type = (element_type or "text").lower()
                label = attribute(element_attrs, "value") or ""
            control_value = (attribute(element_attrs, "value") or "").lower()
            if control_value in ("accept", "reject"):
                controls[control_value] = {
                    "type": element_type,
                    "disabled": bool(re.search(r"\bdisabled\b", element_attrs,
                                               re.IGNORECASE))
                    or any(fieldset_disabled),
                    "label": label,
                }
        return {"method": attr("method").lower(), "action": attr("action"),
                "controls": controls}
    return None


def _live_cookie_value(cookies, name):
    """The last live value of cookie ``name`` across a list of Set-Cookie lines.

    A browser applies every ``Set-Cookie`` line and keeps the last one, so a dead
    line only wins if it is the last for that name. None when no line leaves the
    cookie live: absent, or every matching line is empty or already dead
    (``Max-Age`` at or below zero, or an ``Expires`` moment in the past).
    """
    import datetime
    import email.utils
    import re

    now = datetime.datetime.now(datetime.timezone.utc)
    result = None
    for cookie in cookies:
        match = re.match(r"\s*" + re.escape(name) + r"\s*=\s*([^;]*)", cookie)
        if not match:
            continue
        value = match.group(1).strip()
        dead = not value
        if not dead:
            max_age = re.search(r"max-age\s*=\s*(-?\d+)", cookie, re.IGNORECASE)
            if max_age and int(max_age.group(1)) <= 0:
                dead = True
        if not dead:
            expires = re.search(r"expires\s*=\s*([^;]+)", cookie, re.IGNORECASE)
            if expires:
                try:
                    when = email.utils.parsedate_to_datetime(expires.group(1).strip())
                except (TypeError, ValueError):
                    when = None
                if when is not None:
                    if when.tzinfo is None:
                        when = when.replace(tzinfo=datetime.timezone.utc)
                    if when <= now:
                        dead = True
        result = None if dead else value
    return result


def check_cookies():
    from crawler import crawl
    from urllib.parse import urlsplit

    import serve
    from impatient import fetch, post_form_headers
    from visit import visit

    with _RunningSite() as base:
        # Before the visitor has chosen anything, no non-essential cookie may be
        # set. Visit EVERY page (analytics can be loaded on any of them), and allow
        # only the strictly necessary session cookie.
        before = visit(base, sorted(crawl(base).paths))
        allowed = {serve.SESSION_COOKIE}
        extra = sorted(set(before.cookies) - allowed)
        names = ", ".join(sorted(before.cookies)) or "(none)"
        assert not extra, (
            f"a plain GET before any consent set non-essential cookie(s) {extra} "
            f"(cookies seen: {names}). Only the strictly necessary session cookie "
            "may be set before the visitor chooses; loading analytics on any page "
            "view is exactly the tracking this exercise removes.")
        print(f"      {GREY}cookies before any choice: {names}{RESET}")

        # The banner offers both choices as the SAME kind of working control inside
        # one form that submits the choice. Rejecting must be as easy as accepting.
        _status, home, _content_type = fetch(base, "/")
        banner = _consent_form(home)
        assert banner is not None, (
            "the home page has no consent form: a <form> with two name=\"choice\" "
            "controls. The banner must let the visitor accept or reject analytics.")
        assert banner["method"] == "post", (
            f"the consent form uses method {banner['method']!r}, not post. The choice "
            "has to reach the server, which records the consent.")
        assert urlsplit(banner["action"]).path == "/consent", (
            f"the consent form posts to {banner['action']!r}, not /consent.")
        for choice in ("accept", "reject"):
            control = banner["controls"].get(choice)
            assert control, (
                f"the consent banner has no {choice} control. Rejecting must be "
                "offered with the same one click as accepting, not hidden behind a "
                "settings page or omitted entirely.")
            assert not control["disabled"], (
                f"the {choice} control is disabled: a control the visitor cannot use "
                "is not a choice.")
            assert control["type"] == "submit", (
                f"the {choice} control is type={control['type']!r}, not a submit "
                "button. A button that does not submit the form does not record the "
                "choice; both choices must work with one click and no JavaScript.")
            assert control["label"], (
                f"the {choice} control has no visible label. Both choices must be "
                "named so the visitor knows what each does.")
        print(f"      {GREY}consent form: post /consent, "
              f"accept={banner['controls']['accept']['label']!r} "
              f"reject={banner['controls']['reject']['label']!r}{RESET}")

        # Accept hands the browser a LIVE analytics cookie. The observer has no
        # cookie jar, so a follow-up visit() cannot remember the choice; what is
        # graded is the accept response's own Set-Cookie, and it must be live. See
        # the README's limits for what a stateless observer cannot check.
        _status, _body, headers = post_form_headers(
            base, "/consent", {"choice": "accept"})
        accept_cookies = list(headers.get_all("Set-Cookie") or []) if headers else []
        value = _live_cookie_value(accept_cookies, serve.ANALYTICS_COOKIE)
        assert value, (
            f"POST /consent choice=accept did not set a live analytics cookie "
            f"(Set-Cookie: {accept_cookies}). Accepting must record consent by "
            "issuing the non-essential cookie with a real value, not an empty or "
            "already-expired one.")
        print(f"      {GREY}accept -> {serve.ANALYTICS_COOKIE}={value}{RESET}")

        # Reject must leave no LIVE non-essential cookie — not just the analytics
        # one. An explicit clear (an empty or already-dead value) of a cookie the
        # visitor never had is harmless; any live non-session cookie is not, and a
        # browser applies the last Set-Cookie line.
        _status, _body, headers = post_form_headers(
            base, "/consent", {"choice": "reject"})
        reject_cookies = list(headers.get_all("Set-Cookie") or []) if headers else []
        names = {cookie.split("=", 1)[0].strip()
                 for cookie in reject_cookies if "=" in cookie}
        live_extras = sorted(name for name in names
                             if name and name != serve.SESSION_COOKIE
                             and _live_cookie_value(reject_cookies, name) is not None)
        assert not live_extras, (
            "POST /consent choice=reject still handed the visitor live non-essential "
            f"cookie(s) {live_extras} (Set-Cookie: {reject_cookies}). Recording a "
            "refusal is not consent: rejecting must leave no analytics or tracking "
            "cookie, whatever its name.")
        print(f"      {GREY}reject -> analytics cookie absent{RESET}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("serve.py", "unknown paths return a real 404 page that links home", check_custom_404),
    ("pages.py", "every page has a unique <title> within the length limit", check_titles),
    ("pages.py", "every page has a <meta description> within snippet length", check_descriptions),
    ("serve.py/pages.py", "robots.txt allows the public site and names no secret", check_robots),
    ("pages.py", "sitemap.xml is valid, complete and fetches 200", check_sitemap),
    ("pages.py/serve.py", "the unfurled card shows the page title, description and an absolute, real image", check_open_graph),
    ("pages.py/serve.py", "every page points at a real favicon the browser can fetch", check_favicon),
    ("pages.py", "images carry alt text, decorative ones are silent", check_alt_text),
    ("pages.py/serve.py", "a double submit records one order and the control disables on submit", check_loading_state),
    ("pages.py/serve.py", "invalid input gets a field-level message; a 500 leaks nothing", check_error_messages),
    ("pages.py/serve.py", "no analytics cookie before consent; accept sets it, reject does not", check_cookies),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}Web launch checklist — progress check (exercises 1-11){RESET}")
    print(f"{GREY}implement serve.py and pages.py, then run the observers{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<9} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<9} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<9} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — the crawler sees a launchable site.{RESET}")
        print(f"  {GREY}Run crawler.py against it, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}Stuck? Read the docstrings, then solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
