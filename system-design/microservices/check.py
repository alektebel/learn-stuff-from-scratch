"""
Progress checker for the microservices templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.
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


# ---------------------------------------------------------------------------
# Steps 1-4: registry.py — service discovery, health, draining
# ---------------------------------------------------------------------------

def check_register_resolve() -> None:
    from registry import ServiceRegistry

    registry = ServiceRegistry()
    registry.register("orders", "a", "10.0.0.1:80", ttl=30, now=0.0)
    registry.register("orders", "b", "10.0.0.2:80", ttl=30, now=0.0)
    assert registry.resolve("orders", now=0.0) == ["10.0.0.1:80", "10.0.0.2:80"]
    assert registry.resolve("unknown", now=0.0) == [], "an unknown service resolves to nothing"
    assert registry.resolve("orders", now=29.999) == ["10.0.0.1:80", "10.0.0.2:80"]


def check_expiry_and_heartbeat() -> None:
    from registry import ServiceRegistry

    registry = ServiceRegistry()
    registry.register("svc", "a", "ep-a", ttl=10, now=0.0)
    registry.register("svc", "b", "ep-b", ttl=10, now=0.0)
    assert registry.heartbeat("svc", "b", now=9.0) is True
    assert registry.resolve("svc", now=10.0) == ["ep-b"], (
        "at now=ttl 'a' is expired (now >= expires_at); 'b' was refreshed at 9, alive until 19")
    assert registry.sweep(now=10.0) == 1, "sweep must remove exactly the expired instance"
    assert ("svc", "a") not in registry.instances and ("svc", "b") in registry.instances
    assert registry.heartbeat("svc", "ghost", now=10.0) is False, (
        "heartbeating an unknown instance reports not-found")


def check_draining_and_deregister() -> None:
    from registry import ServiceRegistry

    registry = ServiceRegistry()
    registry.register("svc", "a", "ep-a", ttl=100, now=0.0)
    registry.register("svc", "b", "ep-b", ttl=100, now=0.0)
    assert registry.start_draining("svc", "a") is True
    assert registry.resolve("svc", now=1.0) == ["ep-b"], (
        "a draining instance must not receive new traffic")
    assert ("svc", "a") in registry.instances, (
        "draining keeps the instance registered so in-flight requests can finish")
    assert registry.deregister("svc", "a") is True
    assert registry.resolve("svc", now=1.0) == ["ep-b"]
    assert registry.deregister("svc", "a") is False, "deregistering twice reports not-found"
    assert registry.start_draining("svc", "ghost") is False


def check_reregister_and_isolation() -> None:
    from registry import ServiceRegistry

    registry = ServiceRegistry()
    registry.register("svc", "a", "old:80", ttl=10, now=0.0)
    registry.register("svc", "a", "new:80", ttl=10, now=5.0)  # updates endpoint and deadline
    registry.register("other", "a", "other:80", ttl=10, now=0.0)
    assert registry.resolve("svc", now=6.0) == ["new:80"], "re-registering replaces the endpoint"
    assert registry.resolve("other", now=6.0) == ["other:80"], "services do not leak into each other"
    assert registry.resolve("svc", now=15.0) == [], "the refreshed deadline is now=5 + ttl 10"
    assert registry.resolve("other", now=10.0) == []


# ---------------------------------------------------------------------------
# Steps 5-9: gateway.py — routing, load balancing, safe retries
# ---------------------------------------------------------------------------

def check_gateway_routing() -> None:
    from gateway import Gateway
    from registry import ServiceRegistry

    gateway = Gateway(ServiceRegistry(), [("/api", "api"), ("/api/v2", "api2"), ("/", "web")])
    assert gateway.match("/api/orders") == "api"
    assert gateway.match("/api") == "api"
    assert gateway.match("/api/v2/orders") == "api2", "the longest matching prefix wins"
    assert gateway.match("/api/v2") == "api2"
    assert gateway.match("/apix") == "web", (
        "a prefix must match on a path boundary; '/api' must not swallow '/apix'")
    assert gateway.match("/") == "web"
    no_catch_all = Gateway(ServiceRegistry(), [("/api", "api")])
    assert no_catch_all.call("GET", "/other", now=0.0, invoke=lambda endpoint: 200) == 404, (
        "a path matching no route is a 404, not a call to a random service")


def check_gateway_load_balancing() -> None:
    from gateway import Gateway
    from registry import ServiceRegistry

    registry = ServiceRegistry()
    registry.register("svc", "a", "ep-a", ttl=100, now=0.0)
    registry.register("svc", "b", "ep-b", ttl=100, now=0.0)
    registry.register("svc", "c", "ep-c", ttl=100, now=0.0)
    gateway = Gateway(registry, [("/", "svc")])
    picks = [gateway.pick("svc", now=0.0) for _ in range(4)]
    assert picks == ["ep-a", "ep-b", "ep-c", "ep-a"], f"round-robin, got {picks}"
    registry.start_draining("svc", "b")
    gateway._next["svc"] = 0
    picks = [gateway.pick("svc", now=0.0) for _ in range(3)]
    assert picks == ["ep-a", "ep-c", "ep-a"], f"draining instances are skipped, got {picks}"
    registry.start_draining("svc", "a")
    registry.start_draining("svc", "c")
    assert gateway.pick("svc", now=0.0) is None
    assert gateway.call("GET", "/x", now=0.0, invoke=lambda endpoint: 200) == 503, (
        "no healthy instance is a 503, and the handler must not be called")


def check_gateway_retries_idempotent() -> None:
    from gateway import Gateway
    from registry import ServiceRegistry

    registry = ServiceRegistry()
    registry.register("svc", "a", "ep-a", ttl=100, now=0.0)
    registry.register("svc", "b", "ep-b", ttl=100, now=0.0)
    gateway = Gateway(registry, [("/", "svc")], max_retries=2)
    seen = []

    def flaky(endpoint):
        seen.append(endpoint)
        return 500 if len(seen) < 3 else 200

    assert gateway.call("GET", "/x", now=0.0, invoke=flaky) == 200
    assert seen == ["ep-a", "ep-b", "ep-a"], (
        f"a retry must re-pick a fresh healthy instance, got {seen}")
    seen.clear()
    assert gateway.call("GET", "/x", now=0.0, invoke=lambda e: (seen.append(e), 503)[1]) == 503
    assert len(seen) == 3, "max_retries=2 means at most 3 attempts"


def check_gateway_does_not_retry_post() -> None:
    from gateway import Gateway
    from registry import ServiceRegistry

    registry = ServiceRegistry()
    registry.register("svc", "a", "ep-a", ttl=100, now=0.0)
    registry.register("svc", "b", "ep-b", ttl=100, now=0.0)
    gateway = Gateway(registry, [("/", "svc")], max_retries=2)
    calls = []

    def create_order(endpoint):
        calls.append(endpoint)  # imagine this creates an order
        return 500

    assert gateway.call("POST", "/orders", now=0.0, invoke=create_order) == 500
    assert calls == ["ep-a"], (
        f"a POST must never be retried (it may have applied a side effect); it ran {len(calls)}x")


def check_gateway_does_not_retry_4xx() -> None:
    from gateway import Gateway
    from registry import ServiceRegistry

    registry = ServiceRegistry()
    registry.register("svc", "a", "ep-a", ttl=100, now=0.0)
    gateway = Gateway(registry, [("/", "svc")], max_retries=2)
    calls = []

    def bad_request(endpoint):
        calls.append(endpoint)
        return 400

    assert gateway.call("GET", "/x", now=0.0, invoke=bad_request) == 400
    assert len(calls) == 1, "a 4xx is the client's fault: retrying cannot help"
    calls.clear()

    def refuse(endpoint):
        calls.append(endpoint)
        raise ConnectionError("connection refused")

    assert gateway.call("GET", "/x", now=0.0, invoke=refuse) == 503, (
        "a connection error looks like a transient 5xx")
    assert len(calls) == 3, "a transient failure on an idempotent method is retried"


# ---------------------------------------------------------------------------
# Steps 10-13: contract.py — versioned schema compatibility
# ---------------------------------------------------------------------------

def check_contract_additive() -> None:
    from contract import compatibility

    v1 = {"fields": {"id": {"type": "string", "required": True}}}
    same = {"fields": {"id": {"type": "string", "required": True}}}
    add_optional = {"fields": {"id": {"type": "string", "required": True},
                               "note": {"type": "string", "required": False}}}
    assert compatibility(v1, same) == "compatible"
    assert compatibility(v1, add_optional) == "compatible", "a new OPTIONAL field is additive"


def check_contract_required() -> None:
    from contract import breaking_changes, compatibility

    v1 = {"fields": {"id": {"type": "string", "required": True},
                     "total": {"type": "number", "required": False}}}
    add_required = {"fields": {**v1["fields"], "region": {"type": "string", "required": True}}}
    assert compatibility(v1, add_required) == "breaking", (
        "a new REQUIRED field breaks every old client that does not send it")
    reasons = breaking_changes(v1, add_required)
    assert any("region" in reason and "required" in reason for reason in reasons), reasons
    now_required = {"fields": {"id": {"type": "string", "required": True},
                               "total": {"type": "number", "required": True}}}
    assert compatibility(v1, now_required) == "breaking", "optional -> required is breaking"


def check_contract_removal_and_type() -> None:
    from contract import compatibility

    v1 = {"fields": {"id": {"type": "string", "required": True},
                     "total": {"type": "number", "required": False}}}
    removed = {"fields": {"id": {"type": "string", "required": True}}}
    assert compatibility(v1, removed) == "breaking", "removing a field breaks consumers"
    retyped = {"fields": {"id": {"type": "string", "required": True},
                          "total": {"type": "string", "required": False}}}
    assert compatibility(v1, retyped) == "breaking", "changing a field type is breaking"
    renamed = {"fields": {"id": {"type": "string", "required": True},
                          "amount": {"type": "number", "required": False}}}
    assert compatibility(v1, renamed) == "breaking", "a rename is a remove plus an add"


def check_contract_relaxing() -> None:
    from contract import breaking_changes, compatibility

    v1 = {"fields": {"id": {"type": "string", "required": True},
                     "total": {"type": "number", "required": True}}}
    relaxed = {"fields": {"id": {"type": "string", "required": True},
                          "total": {"type": "number", "required": False}}}
    assert compatibility(v1, relaxed) == "compatible", "required -> optional is a relaxation"
    assert breaking_changes(v1, relaxed) == []
    messy = {"fields": {"id": {"type": "integer", "required": True},
                        "newreq": {"type": "string", "required": True}}}
    reasons = breaking_changes(v1, messy)
    assert reasons == sorted(reasons), "reasons must be returned in a stable order"
    assert len(reasons) == 3, (
        f"expected three independent reasons (type change, removal, new required), got {reasons}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("registry.py", "register and resolve", check_register_resolve),
    ("registry.py", "TTL expiry and heartbeats", check_expiry_and_heartbeat),
    ("registry.py", "draining and deregistering", check_draining_and_deregister),
    ("registry.py", "re-register and per-service isolation", check_reregister_and_isolation),
    ("gateway.py", "longest-prefix routing", check_gateway_routing),
    ("gateway.py", "round-robin over healthy instances", check_gateway_load_balancing),
    ("gateway.py", "retry idempotent requests on 5xx", check_gateway_retries_idempotent),
    ("gateway.py", "never retry a POST", check_gateway_does_not_retry_post),
    ("gateway.py", "never retry a 4xx", check_gateway_does_not_retry_4xx),
    ("contract.py", "additive changes are compatible", check_contract_additive),
    ("contract.py", "required fields are breaking", check_contract_required),
    ("contract.py", "removal and type changes are breaking", check_contract_removal_and_type),
    ("contract.py", "relaxations are compatible", check_contract_relaxing),
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
    print(f"\n{BOLD}Microservices From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have discovered, routed and versioned services.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
