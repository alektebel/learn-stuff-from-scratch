"""
Per-provider circuit breaker for the gateway.

Source (restated, not copied): Nygard, *Release It!* (2nd ed.), the Circuit
Breaker state machine; also the implementation in system-design/circuit_breaker.py.

DESIGN DECISION - allow()/record_success()/record_failure() instead of
call(fn)?
  The callback form hides the routing decision the gateway needs: when the
  breaker is open the gateway does not want an exception, it wants to move to
  the next provider. Splitting the state machine from the call makes that
  explicit and keeps the breaker free of the provider and the clock of one
  request. Cost: the caller must record the outcome, so a path that forgets to
  does not count; the gateway records on every branch.

DESIGN DECISION - one probe at a time in HALF_OPEN?
  If a recovered dependency is hit by every queued request at once, the recovery
  probe becomes a thundering herd and re-opens the breaker. `_probe_in_flight`
  admits exactly one call until it reports back. Cost: a slow probe delays the
  rest; that delay is the point.

DESIGN DECISION - OPEN -> HALF_OPEN happens inside allow(), not on a timer?
  There is no background thread to move the state; time is checked when someone
  asks. A timer thread would wake for breakers that never get traffic and would
  need shutdown. Cost: a breaker with no traffic stays logically OPEN until the
  next call, which is indistinguishable from the correct behaviour.

DESIGN DECISION - the clock is injected?
  Check 7 proves recovery by advancing a fake clock past recovery_timeout, so
  the test never sleeps. Production uses time.monotonic (immune to wall-clock
  jumps). Cost: one more constructor argument, and callers who pass a wall clock
  lose that immunity.
"""
import threading
import time
from enum import Enum


class CircuitState(Enum):
    CLOSED = "CLOSED"        # normal: calls pass, failures are counted
    OPEN = "OPEN"            # failing fast: calls are skipped
    HALF_OPEN = "HALF_OPEN"  # probing: exactly one call tests recovery


class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30.0, clock=time.monotonic):
        self.failure_threshold = int(failure_threshold)
        self.recovery_timeout = float(recovery_timeout)
        self.clock = clock
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = None
        self._probe_in_flight = False
        self._lock = threading.Lock()

    @property
    def state(self):
        return self._state

    def allow(self):
        """True if a call may be attempted now.

        CLOSED always allows. OPEN allows only once recovery_timeout has passed,
        then moves to HALF_OPEN. HALF_OPEN allows exactly one probe at a time.
        """
        with self._lock:
            if self._state is CircuitState.OPEN:
                if self._opened_at is not None and self.clock() - self._opened_at >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._probe_in_flight = True
                    return True
                return False
            if self._state is CircuitState.HALF_OPEN:
                if self._probe_in_flight:
                    return False
                self._probe_in_flight = True
                return True
            return True

    def record_success(self):
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED
            self._opened_at = None
            self._probe_in_flight = False

    def record_failure(self):
        with self._lock:
            self._failures += 1
            self._probe_in_flight = False
            if self._state is CircuitState.HALF_OPEN or self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = self.clock()

    def reset(self):
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failures = 0
            self._opened_at = None
            self._probe_in_flight = False


class _Clock:
    def __init__(self, t=0.0):
        self.t = float(t)

    def __call__(self):
        return self.t

    def tick(self, dt):
        self.t += float(dt)


def _demo():
    clock = _Clock()
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0, clock=clock)
    print("event                     state      allow()")
    for i in range(3):
        allowed = breaker.allow()
        breaker.record_failure()
        print(f"  failure {i + 1}               {breaker.state.value:<10} {allowed}")
    print(f"  OPEN, next allow          {breaker.state.value:<10} {breaker.allow()}")
    clock.tick(breaker.recovery_timeout)
    probe = breaker.allow()
    print(f"  {breaker.recovery_timeout:.0f}s later (half-open)   {breaker.state.value:<10} {probe}")
    breaker.record_success()
    print(f"  probe succeeds            {breaker.state.value:<10} {breaker.allow()}")


if __name__ == "__main__":
    _demo()
