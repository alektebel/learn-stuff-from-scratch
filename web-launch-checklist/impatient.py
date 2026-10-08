"""
impatient.py — the provided observer. Plays the role of a user on a slow API
who clicks "Place order" three times because nothing changed on screen.

A form that gives no immediate feedback invites a second click; a control that
stays enabled invites a third; a server that records every request turns one
intent into three orders and one charge. This observer measures all three: what
the page says the instant the user submits, how long each submission took, and
how many orders the server actually recorded. It is the measuring instrument for
exercise 10; read it, do not edit it. It is symlinked into `solutions/` so the
mutation harness can carry it.

DESIGN DECISION - the immediate visual state is graded STRUCTURALLY, because a
    stdlib observer cannot watch the browser paint. There is no rendering engine
    here (no Chromium, no network), so the observer cannot photograph the button
    after a click. What it can read is the mechanism that produces the immediate
    state: the form's `onsubmit` handler (or a script) disabling the submit
    control. `disable_on_submit` is therefore a structural stand-in for "the user
    sees feedback within 100 ms", and `check.py` says so in its failure message.
    Measuring the real paint would need a browser and is out of scope for a
    standard-library-only exercise.

DESIGN DECISION - the repeat is a multi-click on ONE rendered form, so every
    submission carries the same idempotency key. A form view mints one key and
    the three clicks reuse it; that is what makes the server able to collapse
    them into one order. If the form ships no key, the observer sends an empty
    one, and a server that only dedups non-empty keys records every click - which
    is exactly the missing-key bug the mutation harness plants.

DESIGN DECISION - orders are counted by asking the server, not by trusting the
    response. Each POST returns a confirmation, but a second POST can answer
    "already recorded" and still be a lie about the total. The observer reads
    `/orders` before and after, so the count is the server's own state, and the
    difference is what the user's clicks actually did.

Standard library only (`urllib.request`, `urllib.parse`, `html.parser`, `re`,
`argparse`, `json`, `time`). No network beyond the server it is given.
"""

import argparse
import html.parser
import json
import re
import time
import urllib.parse
import urllib.request

USER_AGENT = "web-launch-checklist-impatient/1.0"

# The form field the server reads the idempotency key from.
KEY_FIELD = "idempotency_key"


class Attempt:
    """One POST of the order form: the key it carried, its status and how long."""

    def __init__(self, key, status, seconds, body):
        self.key = key
        self.status = status
        self.seconds = seconds
        self.body = body


class Report:
    """What the impatient session saw: the clicks, the orders, the control."""

    def __init__(self, attempts, orders_before, orders_after,
                 disable_on_submit, button_label):
        self.attempts = attempts
        self.orders_before = orders_before
        self.orders_after = orders_after
        self.disable_on_submit = disable_on_submit
        self.button_label = button_label


class Form:
    """The pieces of the order form the observer needs to drive it."""

    def __init__(self, action, method, hidden, button_label, disable_on_submit):
        self.action = action
        self.method = method
        self.hidden = hidden
        self.button_label = button_label
        self.disable_on_submit = disable_on_submit


class _FormParser(html.parser.HTMLParser):
    """Collect one form's action, hidden fields, button and any script.

    Only the order form matters, so a flat collection is enough: the page serves
    exactly one form and scripts are read only for their text.
    """

    def __init__(self):
        super().__init__()
        self.action = ""
        self.method = ""
        self.onsubmit = ""
        self.hidden = {}
        self.button_label = ""
        self.scripts = []
        self._in_button = False
        self._script = None

    def handle_starttag(self, tag, attrs):
        attr = {key.lower(): (value or "") for key, value in attrs}
        if tag == "form":
            self.action = attr.get("action", "")
            self.method = attr.get("method", "get")
            self.onsubmit = attr.get("onsubmit", "")
        elif tag == "input" and attr.get("type", "").lower() == "hidden":
            name = attr.get("name", "")
            if name:
                self.hidden[name] = attr.get("value", "")
        elif tag == "button":
            self._in_button = True
        elif tag == "script":
            self._script = []

    def handle_endtag(self, tag):
        if tag == "button":
            self._in_button = False
        elif tag == "script" and self._script is not None:
            self.scripts.append("".join(self._script))
            self._script = None

    def handle_data(self, data):
        if self._in_button:
            self.button_label += data
        if self._script is not None:
            self._script.append(data)


def _disables_on_submit(handler_text):
    """True if the text disables a control when the form is submitted.

    Covers the three ways a page usually does it: an `onsubmit` handler (or a
    script) setting `.disabled = true`, assigning the attribute, or calling
    `setAttribute("disabled", ...)`. The observer cannot run the code, so it
    reads the mechanism instead; see the module docstring.
    """
    if re.search(r"\.disabled\s*=\s*(true|1|!0|['\"]?disabled)", handler_text, re.IGNORECASE):
        return True
    if re.search(r"disabled\s*=\s*(true|['\"]?disabled)", handler_text, re.IGNORECASE):
        return True
    if re.search(r"setAttribute\s*\(\s*['\"]disabled", handler_text, re.IGNORECASE):
        return True
    return False


