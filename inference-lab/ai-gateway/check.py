"""
Progress checker for the AI-gateway templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure):
that is simply the next thing to write. Nothing here imports solutions/. It
tests YOUR code.
"""

import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


class FakeClock:
    """A hand-turned clock. Checks never sleep to observe a timeout."""

    def __init__(self, t=0.0):
        self.t = float(t)

    def __call__(self):
        return self.t

    def tick(self, dt):
        self.t += float(dt)


def _req(tenant="t", prompt="hello", max_ttft_ms=1000.0):
    from model import Request
    return Request(tenant=tenant, prompt=prompt, max_ttft_ms=max_ttft_ms)


# ---------------------------------------------------------------------------
# Steps 5-9: gateway.py
# ---------------------------------------------------------------------------

def check_happy_path() -> None:
    from gateway import AIGateway
    from providers import Provider

    primary = Provider("primary", ttft_ms=12.0)
    gateway = AIGateway([primary])
    response = gateway.handle(_req(prompt="hello", max_ttft_ms=100.0))
    assert response.provider == "primary", (
        f"the only provider is healthy; the request should be served by it, got {response.provider!r}")
    assert "hello" in response.text, f"the provider's answer was not passed through: {response.text!r}"
    assert response.ttft_ms == 12.0, f"the response lost its TTFT: {response.ttft_ms}"
    assert response.degraded is False and response.cached is False, (
        "a first-link success is not a degradation")
    assert primary.calls == 1, f"the provider should be called exactly once, was called {primary.calls} times"


def check_fallback_on_primary_failure() -> None:
    from gateway import AIGateway
    from providers import FAIL, Provider

    primary = Provider("primary", script=[FAIL])
    fallback = Provider("fallback", ttft_ms=20.0)
    gateway = AIGateway([primary, fallback])
    response = gateway.handle(_req())
    assert response.provider == "fallback", (
        "when the primary raises ProviderError the router must advance to the next "
        f"provider; it served from {response.provider!r} instead — does the failure branch "
        "`continue` the chain rather than `break` or return?")
    assert primary.calls == 1 and fallback.calls == 1, (
        f"expected one call to each link, got primary={primary.calls} fallback={fallback.calls}")
    assert response.degraded is True, "a request served after a failure is degraded"


def check_cache_of_last_resort() -> None:
    from gateway import AIGateway
    from model import ProviderError
    from providers import FAIL, Provider, StaticCache

    primary = Provider("primary", script=[FAIL])
    fallback = Provider("fallback", script=[FAIL])
    cache = StaticCache(text="canned")
    gateway = AIGateway([primary, fallback], cache=cache)
    response = gateway.handle(_req())
    assert response.provider == "cache" and response.cached is True, (
        f"with every provider down the static cache must answer, got {response}")
    assert response.text == "canned", f"the cached text was not served: {response.text!r}"
    assert response.degraded is True, "a cache answer is a degradation"
    assert primary.calls == 1 and fallback.calls == 1, (
        "the chain should have tried each provider once before falling back to the cache")

    gateway_no_cache = AIGateway([Provider("primary", script=[FAIL])])
    try:
        gateway_no_cache.handle(_req())
    except ProviderError:
        pass
    else:
        raise AssertionError(
            "with no cache and no healthy provider handle() must raise ProviderError, "
            "not invent an answer")


def check_slo_degradation() -> None:
    from gateway import AIGateway
    from providers import Provider

    slow = Provider("primary", ttft_ms=500.0)
    fast = Provider("fallback", ttft_ms=10.0)
    gateway = AIGateway([slow, fast])
    response = gateway.handle(_req(max_ttft_ms=100.0))
    assert response.provider == "fallback", (
        f"a first token at 500 ms misses the 100 ms SLO, so the router must continue to "
        f"the next provider; it returned {response.provider!r} — is the SLO compared with "
        "`<=` against the request's budget?")
    assert response.degraded is True, "an SLO breach that is retried is a degradation"

    # The limit case in the other direction: a first token within budget must NOT degrade.
    primary = Provider("primary", ttft_ms=10.0)
    other = Provider("fallback", ttft_ms=10.0)
    gateway = AIGateway([primary, other])
    response = gateway.handle(_req(max_ttft_ms=100.0))
    assert response.provider == "primary", (
        "a first token inside the SLO must be served by the primary; the SLO check is a "
        f"comparison, not an unconditional degrade — got {response.provider!r}")
    assert response.degraded is False, "a within-budget success is not a degradation"


def check_gateway_enforces_quota() -> None:
    from gateway import AIGateway
    from limiter import TenantRateLimiter
    from model import RateLimitedError
    from providers import Provider

    clock = FakeClock()
    limiter = TenantRateLimiter(limit=1, window_seconds=10.0, clock=clock)
    primary = Provider("primary")
    gateway = AIGateway([primary], rate_limiter=limiter)

    assert gateway.handle(_req("alice")).provider == "primary"
    assert primary.calls == 1, "the admitted request should reach the provider"
    try:
        gateway.handle(_req("alice"))
    except RateLimitedError:
        pass
    else:
        raise AssertionError(
            "the gateway must consult the tenant limiter and surface a RateLimitedError "
            "for the over-quota request")
    assert primary.calls == 1, (
        "a rate-limited request must be rejected before it reaches any provider")
    assert gateway.handle(_req("bob")).provider == "primary", (
        "bob has his own quota; alice exhausting hers must not block him")


