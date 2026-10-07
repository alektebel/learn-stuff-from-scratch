"""
Progress checker for the prefix-caching proxy templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 2         # run only step 2
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure):
that is simply the next thing to write. Nothing here imports solutions/. It
tests YOUR code, and it starts and stops real servers on ephemeral 127.0.0.1
ports with short timeouts, so it cannot hang.
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
# Step 1: the proxy serves a real request
# ---------------------------------------------------------------------------

def check_proxy_roundtrip() -> None:
    from replica import model_output, post_json, serve_replicas, stop_replicas
    from policy import RoundRobinPolicy
    from proxy import Proxy, ProxyServer

    servers = serve_replicas(3, cache_capacity=200)
    try:
        proxy = Proxy([server.replica for server in servers], RoundRobinPolicy())
        proxy_server = ProxyServer(proxy).start()
        try:
            prompt = [i * 7 + 3 for i in range(20)]
            reply = post_json(proxy_server.port, "/generate",
                              {"prompt": prompt, "gen_len": 12}, timeout=5)
            assert reply["output"] == model_output(prompt, 12), (
                "the proxy returned a different generation than a replica produces: "
                "forward the same prompt and gen_len you received")
            assert reply["reused"] + reply["recomputed"] == len(prompt), (
                f"reused({reply['reused']}) + recomputed({reply['recomputed']}) != "
                f"prompt length ({len(prompt)}): the replica did not see the whole prompt")
            assert 0 <= reply["replica"] < 3, (
                f"reply names replica {reply['replica']}; did you forward to a real replica?")
            assert proxy.requests == 1, (
                f"the proxy reports {proxy.requests} requests after one client call")
        finally:
            proxy_server.stop()
    finally:
        stop_replicas(servers)


# ---------------------------------------------------------------------------
# Steps 2-3: the routing policy itself
# ---------------------------------------------------------------------------

def check_longest_prefix_routing() -> None:
    from replica import Replica
    from policy import LongestPrefixPolicy

    replicas = [Replica(i, cache_capacity=1000) for i in range(3)]
    replicas[0].cache.insert([1, 2, 3, 4, 5])
    replicas[1].cache.insert([1, 2, 3, 4, 5, 6, 7, 8, 9])
    replicas[2].cache.insert([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    policy = LongestPrefixPolicy()
    prompt = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    chosen = policy.choose(replicas, prompt)
    assert chosen.id == 2, (
        f"replica 2 shares 12 tokens, replica 1 shares 9 and replica 0 shares 5, "
        f"but the policy chose replica {chosen.id}: pick the LONGEST match, not the first "
        "replica that matches anything")

    tie = [Replica(i, cache_capacity=1000) for i in range(2)]
    for replica in tie:
        replica.cache.insert([1, 2, 3, 4])
    tie[0].load = 50
    tie[1].load = 5
    chosen = policy.choose(tie, [1, 2, 3, 4, 99])
    assert chosen.id == 1, (
        "two replicas share the same 4-token prefix; the tie-break should send the "
        f"request to the least-loaded one (replica 1), not replica {chosen.id}")


def check_cold_fallback() -> None:
    from replica import Replica
    from policy import LongestPrefixPolicy

    replicas = [Replica(i, cache_capacity=200) for i in range(3)]
    replicas[0].load = 100
    replicas[1].load = 10
    replicas[2].load = 50
    policy = LongestPrefixPolicy()
    chosen = policy.choose(replicas, [700_000, 700_001, 700_002])
    assert chosen.id == 1, (
        "no replica holds any part of this prompt, so the policy must fall back to the "
        f"least-loaded replica (1); it chose replica {chosen.id}. A cold request is not a "
        "0-token match to be handed to replica 0")

    for replica in replicas:
        replica.load = 0
    chosen = policy.choose(replicas, [800_000])
    assert chosen.id == 0, (
        f"with equal loads the fallback should break ties by lowest id; chose {chosen.id}")


# ---------------------------------------------------------------------------
# Steps 4-5: the proxy as a whole
# ---------------------------------------------------------------------------

def check_proxy_routes_on_prompt() -> None:
    """A previous response must not decide the next request's replica."""
    from replica import post_json, serve_replicas, stop_replicas
    from policy import LongestPrefixPolicy
    from proxy import Proxy, ProxyServer

    servers = serve_replicas(2, cache_capacity=400)
    try:
        replicas = [server.replica for server in servers]
        prompt_b = [600_000 + i for i in range(40)]
        replicas[1].cache.insert(prompt_b)          # replica 1 is warm for B
        proxy = Proxy(replicas, LongestPrefixPolicy())
        proxy_server = ProxyServer(proxy).start()
        try:
            prompt_a = [1_000 + i for i in range(40)]  # disjoint from B and B's output
            reply_a = post_json(proxy_server.port, "/generate",
                                {"prompt": prompt_a, "gen_len": 16}, timeout=5)
            assert reply_a["replica"] == 0, (
                "both replicas are cold for A, so the least-loaded tie picks replica 0; "
                f"got replica {reply_a['replica']}")
            reply_b = post_json(proxy_server.port, "/generate",
                                {"prompt": prompt_b, "gen_len": 16}, timeout=5)
            assert reply_b["replica"] == 1, (
                f"prompt B shares all 40 tokens with replica 1, but the proxy chose replica "
                f"{reply_b['replica']}: route on the incoming PROMPT, not on the previous "
                "response's tokens")
            assert reply_b["reused"] == 40, (
                f"replica 1 should have reused all 40 prompt tokens, reused {reply_b['reused']}")
        finally:
            proxy_server.stop()
    finally:
        stop_replicas(servers)


def check_cache_hit_improvement() -> None:
    from replica import Replica
    from policy import make_policy
    from workload import traced_workload

    def replay(policy_name, trace, n=4, capacity=120):
        replicas = [Replica(i, cache_capacity=capacity) for i in range(n)]
        policy = make_policy(policy_name)
        reused = 0
        total = 0
        for request in trace:
            replica = policy.choose(replicas, request["prompt"])
            reply = replica.handle(request["prompt"], request["gen_len"])
            reused += reply["reused"]
            total += reply["reused"] + reply["recomputed"]
        return reused, total

    trace = traced_workload()
    rr_reused, total = replay("round_robin", trace)
    lp_reused, _ = replay("longest_prefix", trace)
    assert lp_reused >= 2 * rr_reused, (
        f"longest-prefix reused {lp_reused}/{total} prompt tokens, round-robin "
        f"{rr_reused}/{total}: less than the 2x this trace should show. Does the policy "
        "ignore the replica's cache, or scatter shared prefixes so each replica evicts "
        "the others' system prompts?")


# ---------------------------------------------------------------------------

CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("proxy.py", "a client gets the right response through the proxy", check_proxy_roundtrip),
    ("policy.py", "longest shared prefix wins", check_longest_prefix_routing),
    ("policy.py", "cold request falls back to least loaded", check_cold_fallback),
    ("proxy.py", "routing follows the prompt, not the last response", check_proxy_routes_on_prompt),
    ("policy.py", "cache-hit gain over round-robin on the trace", check_cache_hit_improvement),
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
    print(f"\n{BOLD}Prefix-Caching Proxy — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — the proxy routes by prefix and the numbers move.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
