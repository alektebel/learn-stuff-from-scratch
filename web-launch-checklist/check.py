"""
Progress checker for the web launch checklist, exercises 1-8.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 2         # run only step 2
    python3 check.py 1 3       # run steps 1 through 3
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that
is simply the next thing to write. Nothing here imports solutions/. It tests YOUR
`serve.py` and `pages.py` by starting a server and observing it with the provided
`crawler.py` (a search bot), `unfurl.py` (a chat app building a preview),
`visit.py` (a browser's first visit, implicit favicon and all) and `reader.py`
(a screen reader linearising the page).
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


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("serve.py", "unknown paths return a real 404 page that links home", check_custom_404),
    ("pages.py", "every page has a unique <title> within the length limit", check_titles),
    ("pages.py", "every page has a <meta description> within snippet length", check_descriptions),
    ("serve.py/pages.py", "robots.txt allows the public site and names no secret", check_robots),
    ("pages.py", "sitemap.xml is valid, complete and fetches 200", check_sitemap),
    ("pages.py/serve.py", "the unfurled card shows the page title, description and an absolute, real image", check_open_graph),
    ("pages.py/serve.py", "every page points at a real favicon the browser can fetch", check_favicon),
    ("pages.py", "images carry alt text, decorative ones are silent", check_alt_text),
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
    print(f"\n{BOLD}Web launch checklist — progress check (exercises 1-8){RESET}")
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
