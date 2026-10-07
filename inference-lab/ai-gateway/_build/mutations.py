"""Plant known bugs in copies of the solutions; every one must be CAUGHT.

Run:
    python3 .claude/skills/graded-module/scripts/mutate.py \
        inference-lab/ai-gateway inference-lab/ai-gateway/_build/mutations.py

Each entry: (description, file, exact text in solutions/<file>, replacement, check step).
The last element is the step index in check.py that must fail (✗) with the bug present.
"""

MUTATIONS = [
    # Classic: the rate limiter keeps one bucket for everybody, so one noisy tenant
    # exhausts every other tenant's quota.
    ("rate limiter shared across tenants",
     "limiter.py",
     "            quota_key = tenant\n",
     "            quota_key = \"all-tenants\"\n",
     "1"),
    # Classic: the window is never rolled over, so a tenant stays blocked forever.
    ("rate limiter never resets its window",
     "limiter.py",
     "            if current_window != window_id:\n",
     "            if False:\n",
     "2"),
    # Classic: failures are counted but the threshold never trips, so the breaker
    # keeps hammering a dead provider.
    ("circuit breaker never opens",
     "circuit.py",
     "            if self._state is CircuitState.HALF_OPEN or self._failures >= self.failure_threshold:\n",
     "            if self._state is CircuitState.HALF_OPEN:\n",
     "3"),
    # Classic: a successful half-open probe does not reset to CLOSED, so the
    # provider is never fully trusted again.
    ("half-open probe success does not close the circuit",
     "circuit.py",
     "            self._state = CircuitState.CLOSED\n",
     "            self._state = CircuitState.HALF_OPEN\n",
     "4"),
    # Classic: the one-probe guard is gone, so every queued call storms a recovered
    # provider and re-opens the breaker.
    ("half-open admits every caller (one-probe guard deleted)",
     "circuit.py",
     "            if self._state is CircuitState.HALF_OPEN:\n"
     "                if self._probe_in_flight:\n"
     "                    return False\n"
     "                self._probe_in_flight = True\n"
     "                return True\n",
     "            if self._state is CircuitState.HALF_OPEN:\n"
     "                return True\n",
     "4"),
    # Classic: a failing probe is treated as recovery, so the breaker never re-opens
    # and keeps traffic on a dead provider.
    ("a failing half-open probe does not return to OPEN",
     "circuit.py",
     "            if self._state is CircuitState.HALF_OPEN or self._failures >= self.failure_threshold:\n"
     "                self._state = CircuitState.OPEN\n"
     "                self._opened_at = self.clock()\n",
     "            if self._state is CircuitState.HALF_OPEN:\n"
     "                self._state = CircuitState.CLOSED\n"
     "                self._opened_at = None\n"
     "            elif self._failures >= self.failure_threshold:\n"
     "                self._state = CircuitState.OPEN\n"
     "                self._opened_at = self.clock()\n",
     "4"),
    # Classic: a provider failure stops the walk instead of advancing the chain.
    ("fallback chain never advances past a failure",
     "gateway.py",
     "            except ProviderError:\n"
     "                if breaker is not None:\n"
     "                    breaker.record_failure()\n"
     "                continue\n",
     "            except ProviderError:\n"
     "                if breaker is not None:\n"
     "                    breaker.record_failure()\n"
     "                break\n",
     "6"),
    # Classic: the SLO is not actually compared, so every success degrades.
    ("SLO degradation triggers even on an in-budget success",
     "gateway.py",
     "            if response.ttft_ms <= slo:\n",
     "            if True:\n",
     "8"),
    # Classic: the last-resort cache is never consulted, so an outage surfaces as a
    # raw error with no degradation.
    ("static cache never used when every provider fails",
     "gateway.py",
     "        if self.cache is not None:\n",
     "        if False:\n",
     "7"),
]
