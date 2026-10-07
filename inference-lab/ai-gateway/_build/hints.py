"""Graded hints for the AI-gateway templates.

Keys are solution filenames; values map `function_or_Class.method` to the one-line
hint that replaces the body in the generated template.
"""

HINTS = {
    "limiter.py": {
        "TenantRateLimiter.allow": (
            "Under the lock: window_id = int(clock() / window_seconds); load "
            "(window_id, count) for THIS tenant; if the window changed, reset count to 0; "
            "if count >= limit, store and return False; else store count + 1 and return True."
        ),
    },
    "circuit.py": {
        "CircuitBreaker.allow": (
            "CLOSED -> True. OPEN -> True only once clock() - opened_at >= recovery_timeout "
            "(then move to HALF_OPEN and mark a probe in flight); otherwise False. "
            "HALF_OPEN -> admit one probe at a time."
        ),
        "CircuitBreaker.record_success": (
            "Reset the failure count, clear opened_at, mark no probe in flight, and set "
            "state = CLOSED; this is what closes a half-open circuit."
        ),
        "CircuitBreaker.record_failure": (
            "Increment the failure count; from HALF_OPEN, or once the count reaches "
            "failure_threshold, set state = OPEN and stamp opened_at = clock()."
        ),
    },
    "gateway.py": {
        "AIGateway.handle": (
            "Rate-limit the tenant first (raise RateLimitedError). Walk the provider chain "
            "in order: skip a link whose breaker is open; on ProviderError record a failure "
            "and continue; on success record it, and if ttft_ms <= request.max_ttft_ms return "
            "it (degraded iff not the first link), otherwise continue. After the chain, serve "
            "the cache (cached + degraded) or raise ProviderError."
        ),
    },
}
