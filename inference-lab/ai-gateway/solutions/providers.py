"""
Fake providers with scripted latency/error models, plus the static cache.

Sources (restated, not copied):
  - Nygard, *Release It!*: the failure classes to survive are "slow", "errors"
    and "refuses connections"; a healthy dependency usually degrades through
    slow before it starts erroring.
  - Google SRE book, "Addressing Cascading Failures": the fallback answer is
    usually stale or less personalised, never a fabricated fresh one.

DESIGN DECISION - a cycling script per provider instead of a random error rate?
  A seeded RNG is reproducible run to run but not code-path to code-path: add
  one call anywhere and every later draw shifts, so a test can start passing for
  the wrong reason. A short script makes the limit case the primary case:
  script=[FAIL, FAIL, OK] fails twice and then recovers, and a test can say
  exactly which call is which. Cost: no statistical coverage; a distribution
  belongs in the chaos suite (inference-lab project #14), not here.

DESIGN DECISION - run in-process with no sockets?
  127.0.0.1 servers and real timeouts would exercise HTTP framing, but the thing
  under test is the routing policy, not framing. Here Provider.complete() is a
  normal Python call and the TTFT is a number the provider reports, so checks
  never hang and SLO breaches are deterministic. Cost: the gateway never sees a
  real hung socket; the threading in limiter.py and circuit.py is not exercised
  by these sequential checks.

DESIGN DECISION - FAIL as a sentinel string, not a bool or an exception
instance?
  The script mixes outcomes of different types ("slow", a float, FAIL); a plain
  sentinel reads as data and keeps the script list flat and inspectable. A bool
  would collide with a legitimate 0.0 latency entry. Cost: an outcome of FAIL in
  a provider that also needs a custom error message cannot carry one.
"""
import time

from model import ProviderError, Response

OK = "ok"
FAIL = "fail"


class Provider:
    """A fake model provider driven by a cycling script of outcomes.

    script entries:
      None        -> success at this provider's default ttft_ms
      FAIL        -> raise ProviderError
      "slow"      -> success at slow_ms
      float/int   -> success at that ttft_ms
    script=None means always succeed (the happy path). calls counts every
    invocation, including failed ones, so a test can prove a circuit breaker
    stopped the hammering.
    """

    def __init__(self, name, ttft_ms=10.0, script=None, slow_ms=None, text_prefix=None):
        self.name = name
        self.ttft_ms = float(ttft_ms)
        self.slow_ms = float(slow_ms if slow_ms is not None else ttft_ms * 50)
        self.text_prefix = text_prefix if text_prefix is not None else name
        self.script = list(script) if script is not None else None
        self.calls = 0
        self._i = 0

    def complete(self, request):
        self.calls += 1
        entry = self._next()
        if entry == FAIL:
            raise ProviderError(f"provider {self.name!r} returned an error")
        if entry == "slow":
            time.sleep(self.slow_ms / 1000.0)  # a real slow call, for demos only
            ttft = self.slow_ms
        elif isinstance(entry, (int, float)):
            ttft = float(entry)
        else:
            ttft = self.ttft_ms
        return Response(text=f"{self.text_prefix}: {request.prompt}",
                        provider=self.name, ttft_ms=ttft)

    def _next(self):
        if self.script is None:
            return None
        entry = self.script[self._i % len(self.script)]
        self._i += 1
        return entry


class StaticCache:
    """Last-resort fallback: a canned answer, served even when every provider is down."""

    name = "cache"

    def __init__(self, text="The model is unavailable. Please retry shortly."):
        self.text = text
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        return Response(text=self.text, provider=self.name, ttft_ms=0.0,
                        cached=True, degraded=True)


def _demo():
    import time

    print("scripted outcomes for primary = [FAIL, FAIL, OK]:")
    primary = Provider("primary", ttft_ms=8.0, script=[FAIL, FAIL, OK])
    for i in range(3):
        try:
            r = primary.complete(_Req("q"))
            print(f"  call {i + 1}: {r}")
        except ProviderError as exc:
            print(f"  call {i + 1}: ProviderError ({exc})")

    # Measured wall-clock for the latency model: "slow" really is slow here.
    slow = Provider("slow", slow_ms=30.0, script=["slow"])
    t0 = time.perf_counter()
    slow.complete(_Req("q"))
    print(f"  a 'slow' provider took {(time.perf_counter() - t0) * 1000:.1f} ms wall-clock "
          f"and reports 30.0 ms TTFT")


class _Req:
    def __init__(self, prompt):
        self.prompt = prompt


if __name__ == "__main__":
    _demo()
