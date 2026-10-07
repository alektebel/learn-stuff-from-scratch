"""
The AI gateway: multi-provider routing with a degradation chain.

Sources (restated, not copied):
  - Nygard, *Release It!* (2nd ed.): the fallback chain (primary -> replica ->
    cache) and the circuit breaker are the two stability patterns this gateway
    combines.
  - Google SRE book, "Handling Overload" and "Service Level Objectives": shed
    or degrade before the queue collapses, and treat a TTFT target as an SLO —
    a call that returns but misses the target is a breach.
  - Amazon's 2002 API mandate: every internal call can fail, so a caller must
    name a fallback.

DESIGN DECISION - an ordered chain that the gateway walks, not a fixed
primary/fallback pair?
  Providers can be added without changing the policy; "next" is simply the next
  provider whose breaker admits a call. Cost: the policy must skip open breakers,
  which is one more branch; check 6 pins it.

DESIGN DECISION - an SLO breach means "try the next provider", not a failure
recorded on the breaker?
  A provider that answers correctly but slowly is not failing; tripping its
  breaker would eject capacity that is merely slow. The gateway records a
  success for the breaker and continues down the chain, so the slow provider is
  retried on the next request instead of being removed. Cost: a permanently slow
  provider is probed on every request; the SLO budget, not the breaker, bounds
  that.

DESIGN DECISION - when the chain is exhausted, serve the cache or raise?
  If a cache is configured, serve it and mark the response cached and degraded.
  Otherwise raise ProviderError. Returning an empty 200 would hide an outage
  from the caller; the gateway is not allowed to invent an answer. Cost: the
  caller must handle ProviderError (an HTTP layer maps it to 502).

DESIGN DECISION - one breaker per provider, keyed by name?
  Two links must not share a breaker, or a healthy replica would be ejected with
  a failing one. The constructor builds one per provider unless explicit
  breakers are injected (a caller may supply its own, e.g. with a fake clock). Cost:
  the caller can pass a name that does not match a provider, handled by .get().
"""
import time

from circuit import CircuitBreaker
from model import ProviderError, RateLimitedError


class AIGateway:
    def __init__(self, providers, cache=None, rate_limiter=None, breakers=None,
                 default_slo_ms=1000.0, clock=time.monotonic):
        self.providers = list(providers)
        self.cache = cache
        self.rate_limiter = rate_limiter
        self.default_slo_ms = float(default_slo_ms)
        self.clock = clock
        self.breakers = breakers if breakers is not None else {
            p.name: CircuitBreaker(clock=clock) for p in self.providers}
        self.stats = {"requests": 0, "rate_limited": 0, "cache_hits": 0,
                      "degraded": 0, "provider_calls": 0}

    def handle(self, request):
        """Route one request down the degradation chain.

        Returns a Response. Raises RateLimitedError when the tenant is over
        quota, or ProviderError when every provider failed and no cache is set.
        """
        # TODO: Rate-limit the tenant first (raise RateLimitedError). Walk the provider chain in order: skip a link whose breaker is open; on ProviderError record a failure and continue; on success record it, and if ttft_ms <= request.max_ttft_ms return it (degraded iff not the first link), otherwise continue. After the chain, serve the cache (cached + degraded) or raise ProviderError.
        raise NotImplementedError("AIGateway.handle")


def _demo():
    from model import Request
    from providers import FAIL, OK, Provider, StaticCache

    print("routing a burst through a primary that fails every other call:")
    primary = Provider("primary", ttft_ms=8.0, script=[FAIL, OK])
    fallback = Provider("fallback", ttft_ms=40.0)
    cache = StaticCache(text="canned answer")
    gateway = AIGateway([primary, fallback], cache=cache)
    served = {"primary": 0, "fallback": 0, "cache": 0}
    for i in range(1000):
        response = gateway.handle(Request("tenant-a", f"q{i}", max_ttft_ms=100.0))
        served[response.provider] += 1
    print(f"  primary={served['primary']} fallback={served['fallback']} cache={served['cache']} "
          f"(primary calls={primary.calls})")

    print("when every provider is down:")
    down = AIGateway([Provider("p", script=[FAIL])], cache=StaticCache(text="canned answer"))
    response = down.handle(Request("tenant-b", "q", max_ttft_ms=100.0))
    print(f"  served {response}")
    print(f"  failovers to cache = {down.stats['cache_hits']} of {down.stats['requests']} requests")


if __name__ == "__main__":
    _demo()
