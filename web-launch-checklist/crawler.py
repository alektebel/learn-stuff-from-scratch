"""
crawler.py — the provided observer. Plays the role of a search-engine bot.

It fetches a running site over HTTP and reports what a bot would see: status
codes, `<title>`, `<meta name="description">`, the internal link graph,
`robots.txt`, `sitemap.xml`, and — the important one for exercise 1 — soft 404s.

A soft 404 is a response with status 200 whose body is a "not found" page (or the
home page). A bot indexes it as a real page: the deleted URL stays in the index
forever. The observer detects it by requesting a path that certainly does not
exist and checking the status: 404 is a real 404, 200 is a soft one.

This file is infrastructure, not the exercise. Do not edit it; read it. It is
also copied into `solutions/` as a symlink so the mutation harness can take it
along.

Standard library only. No network beyond 127.0.0.1.
"""

import http.client  # noqa: F401  (kept for readers who expect it below)
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

# What the observer "displays": a title longer than this is truncated in the
# results list, a description longer than this is cut in the snippet.
TITLE_MAX = 60
DESC_MAX = 160

# A path guaranteed to be absent, used to test for soft 404s.
SOFT_404_PROBE = "/this-page-does-not-exist-9f3a"

USER_AGENT = "web-launch-checklist-crawler/1.0"


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def _get(base_url, path):
    """Return (status, body). A 4xx/5xx body is read, not raised."""
    url = base_url.rstrip("/") + (path or "/")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# Parsing one page
# ---------------------------------------------------------------------------

class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = None
        self.description = None
        self.links = []
        self.meta = {}
        self._in_title = False
        self._title_parts = []

    def handle_starttag(self, tag, attrs):
        attr = {key.lower(): value for key, value in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (attr.get("name") or "").lower()
            if name:
                self.meta[name] = attr.get("content")
            if name == "description" and self.description is None:
                self.description = attr.get("content")
        elif tag == "a":
            href = attr.get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
            if self.title is None:
                self.title = "".join(self._title_parts).strip()

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)


class Page:
    """One fetched URL and everything a bot reads from it."""

    def __init__(self, path, status, html):
        self.path = path
        self.status = status
        self.html = html
        parser = _PageParser()
        parser.feed(html)
        parser.close()
        self.title = parser.title
        self.description = parser.description
        self.links = parser.links
        self.meta = parser.meta

    def __repr__(self):
        return f"Page({self.path!r}, status={self.status}, title={self.title!r})"


def fetch(base_url, path):
    """Fetch one path and parse it."""
    status, html = _get(base_url, path)
    return Page(path, status, html)


# ---------------------------------------------------------------------------
# Internal links
# ---------------------------------------------------------------------------

def _internal_path(base_url, from_path, href):
    """Resolve `href` from `from_path`; None if it leaves the site or is not a page."""
    if href.startswith(("mailto:", "tel:", "javascript:", "data:", "#")):
        return None
    target = urllib.parse.urljoin(base_url.rstrip("/") + from_path, href)
    parsed = urllib.parse.urlparse(target)
    base = urllib.parse.urlparse(base_url)
    if parsed.netloc and parsed.netloc != base.netloc:
        return None
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path
    return path.rstrip("/") or "/"


def internal_targets(base_url, page):
    """The internal paths a single page links to."""
    targets = set()
    for href in page.links:
        target = _internal_path(base_url, page.path, href)
        if target:
            targets.add(target)
    return targets


# ---------------------------------------------------------------------------
# robots.txt and sitemap.xml (exercises 5 and 6) — provided, unused by 1-3
# ---------------------------------------------------------------------------

def parse_robots(text):
    """Return {user_agent: [(allow|disallow, path), ...]} preserving order."""
    groups = {}
    agents = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            agents = [value.lower()]
            groups.setdefault(value.lower(), [])
        elif field in ("allow", "disallow") and agents:
            for agent in agents:
                groups[agent].append((field, value))
    return groups


def allowed(groups, path, agent="*"):
    """Longest-match Allow/Disallow. Returns True when the path may be crawled."""
    rules = groups.get(agent.lower(), groups.get("*", []))
    best = None
    for field, value in rules:
        if not value or path.startswith(value):
            if best is None or len(value) >= len(best[1]):
                best = (field, value)
    return best is None or best[0] == "allow"


def sitemap_urls(base_url):
    """Every <loc> in /sitemap.xml, or [] when absent or malformed."""
    status, text = _get(base_url, "/sitemap.xml")
    if status != 200:
        return []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    return [element.text for element in root.iter() if element.tag.endswith("loc")]


# ---------------------------------------------------------------------------
# The crawl
# ---------------------------------------------------------------------------

class Site:
    """The result of a crawl: what a bot would know after visiting the site."""

    def __init__(self, base_url, pages, missing, robots, sitemap):
        self.base_url = base_url
        self.pages = pages
        self.missing = missing
        self.robots = robots
        self.sitemap = sitemap

    @property
    def paths(self):
        return [page.path for page in self.pages if page.status == 200]

    @property
    def soft_404s(self):
        """Pages that came back 200 although they do not exist."""
        return [self.missing] if self.missing.status == 200 else []

    @property
    def link_graph(self):
        return {
            page.path: sorted(internal_targets(self.base_url, page))
            for page in self.pages
            if page.status == 200
        }

    def duplicate_titles(self):
        seen, duplicates = {}, {}
        for page in self.pages:
            if page.status != 200 or not page.title:
                continue
            seen.setdefault(page.title, []).append(page.path)
        for title, paths in seen.items():
            if len(paths) > 1:
                duplicates[title] = paths
        return duplicates


def crawl(base_url, seed="/", max_pages=50):
    """Breadth-first crawl from `seed`, then probe for a soft 404."""
    pages, seen, queue = [], set(), [seed]
    while queue:
        path = queue.pop(0)
        if path in seen or len(seen) >= max_pages:
            continue
        seen.add(path)
        page = fetch(base_url, path)
        pages.append(page)
        if page.status == 200:
            for href in page.links:
                target = _internal_path(base_url, path, href)
                if target and target not in seen:
                    queue.append(target)
    missing = fetch(base_url, SOFT_404_PROBE)
    robots_status, robots_body = _get(base_url, "/robots.txt")
    return Site(base_url, pages, missing, (robots_status, robots_body),
                sitemap_urls(base_url))


def _main():
    import sys

    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    site = crawl(base)
    print(f"crawled {len(site.paths)} pages from {base}")
    for page in site.pages:
        if page.status == 200:
            title = page.title if page.title is not None else "(no title)"
            print(f"  200  {page.path:<12} {len(title):>2} chars  {title}")
    print(f"  {site.missing.status}  {SOFT_404_PROBE}  (soft 404s: {len(site.soft_404s)})")
    for title, paths in site.duplicate_titles().items():
        print(f"  duplicate title {title!r}: {paths}")
    if site.sitemap:
        print(f"  sitemap lists {len(site.sitemap)} URLs")


if __name__ == "__main__":
    _main()