# ---------------------------------------------------------------------------
# Steps 1-2: limiter.py
# ---------------------------------------------------------------------------

def check_rate_limit_per_tenant() -> None:
    from limiter import TenantRateLimiter

    clock = FakeClock()
    limiter = TenantRateLimiter(limit=2, window_seconds=10.0, clock=clock)
    assert limiter.allow("alice") is True, "the first request in a fresh window is admitted"
    assert limiter.allow("alice") is True, "the second request is still inside the limit"
    assert limiter.allow("alice") is False, "the third request in the window must be denied"
    assert limiter.allow("bob") is True, (
        "bob has his own quota; alice exhausting hers must not block him — is the "
        "limiter keyed by tenant rather than by a single global counter?")


def check_rate_limit_window_resets() -> None:
    from limiter import TenantRateLimiter

    clock = FakeClock()
    limiter = TenantRateLimiter(limit=1, window_seconds=10.0, clock=clock)
    assert limiter.allow("a") is True, "the first request in a fresh window is admitted"
    assert limiter.allow("a") is False, "the second request in the same window is denied"
    clock.tick(10.0)
    assert limiter.allow("a") is True, (
        "a full window has passed, so the tenant's counter must reset; does allow() "
        "compare the stored window id with the current one?")


# ---------------------------------------------------------------------------
# Steps 3-4: circuit.py
# ---------------------------------------------------------------------------

def check_circuit_opens() -> None:
    from circuit import CircuitBreaker, CircuitState

    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=5.0, clock=clock)
    assert breaker.state is CircuitState.CLOSED, "a new breaker starts closed"
    assert breaker.allow() is True, "a closed breaker admits calls"
    breaker.record_failure()
    assert breaker.allow() is True, "one failure is below the threshold"
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN, (
        f"after {breaker.failure_threshold} failures the breaker must open; state is "
        f"{breaker.state} — does record_failure() increment the count and does the "
        "threshold test use `>=`?")
    assert breaker.allow() is False, (
        "an OPEN breaker must refuse calls instead of hammering the provider")
    clock.tick(4.0)
    assert breaker.allow() is False, (
        "before recovery_timeout the breaker stays open")


def check_circuit_recovers() -> None:
    from circuit import CircuitBreaker, CircuitState

    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=5.0, clock=clock)
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN, "precondition: the breaker is open"
    clock.tick(5.0)
    assert breaker.allow() is True, (
        "after recovery_timeout the breaker should half-open and admit one probe")
    assert breaker.state is CircuitState.HALF_OPEN, (
        f"admitting the first probe after the timeout moves the breaker to HALF_OPEN, "
        f"got {breaker.state}")
    breaker.record_success()
    assert breaker.state is CircuitState.CLOSED, (
        f"a successful probe must close the breaker; state is {breaker.state} — does "
        "record_success() reset the state to CLOSED?")
    assert breaker.allow() is True, "a closed breaker admits calls again"

    # A second breaker takes the same journey except the probe fails: HALF_OPEN must
    # admit exactly one probe, and a failing probe must return the breaker to OPEN.
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=5.0, clock=clock)
    breaker.record_failure()
    breaker.record_failure()
    clock.tick(5.0)
    assert breaker.allow() is True, "the first probe after the timeout is admitted"
    assert breaker.state is CircuitState.HALF_OPEN, "precondition: the breaker is probing"
    assert breaker.allow() is False, (
        "HALF_OPEN admits exactly one probe at a time; a second caller must be refused "
        "until the first probe reports back — does allow() guard on a probe in flight?")
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN, (
        f"a failing probe must return the breaker to OPEN; got {breaker.state} — does "
        "record_failure() reopen from HALF_OPEN?")
    assert breaker.allow() is False, (
        "a failed probe leaves the breaker OPEN, so it refuses calls again")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("limiter.py", "quota is per tenant, rejected at the limit", check_rate_limit_per_tenant),
    ("limiter.py", "the window resets after window_seconds", check_rate_limit_window_resets),
    ("circuit.py", "breaker opens after the failure threshold", check_circuit_opens),
    ("circuit.py", "half-open probe closes on recovery", check_circuit_recovers),
    ("gateway.py", "happy-path routing to the primary", check_happy_path),
    ("gateway.py", "primary failure advances to the fallback", check_fallback_on_primary_failure),
    ("gateway.py", "all providers fail -> static cache, or ProviderError", check_cache_of_last_resort),
    ("gateway.py", "TTFT SLO breach degrades; a success does not", check_slo_degradation),
    ("gateway.py", "the gateway enforces the tenant quota before routing", check_gateway_enforces_quota),
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
    print(f"\n{BOLD}AI Gateway — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<12} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<12} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<12} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built an AI gateway.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
