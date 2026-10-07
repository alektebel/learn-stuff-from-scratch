"""
Per-tenant rate limiting for the gateway.

Source (restated, not copied): fixed-window counter, as built in
system-design/rate_limiter.py. The gateway needs one limiter keyed by tenant so
one abusive caller cannot consume another's quota.

DESIGN DECISION - fixed window or token bucket?
  Fixed window is O(1) memory per tenant and the gateway's unit is "requests per
  window", which is how a quota is sold. Its known flaw is the boundary spike: a
  tenant can send `limit` requests at the end of one window and `limit` at the
  start of the next, twice the intended burst. That is acceptable here because
  the circuit breaker is the second line of defence and the window is short.
  Cost: the double-burst is real; check 4 measures inside a single window, and
  a token bucket would remove it at the price of a second tuning number.

DESIGN DECISION - the clock is injected instead of calling time.monotonic()
directly?
  A check that a window resets would otherwise have to sleep for window_seconds.
  With an injected clock the reset is deterministic and the whole suite stays
  well under a second. Production callers get the default and never think about
  it. Cost: one more constructor argument to document.

DESIGN DECISION - one lock for all tenants?
  Correctness first: a per-tenant lock would let tenants proceed in parallel,
  but the critical section is a dict read and write measured in nanoseconds, so
  contention is not the problem the gateway has. A single lock is easier to
  prove free of races. Cost: under a huge number of tenants the lock serialises
  admission; sharding by tenant hash is the next step, not this one.
"""
import threading
import time


class TenantRateLimiter:
    def __init__(self, limit, window_seconds, clock=time.monotonic):
        self.limit = int(limit)
        self.window_seconds = float(window_seconds)
        self.clock = clock
        self._windows = {}   # tenant -> (window_id, count)
        self._lock = threading.Lock()

    def allow(self, tenant):
        """Consume one request from this tenant's quota.

        Returns True when the request may proceed, False when the quota for the
        current window is already spent.
        """
        # TODO: Under the lock: window_id = int(clock() / window_seconds); load (window_id, count) for THIS tenant; if the window changed, reset count to 0; if count >= limit, store and return False; else store count + 1 and return True.
        raise NotImplementedError("TenantRateLimiter.allow")


class _Clock:
    """A hand-turned clock for the demo, so no real time passes."""

    def __init__(self, t=0.0):
        self.t = float(t)

    def __call__(self):
        return self.t

    def tick(self, dt):
        self.t += float(dt)


def _demo():
    clock = _Clock()
    limiter = TenantRateLimiter(limit=3, window_seconds=10.0, clock=clock)
    print("tenant   requests -> allowed?")
    for tenant in ("alice", "alice", "alice", "alice", "bob"):
        print(f"  {tenant:<6} {limiter.allow(tenant)}")
    print("  one window later:", end=" ")
    clock.tick(10.0)
    print("alice allowed =", limiter.allow("alice"))


if __name__ == "__main__":
    _demo()
