"""
Page-view counting a launch can trust.

WHAT IT IMPLEMENTS
    `count_views(records)` turns a request log into the number of page views,
    where a "view" means one human, consenting browser deliberately opening a
    page. A bot, a prefetch, a reload, a static asset, a non-GET request and a
    visitor who never accepted analytics are not views, and are dropped before
    they are ever counted.

DESIGN DECISION - a view is filtered, not merely logged.
    The naive count is `len(records)`: every request that carried a path. That
    number is wrong in five ways at once. It counts search-engine crawlers (a
    busy bot can outnumber humans), it counts speculative prefetches the
    browser issued before the user arrived, it counts the same person twice
    when they hit reload, it counts CSS and images as though they were pages,
    and it counts everyone who never agreed to be measured. Each is a named
    case below; `count_views` exists so the number means exactly one thing.

DESIGN DECISION - bots are recognised by a marker in the user-agent, not by an
    allow-list of known names. `BOT_MARKERS` covers the common web crawlers
    (`bot`, `spider`, `crawl`, `slurp`) and the traffic that pretends to be a
    browser but is not (`headless`, `python-urllib`, `curl`, `wget`). A missing
    user-agent (`None`) is NOT a bot: plenty of real, privacy-preserving clients
    send none, and dropping them would under-count humans. An empty string, by
    contrast, is a client that chose to say nothing, and is treated as a bot.
    The honest limit: a determined crawler can forge a browser user-agent and
    evade this. Defence in depth (robots.txt, rate limits) is a server-side
    concern, not this counter's.

DESIGN DECISION - prefetch and reload are read from request headers.
    A speculative `Purpose: prefetch` / `X-Moz: prefetch` never had a human in
    front of it. A reload is genuinely hard to see server-side: the browser
    re-sends the request and nothing distinguishes a refresh from a first
    visit. Since a header is all a stdlib observer can see, `is_reload` uses the
    deterministic stand-in the browser does send on a forced reload -
    `Cache-Control: no-cache` or `max-age=0`, or `Pragma: no-cache`. Grading a
    counter against that header is honest; claiming it is a perfect reload
    signal would not be.

DESIGN DECISION - consent is checked before anything is counted.
    `consented` looks for a non-empty `ANALYTICS_COOKIE` in the request's cookie
    header - the same cookie `serve.py` hands out on `POST /consent` with
    `choice=accept`. No cookie, no count. That is the line between analytics and
    tracking.

DESIGN DECISION - the result stores paths and integers, nothing else.
    The output is `{"views": {path: count}, "total": n}`: aggregate counts only.
    No IP, no user-agent, no cookie, no timestamp reaches it. A count of one
    cannot re-identify anyone, and there is nothing to leak if the database
    does. `demo()` prints the fixed counts next to the naive ones.
"""

from collections import Counter

from pages import ANALYTICS_COOKIE

BOT_MARKERS = (
    "bot", "spider", "crawl", "slurp", "bingpreview",
    "facebookexternalhit", "headless", "python-urllib", "curl", "wget",
)

ASSET_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".css",
    ".js", ".webp", ".woff", ".woff2",
)

# Header values that mean "the browser fetched this speculatively".
_PREFETCH_VALUES = ("prefetch", "preview")


def _header(headers, name):
    """Case-insensitive lookup of one header value, or "" when absent."""
    if not headers:
        return ""
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return value or ""
    return ""


def is_bot(user_agent):
    """True when the user-agent is a crawler, a script, or an explicit blank."""
    # TODO: return True when the user-agent is an explicit blank string or contains any marker from BOT_MARKERS, case-insensitively; a missing user-agent (None) is not a bot
    raise NotImplementedError("is_bot")


def is_prefetch(headers):
    """True when the browser fetched the URL speculatively, not by a human.

    The header may carry several comma/semicolon-separated tokens, so match any
    one of them, not the whole string.
    """
    # TODO: return True when the Purpose, X-Purpose or X-Moz header is a prefetch or preview value
    raise NotImplementedError("is_prefetch")


def is_reload(headers):
    """True on the header a forced reload sends.

    A real reload is invisible server-side - the browser re-sends the request
    and nothing distinguishes it from a first visit - so this deterministic
    header stands in for it: `Cache-Control: no-cache`/`max-age=0` or
    `Pragma: no-cache`.
    """
    # TODO: return True when Cache-Control contains no-cache or max-age=0, or Pragma contains no-cache
    raise NotImplementedError("is_reload")


def consented(cookies):
    """True when the cookie header carries a non-empty analytics cookie."""
    # TODO: return True when the cookie header carries a non-empty ANALYTICS_COOKIE value
    raise NotImplementedError("consented")


def count_views(records):
    """Count deliberate, consented human page views in a request log.

    A record counts only when the method is GET, the path is not a static
    asset, and the request is not a bot, a prefetch, a reload, or unconsented.
    The result is aggregate counts only - paths and integers, no personal data.
    """
    # TODO: keep only GET records whose path is not an asset, whose user-agent is not a bot, that are neither prefetch nor reload, and that carry consent; tally per path and return {"views": {sorted path: int}, "total": int} - stored paths and integers only, no user-agent, IP or cookie
    raise NotImplementedError("count_views")


def demo():
    """Print the fixed counts beside the naive "count every request" counts."""
    human = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Firefox/128.0")
    bot = "Googlebot/2.1 (+http://www.google.com/bot.html)"
    consent = f"{ANALYTICS_COOKIE}=1"

    def record(path, method="GET", user_agent=human, headers=None, cookies=consent):
        return {"path": path, "method": method, "user_agent": user_agent,
                "headers": headers or {}, "cookies": cookies}

    records = [
        record("/"),                                             # view
        record("/"),                                             # view
        record("/", cookies=""),                                 # no consent
        record("/about"),                                        # view
        record("/about", user_agent=bot),                        # bot
        record("/", headers={"Purpose": "prefetch"}),            # prefetch
        record("/about", headers={"Cache-Control": "no-cache"}),  # reload
        record("/assets/site.css"),                              # asset
        record("/pricing"),                                      # view
        record("/", method="POST"),                              # not a GET
    ]

    fixed = count_views(records)
    naive = Counter(record["path"] for record in records)
    excluded = Counter()
    for request in records:
        path = (request.get("path") or "").lower()
        if path.endswith(ASSET_EXTENSIONS):
            excluded["asset"] += 1
        if is_bot(request.get("user_agent")):
            excluded["bot"] += 1
        headers = request.get("headers") or {}
        if is_prefetch(headers):
            excluded["prefetch"] += 1
        if is_reload(headers):
            excluded["reload"] += 1
        if not consented(request.get("cookies")):
            excluded["no consent"] += 1

    print("naive (count every request):")
    for path in sorted(naive):
        print(f"    {path:<20} {naive[path]}")
    print(f"    {'TOTAL':<20} {sum(naive.values())}")
    print("fixed (count human, consented views):")
    for path in sorted(fixed["views"]):
        print(f"    {path:<20} {fixed['views'][path]}")
    print(f"    {'TOTAL':<20} {fixed['total']}")
    print("excluded requests:")
    for reason in ("bot", "prefetch", "reload", "no consent", "asset"):
        print(f"    {reason:<20} {excluded[reason]}")


if __name__ == "__main__":
    demo()
