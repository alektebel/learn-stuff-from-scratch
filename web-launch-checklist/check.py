"""
Progress checker for the web launch checklist, exercises 1-3.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 2         # run only step 2
    python3 check.py 1 3       # run steps 1 through 3
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that
is simply the next thing to write. Nothing here imports solutions/. It tests YOUR
`serve.py` and `pages.py` by starting a server and crawling it with the provided
`crawler.py`, exactly as a search bot would.
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


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("serve.py", "unknown paths return a real 404 page that links home", check_custom_404),
    ("pages.py", "every page has a unique <title> within the length limit", check_titles),
    ("pages.py", "every page has a <meta description> within snippet length", check_descriptions),
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
    print(f"\n{BOLD}Web launch checklist — progress check (exercises 1-3){RESET}")
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