def parse_form(html_text):
    """Return the page's order `Form`: action, hidden fields, button, feedback.

    `disable_on_submit` is read from the `onsubmit` handler and any inline
    `<script>`, because that is the only part of the immediate state a
    standard-library observer can see without a rendering engine.
    """
    parser = _FormParser()
    parser.feed(html_text)
    parser.close()
    handler_text = " ".join([parser.onsubmit] + parser.scripts)
    label = " ".join(parser.button_label.split())
    return Form(parser.action, parser.method, dict(parser.hidden), label,
                _disables_on_submit(handler_text))


def _get(base_url, path):
    """Return (status, text, content_type); a 4xx/5xx body is read, not raised."""
    url = base_url.rstrip("/") + path
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return (response.status, response.read().decode("utf-8", "replace"),
                    response.headers.get("Content-Type", ""))
    except OSError as error:  # HTTPError and URLError both subclass OSError
        body = error.read().decode("utf-8", "replace") if hasattr(error, "read") else ""
        headers = getattr(error, "headers", None)
        content_type = headers.get("Content-Type", "") if headers else ""
        return getattr(error, "code", 0), body, content_type


def post_order(base_url, key, field_name=KEY_FIELD, product="widget"):
    """POST the order form urlencoded to `/order`; time the round trip.

    The key travels as a body field, so a server can dedup it without trusting a
    header or a cookie. The elapsed seconds are measured around the request so
    the report can show how long the user waited between the click and the
    confirmation.
    """
    data = urllib.parse.urlencode({field_name: key, "product": product}).encode("utf-8")
    url = base_url.rstrip("/") + "/order"
    request = urllib.request.Request(
        url, data=data, method="POST",
        headers={"User-Agent": USER_AGENT,
                 "Content-Type": "application/x-www-form-urlencoded"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", "replace")
            status = response.status
    except OSError as error:
        body = error.read().decode("utf-8", "replace") if hasattr(error, "read") else ""
        status = getattr(error, "code", 0)
    seconds = time.perf_counter() - start
    return Attempt(key, status, seconds, body)


def get_order_count(base_url):
    """GET `/orders` and return the number of orders the server recorded.

    The route answers JSON `{"count": n}` (or a bare number). Anything else is a
    broken contract: raise, so a missing counter is an error the caller can see
    rather than a silent zero.
    """
    status, body, _content_type = _get(base_url, "/orders")
    if status != 200:
        raise ValueError(f"GET /orders returned status {status}, not 200")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        text = body.strip()
        if text.isdigit():
            return int(text)
        raise ValueError(f"GET /orders did not return JSON or a number: {body[:80]!r}")
    if isinstance(data, dict):
        return int(data["count"])
    return int(data)


def impatient(base_url, clicks=3):
    """Load the order form, click submit `clicks` times, and report what happened.

    One form view is loaded and parsed; its key is reused for every click, the
    way a person hammering one button sends one key three times. If the form
    carries no key, an empty one is sent and a correct server records each click
    as a separate order. The order count is read before and after so the report
    distinguishes "the response said 200" from "the server actually recorded".
    """
    _status, page, _content_type = _get(base_url, "/order")
    form = parse_form(page)
    key = form.hidden.get(KEY_FIELD, "")
    orders_before = get_order_count(base_url)
    attempts = [post_order(base_url, key) for _ in range(clicks)]
    orders_after = get_order_count(base_url)
    return Report(attempts, orders_before, orders_after,
                  form.disable_on_submit, form.button_label)


def _main():
    parser = argparse.ArgumentParser(
        description="Click an order form too many times and count the orders.")
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:8000/")
    parser.add_argument("--clicks", type=int, default=3,
                        help="how many times to click submit (default 3)")
    args = parser.parse_args()
    parsed = urllib.parse.urlparse(args.url)
    base = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else args.url
    report = impatient(base, clicks=args.clicks)
    print(f"submitted the order form {len(report.attempts)} time(s) on {base}")
    for index, attempt in enumerate(report.attempts, start=1):
        shown = attempt.key[:8] if attempt.key else "(none)"
        print(f"  click {index}: key={shown} status={attempt.status} "
              f"{attempt.seconds * 1000:.1f} ms")
    print(f"  disables the control on submit: {report.disable_on_submit}")
    print(f"  submit control label: {report.button_label!r}")
    print(f"  orders before: {report.orders_before}  after: {report.orders_after}  "
          f"recorded: {report.orders_after - report.orders_before}")


if __name__ == "__main__":
    _main()
