"""
Lambda — invocation, concurrency and cold starts. Complete Solution.

DESIGN DECISION — how to model a "container"?
  You could invoke the handler directly and call it done.
  CHOSEN: model the execution ENVIRONMENT explicitly, with a lifetime and
  reusable state. That is what makes cold starts, warm state and the
  "why is my global variable still there" question demonstrable — and global
  state surviving between invocations is the single most common Lambda bug.

DESIGN DECISION — one concurrency number, or reserved plus unreserved?
  CHOSEN: both. Reserved concurrency is a floor AND a ceiling: it guarantees a
  function that much capacity and forbids it more. Setting it on one function
  silently reduces what every other function can use, which is a failure mode
  worth feeling once.

DESIGN DECISION — how do sync and async invocations differ?
  CHOSEN: model both. Synchronous throttling returns a 429 to the caller;
  asynchronous throttling is retried internally, and only after the retries
  are exhausted does the event go to a dead-letter destination. Same function,
  completely different failure behaviour.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple


class Throttled(Exception):
    """TooManyRequestsException — 429."""


class ExecutionEnvironment:
    """One "container": has an init cost, then survives to be reused."""

    def __init__(self, env_id: int, init_ms: float, now: float):
        self.env_id = env_id
        self.init_ms = init_ms
        self.created_at = now
        self.last_used = now
        self.invocations = 0
        self.state: Dict[str, Any] = {}     # survives between invocations

    def __repr__(self) -> str:
        return f"<Env {self.env_id} invocations={self.invocations}>"


class Invocation:
    def __init__(self, request_id: str, cold: bool, duration_ms: float,
                 billed_ms: float, result: Any, error: Optional[str] = None,
                 env_id: int = 0, attempt: int = 1):
        self.request_id = request_id
        self.cold = cold
        self.duration_ms = duration_ms
        self.billed_ms = billed_ms
        self.result = result
        self.error = error
        self.env_id = env_id
        self.attempt = attempt

    def __repr__(self) -> str:
        state = f"error={self.error}" if self.error else f"result={self.result!r}"
        return (f"<{'COLD' if self.cold else 'warm'} {self.billed_ms:.0f}ms "
                f"env={self.env_id} {state}>")


class Function:
    def __init__(self, name: str, handler: Callable[[Any, Any], Any],
                 memory_mb: int = 128, timeout_s: float = 3.0,
                 init_ms: float = 800.0, env_ttl_s: float = 300.0,
                 reserved_concurrency: Optional[int] = None,
                 dead_letter: Optional[List[Any]] = None):
        self.name = name
        self.handler = handler
        self.memory_mb = memory_mb
        self.timeout_s = timeout_s
        self.init_ms = init_ms
        self.env_ttl_s = env_ttl_s
        self.reserved_concurrency = reserved_concurrency
        self.dead_letter = dead_letter if dead_letter is not None else []
        self.environments: List[ExecutionEnvironment] = []
        self.busy = 0
        self._next_env = 1
        self.stats = {"invocations": 0, "cold_starts": 0, "throttles": 0,
                      "errors": 0, "async_retries": 0, "dead_lettered": 0,
                      "billed_ms": 0.0}


class LambdaService:
    """The control plane: owns the account-wide concurrency pool."""

    ACCOUNT_CONCURRENCY = 10       # tiny, so the limit is reachable in a demo

    def __init__(self, account_concurrency: Optional[int] = None):
        self.account_concurrency = account_concurrency or self.ACCOUNT_CONCURRENCY
        self.functions: Dict[str, Function] = {}

    def register(self, function: Function) -> Function:
        self.functions[function.name] = function
        return function

    # -- concurrency accounting ---------------------------------------------

    def unreserved_capacity(self) -> int:
        """What is left for functions WITHOUT reserved concurrency.

        Reserved concurrency is carved out of the account pool whether it is
        being used or not. Reserving 5 of 10 for one function means every other
        function in the account now shares 5 — which is why a single reservation
        can throttle an unrelated service.
        """
        reserved = sum(f.reserved_concurrency or 0
                       for f in self.functions.values())
        return self.account_concurrency - reserved

    def available_for(self, function: Function) -> int:
        if function.reserved_concurrency is not None:
            return function.reserved_concurrency - function.busy
        used = sum(f.busy for f in self.functions.values()
                   if f.reserved_concurrency is None)
        return self.unreserved_capacity() - used

    # -- invocation ---------------------------------------------------------

    def invoke(self, name: str, event: Any, now: Optional[float] = None,
               duration_ms: float = 50.0) -> Invocation:
        """Synchronous invoke. Throttling raises — the caller sees a 429."""
        now = time.time() if now is None else now
        function = self.functions[name]

        if self.available_for(function) <= 0:
            function.stats["throttles"] += 1
            raise Throttled(
                f"{name}: no concurrency available "
                f"({function.busy} running, limit "
                f"{function.reserved_concurrency or self.unreserved_capacity()})")

        environment, cold = self._acquire_environment(function, now)
        function.busy += 1
        try:
            wall = duration_ms + (environment.init_ms if cold else 0.0)
            request_id = f"req-{function.stats['invocations'] + 1:04d}"
            function.stats["invocations"] += 1
            if cold:
                function.stats["cold_starts"] += 1

            if wall > function.timeout_s * 1000:
                function.stats["errors"] += 1
                # Billed for the full timeout, and the environment is destroyed.
                function.environments.remove(environment)
                function.stats["billed_ms"] += function.timeout_s * 1000
                return Invocation(request_id, cold, wall,
                                  function.timeout_s * 1000, None,
                                  error="Task timed out", env_id=environment.env_id)

            context = {"function_name": name, "memory_mb": function.memory_mb,
                       "request_id": request_id, "env": environment.state}
            try:
                result, error = function.handler(event, context), None
            except Exception as exc:                    # noqa: BLE001
                result, error = None, f"{type(exc).__name__}: {exc}"
                function.stats["errors"] += 1

            environment.invocations += 1
            environment.last_used = now
            function.stats["billed_ms"] += wall
            return Invocation(request_id, cold, wall, wall, result, error,
                              environment.env_id)
        finally:
            function.busy -= 1

    def invoke_async(self, name: str, event: Any, now: Optional[float] = None,
                     duration_ms: float = 50.0,
                     max_attempts: int = 3) -> List[Invocation]:
        """Asynchronous invoke: retried internally, then dead-lettered.

        This is the difference that matters operationally. A synchronous caller
        sees the failure immediately and decides what to do. An asynchronous
        event is retried by Lambda itself — twice by default — and only then
        goes to the destination. A handler that is not idempotent will run
        three times.
        """
        now = time.time() if now is None else now
        function = self.functions[name]
        attempts: List[Invocation] = []

        for attempt in range(1, max_attempts + 1):
            try:
                result = self.invoke(name, event, now, duration_ms)
            except Throttled:
                function.stats["async_retries"] += 1
                now += 1.0
                continue
            result.attempt = attempt
            attempts.append(result)
            if result.error is None:
                return attempts
            function.stats["async_retries"] += 1
            now += 1.0

        function.dead_letter.append(event)
        function.stats["dead_lettered"] += 1
        return attempts

    def _acquire_environment(self, function: Function,
                             now: float) -> Tuple[ExecutionEnvironment, bool]:
        """Reuse a warm environment if one is free; otherwise pay the init cost."""
        function.environments = [e for e in function.environments
                                 if now - e.last_used < function.env_ttl_s]
        for environment in function.environments:
            if environment.invocations >= 0:      # free in this single-threaded model
                return environment, False
        environment = ExecutionEnvironment(function._next_env, function.init_ms, now)
        function._next_env += 1
        function.environments.append(environment)
        return environment, True

    def concurrent_invoke(self, name: str, events: List[Any],
                          now: Optional[float] = None,
                          duration_ms: float = 50.0) -> Tuple[int, int]:
        """Fire N events at once. Returns (succeeded, throttled)."""
        now = time.time() if now is None else now
        function = self.functions[name]
        succeeded = throttled = 0
        held: List[ExecutionEnvironment] = []
        for event in events:
            if self.available_for(function) <= 0:
                function.stats["throttles"] += 1
                throttled += 1
                continue
            environment, cold = self._acquire_environment(function, now)
            function.busy += 1
            held.append(environment)
            environment.invocations += 1
            if cold:
                function.stats["cold_starts"] += 1
            function.stats["invocations"] += 1
            succeeded += 1
        function.busy -= len(held)
        return succeeded, throttled


def _demo() -> None:
    service = LambdaService(account_concurrency=10)

    counter_state = {"seen": 0}

    def handler(event, context):
        # A module-level counter: the classic Lambda surprise.
        context["env"]["calls"] = context["env"].get("calls", 0) + 1
        counter_state["seen"] += 1
        return {"echo": event, "calls_in_this_env": context["env"]["calls"]}

    api = service.register(Function("api", handler, init_ms=800, timeout_s=3))

    print("=== Cold starts, and warm state that outlives your invocation ===")
    for n in range(4):
        result = service.invoke("api", {"n": n}, now=n)
        print(f"  invoke {n}: {result}  {result.result}")
    print("  Only the first paid the 800ms init. And `calls_in_this_env` keeps")
    print("  climbing: anything you put outside the handler SURVIVES. Great for")
    print("  a database connection, a disaster for a cache you assumed was empty.")

    print("\n=== The environment eventually goes away ===")
    late = service.invoke("api", {"n": "later"}, now=1000)
    print(f"  after 1000s idle (TTL 300s): {late}")
    print("  You cannot rely on warm state, and you cannot rely on it being gone.")

    print("\n=== Concurrency is the real limit ===")
    print(f"  account concurrency: {service.account_concurrency}")
    succeeded, throttled = service.concurrent_invoke(
        "api", [{"i": i} for i in range(15)], now=2000)
    print(f"  15 simultaneous events -> {succeeded} ran, {throttled} throttled")
    print("  Throttling is not about CPU. It is a quota, and a burst of 15 into")
    print("  a limit of 10 sheds 5 regardless of how fast the function is.")

    print("\n=== Reserved concurrency is a ceiling AND a floor ===")
    def noop(event, context):
        return "ok"
    service.register(Function("critical", noop, reserved_concurrency=6))
    print(f"  reserved 6 for 'critical'")
    print(f"  unreserved pool left for everything else: "
          f"{service.unreserved_capacity()}")
    succeeded, throttled = service.concurrent_invoke(
        "api", [{"i": i} for i in range(10)], now=3000)
    print(f"  10 events to 'api' -> {succeeded} ran, {throttled} throttled")
    print("  'api' was not changed at all. Reserving capacity for one function")
    print("  silently took it from every other function in the account.")

    print("\n=== Sync vs async failure: the same bug, different blast radius ===")
    def flaky(event, context):
        raise ValueError("downstream unavailable")

    dlq: List[Any] = []
    service.register(Function("worker", flaky, init_ms=100, dead_letter=dlq))

    result = service.invoke("worker", {"job": 1}, now=4000)
    print(f"  sync:  {result.error}  -> the caller decides what to do")

    attempts = service.invoke_async("worker", {"job": 2}, now=4100)
    print(f"  async: {len(attempts)} attempts, all failing")
    print(f"         dead letter queue now holds: {dlq}")
    print("  Async runs the handler THREE times before giving up. If it is not")
    print("  idempotent, that is three charges, three emails, three of whatever.")

    print("\n=== Timeouts are billed in full ===")
    def slow(event, context):
        return "never gets here"
    service.register(Function("slow", slow, timeout_s=1.0, init_ms=100))
    result = service.invoke("slow", {}, now=5000, duration_ms=5000)
    print(f"  {result}")
    print(f"  billed {result.billed_ms:.0f}ms for work that produced nothing,")
    print("  and the environment is destroyed, so the next call is cold too.")


if __name__ == "__main__":
    _demo()
