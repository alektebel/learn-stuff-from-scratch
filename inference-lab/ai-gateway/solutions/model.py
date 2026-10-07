"""
Request/response model and the gateway's error taxonomy.

Sources (restated, not copied):
  - Google SRE book, "Service Level Objectives": a first-token budget is an SLI
    with a target; a call that succeeds but misses the target is still a breach.
  - Nygard, *Release It!* (2nd ed.), "Stability Patterns": fail fast, circuit
    breaker and the fallback chain are the three patterns this gateway joins.
  - Amazon's 2002 API mandate: every internal call is a network call that can
    fail, so a fallback is explicit rather than assumed.

DESIGN DECISION - one exception class per failure mode, not one GatewayError
with a code string?
  The router branches on the KIND of failure. A rate limit is a client error:
  trying another provider would not help, so it must surface as 429. A provider
  error is a routing signal: try the next link. A circuit-open is also a routing
  signal but must not be double-counted as a fresh provider failure. Distinct
  types make those branches impossible to confuse, and `except GatewayError`
  cannot silently swallow a quota violation. Cost: callers must name three
  exceptions; a code enum would be one import but loses the check.

DESIGN DECISION - ttft_ms carried on the Response rather than measured by the
gateway?
  In this CPU-real simulation the provider reports its own first-token time, so
  checks are deterministic and no test has to sleep to observe a breach. A real
  gateway wraps a streaming socket and stamps the time of the first content
  chunk; that work lives behind Provider.complete(). Cost: the gateway trusts
  the number it is given, which is exactly where the SLO comparison belongs.
  providers.py shows the same model against measured wall-clock.
"""
from dataclasses import dataclass
from typing import Optional


class GatewayError(Exception):
    """Base class for every failure the gateway raises."""


class ProviderError(GatewayError):
    """A provider call failed (timeout, 5xx, refused). Try the next provider."""


class RateLimitedError(GatewayError):
    """The tenant exhausted its quota for the window. Surface as HTTP 429."""


class CircuitOpenError(GatewayError):
    """The provider's breaker is open and the call was not attempted."""


class SLOTimeoutError(GatewayError):
    """A successful call breached the request's TTFT budget."""


@dataclass
class Request:
    tenant: str
    prompt: str
    max_ttft_ms: float = 1000.0
    priority: int = 0


@dataclass
class Response:
    text: str
    provider: str
    ttft_ms: float
    cached: bool = False
    degraded: bool = False
    attempts: int = 1

    def __str__(self) -> str:
        tag = " (cache)" if self.cached else (" (degraded)" if self.degraded else "")
        return f"[{self.provider} {self.ttft_ms:.1f}ms]{tag} {self.text}"


if __name__ == "__main__":
    print(Response(text="the answer", provider="primary", ttft_ms=12.0))
    print(Response(text="canned", provider="cache", ttft_ms=0.0, cached=True, degraded=True))
