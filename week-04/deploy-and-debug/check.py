"""
Progress checker for the deploy-and-debug templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

Nothing here imports solutions/. It tests YOUR code.
"""

import math
import pathlib
import shutil
import sys
import traceback

# Always read the learner's source fresh. Python validates cached bytecode on
# (mtime, size), so an edit that keeps a file the same size within the same
# second can be masked by a stale __pycache__ — and a checker you cannot trust
# is worse than no checker.
sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"

GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# Step 1-2: capacity.py
# ---------------------------------------------------------------------------

def check_kv_math() -> None:
    from capacity import (MODELS, kv_bytes_per_token, kv_cache_capacity,
                          max_concurrent_sequences)

    layers, kv_heads, head_dim, weights = MODELS["Llama-3-8B"]
    per_token = kv_bytes_per_token(layers, kv_heads, head_dim)
    assert per_token == 131072, (
        f"Llama-3-8B should be 131,072 bytes/token (128 KiB), got {per_token:,}. "
        "Formula: 2 x layers x KV_heads x head_dim x dtype_bytes. If you got "
        "524,288 you used the 32 query heads instead of the 8 KV heads — that "
        "sizes your fleet 4x too large.")
    assert kv_bytes_per_token(32, 8, 128, dtype_bytes=1) == per_token // 2, \
        "fp8 should halve the per-token cost"

    kv = kv_cache_capacity(80.0, weights, 0.90, activation_gib=2.0)
    assert abs(kv - 54.0) < 0.01, \
        f"80 x 0.90 - 16 - 2 = 54.0 GiB, got {kv}"
    assert kv_cache_capacity(20.0, 140.0, 0.90) == 0.0, \
        "weights larger than the card must floor at 0, not go negative"

    seqs_2k = max_concurrent_sequences(kv, per_token, 2048)
    seqs_32k = max_concurrent_sequences(kv, per_token, 32768)
    assert seqs_2k == 216, f"expected 216 sequences at 2k context, got {seqs_2k}"
    assert seqs_32k == 13, f"expected 13 at 32k context, got {seqs_32k}"
    assert seqs_2k == seqs_32k * 16 + 8, (
        "2k vs 32k should differ by ~16x — that ratio is why max_model_len is "
        "a capacity decision")
    try:
        max_concurrent_sequences(kv, per_token, 0)
        raise AssertionError("a non-positive context length must raise ValueError")
    except ValueError:
        pass


def check_fleet_and_quorum() -> None:
    from capacity import (quorum_is_strict, rebalance_cost, replicas_needed,
                          storage_per_node, throughput_estimate,
                          tolerable_failures)

    estimate = throughput_estimate(concurrent=216, output_tokens=200,
                                   prefill_tokens=1800)
    assert abs(estimate["service_ms"] - 1662.0) < 1.0, \
        f"1800*0.09 + 200*7.5 = 1662ms, got {estimate['service_ms']}"
    assert abs(estimate["requests_per_s"] - 130.0) < 1.0, \
        f"216 * 1000 / 1662 = 130 req/s, got {estimate['requests_per_s']}"

    assert replicas_needed(400, 130.0, headroom=0.7) == 5, \
        "400 req/s at 130/replica with 0.7 headroom needs 5 replicas"
    assert replicas_needed(400, 130.0, headroom=1.0) == 4, \
        "at 1.0 headroom, 4 — and 77% utilisation, which is already too hot"
    assert replicas_needed(1, 1000.0) == 1, "never return 0 replicas"
    for bad in (0.0, 1.5, -1):
        try:
            replicas_needed(10, 5, headroom=bad)
            raise AssertionError(f"headroom={bad} must raise ValueError")
        except ValueError:
            pass

    assert quorum_is_strict(3, 2, 2) and not quorum_is_strict(3, 1, 1)
    assert tolerable_failures(3, 2, 2)["either"] == 1, (
        "N=3 R=2 W=2 survives exactly ONE node loss. If you computed 2, "
        "re-read the formula — this is the number that ends up in an "
        "availability review.")
    assert tolerable_failures(5, 3, 3)["either"] == 2
    assert tolerable_failures(3, 3, 3)["either"] == 0, \
        "R=W=N tolerates nothing"
    assert tolerable_failures(3, 1, 3)["reads"] == 2, \
        "R=1 tolerates 2 read failures even though writes tolerate none"

    gib = storage_per_node(500_000_000, 1024, n=3, num_nodes=6)
    assert 350 < gib < 380, (
        f"500M keys x 1KiB x 3 replicas x 1.5 compaction / 6 nodes should be "
        f"~357 GiB, got {gib:.0f}")

    cost = rebalance_cost(1_000_000, 4, adding=1)
    assert abs(cost["fraction_moved"] - 0.2) < 1e-9, \
        f"adding the 5th node moves 1/5, got {cost['fraction_moved']}"


# ---------------------------------------------------------------------------
# Step 3-4: metrics.py
# ---------------------------------------------------------------------------

def check_percentiles() -> None:
    from metrics import percentile, summarize, why_not_the_mean

    values = list(range(1, 101))
    assert percentile(values, 0.0) == 1
    assert percentile(values, 1.0) == 100
    assert percentile(values, 0.5) in (50, 51), \
        f"median of 1..100 should be ~50, got {percentile(values, 0.5)}"
    assert percentile([], 0.99) == 0.0, "empty input must not crash"
    assert percentile([7.0], 0.99) == 7.0

    stats = summarize(values)
    assert stats["count"] == 100 and stats["max"] == 100
    assert abs(stats["mean"] - 50.5) < 1e-9
    assert summarize([])["count"] == 0, "empty input must not crash"

    skewed = [10.0] * 99 + [1000.0]
    hidden = why_not_the_mean(skewed)
    assert hidden["p99"] >= 1000.0 or hidden["p99"] >= 10.0
    assert hidden["fraction_above_mean"] < 0.05, (
        "with one huge outlier, almost nothing is above the mean — that is "
        "exactly how an average hides a tail")


def check_latency_effects() -> None:
    from metrics import fanout_tail, queueing_delay

    assert abs(queueing_delay(0.5, 100) - 100.0) < 1e-9, \
        "at 50% utilisation you wait 1x the service time"
    assert abs(queueing_delay(0.9, 100) - 900.0) < 1e-6, \
        "at 90%, 9x — this is the number capacity plans forget"
    assert queueing_delay(1.0, 100) == float("inf")
    assert queueing_delay(0.0, 100) == 0.0

    one = fanout_tail(900, 120, 1)
    hundred = fanout_tail(900, 120, 100)
    assert one < hundred, "more fan-out must mean a worse effective tail"
    assert hundred > 500, (
        f"at fanout 100 the effective tail should approach p99, got {hundred:.0f}")
    assert abs(fanout_tail(900, 120, 0) - 120.0) < 1e-9, \
        "zero fan-out is just the median"


def check_slo() -> None:
    from metrics import SLO, burn_rate

    slo = SLO("api", threshold_ms=500, target=0.999, window_days=30)
    assert abs(slo.allowed_failure_fraction - 0.001) < 1e-12
    assert abs(slo.budget_minutes - 43.2) < 0.1, (
        f"99.9% over 30 days is 43.2 minutes, got {slo.budget_minutes:.1f}. "
        "Say that number out loud next time someone proposes 99.99%.")
    for bad in (0.0, 1.0, 1.5):
        try:
            SLO("x", 100, target=bad)
            raise AssertionError(f"target={bad} must raise ValueError")
        except ValueError:
            pass

    clean = slo.evaluate([100.0] * 1000, errors=0)
    assert clean["met"] and clean["budget_used"] == 0.0

    result = slo.evaluate([100.0] * 999 + [900.0], errors=0)
    assert result["bad_events"] == 1
    assert abs(result["budget_used"] - 1.0) < 0.01, (
        "1 bad event in 1000 at a 99.9% target is exactly 100% of the budget, "
        f"got {result['budget_used']:.2f}")
    assert slo.evaluate([], errors=0)["met"], "no traffic is not a violation"

    assert abs(burn_rate(1.0, 30 * 24) - 1.0) < 1e-9, \
        "using the whole budget over the whole window is burn rate 1.0"
    assert abs(burn_rate(0.05, 1.0) - 36.0) < 0.1, \
        f"5% of budget in 1 hour is 36x, got {burn_rate(0.05, 1.0):.1f}"
    assert burn_rate(0.002, 1.0) < 14.4, \
        "0.2% in an hour is 1.4x — below the page threshold"


# ---------------------------------------------------------------------------
# Step 5-6: diagnose.py
# ---------------------------------------------------------------------------

def check_diagnose_serving() -> None:
    from deployment import SERVING_FAULTS, ServingDeployment
    from diagnose import Diagnosis, diagnose

    wrong = []
    for fault in SERVING_FAULTS:
        snapshot = ServingDeployment.with_fault(fault).observe()
        result = diagnose(snapshot)
        assert isinstance(result, Diagnosis), \
            f"diagnose must return a Diagnosis, got {type(result).__name__}"
        if result.cause != fault:
            wrong.append(f"{fault} -> diagnosed as {result.cause}")
        assert result.evidence, (
            f"the {fault} diagnosis has no evidence. A diagnosis nobody else "
            "can check is not much use at 3am.")
    assert not wrong, "misdiagnosed:\n      " + "\n      ".join(wrong)


def check_confusable_serving() -> None:
    """The pair that matters: undersized KV vs plain overload."""
    from deployment import (OVERLOADED, UNDERSIZED_KV, ServingDeployment)
    from diagnose import diagnose

    starved = ServingDeployment.with_fault(UNDERSIZED_KV).observe()
    flooded = ServingDeployment.with_fault(OVERLOADED).observe()

    assert starved["preempt_per_s"] > 1 and flooded["preempt_per_s"] > 1, \
        "setup: both faults should show preemption"
    assert diagnose(starved).cause == UNDERSIZED_KV
    assert diagnose(flooded).cause == OVERLOADED, (
        "overload was diagnosed as undersized KV. Both show preemption and "
        "timeouts; the separator is max_concurrent_seqs — 1 sequence means the "
        "budget is wrong, a normal number means the traffic is too high. "
        "Fixing the wrong one wastes a scale-up or ships a no-op config change.")

    # ...and it must not fire on a healthy fleet at a different seed.
    for seed in (7, 21, 99):
        healthy = ServingDeployment.with_fault("healthy", seed=seed).observe()
        assert diagnose(healthy).cause == "healthy", \
            f"a healthy fleet at seed {seed} was diagnosed as " \
            f"{diagnose(healthy).cause}"


def check_diagnose_store() -> None:
    from deployment import STORE_FAULTS, StoreDeployment
    from diagnose import diagnose

    wrong = []
    for fault in STORE_FAULTS:
        snapshot = StoreDeployment.with_fault(fault).observe()
        result = diagnose(snapshot)
        if result.cause != fault:
            wrong.append(f"{fault} -> diagnosed as {result.cause}")
        assert result.action, f"the {fault} diagnosis has no action"
    assert not wrong, "misdiagnosed:\n      " + "\n      ".join(wrong)


def check_confusable_store() -> None:
    """The other pair: a dead node vs a quorum that never tolerated one."""
    from deployment import NODE_DOWN, QUORUM_TOO_STRICT, StoreDeployment
    from diagnose import diagnose

    down = StoreDeployment.with_fault(NODE_DOWN).observe()
    strict = StoreDeployment.with_fault(QUORUM_TOO_STRICT).observe()

    assert down["nodes_up"] == strict["nodes_up"], \
        "setup: identical topology, one node down in both"
    assert down["hint_queue_total"] == strict["hint_queue_total"], \
        "setup: identical hint backlog"
    assert diagnose(down).cause == NODE_DOWN
    assert diagnose(strict).cause == QUORUM_TOO_STRICT, (
        "these two have IDENTICAL node counts and hint queues. The only "
        "difference is R and W. Your rule has to read the configuration, not "
        "just the symptoms — the fix is a config change in one case and "
        "hardware replacement in the other.")


# ---------------------------------------------------------------------------
# Step 7-8: rollout.py
# ---------------------------------------------------------------------------

def check_health_checks() -> None:
    from rollout import HealthCheck, probe_plan

    liveness = HealthCheck("x", "liveness", 10, failure_threshold=3)
    assert liveness.record(False) == "none", "one failure is not enough"
    assert liveness.record(False) == "none"
    assert liveness.record(False) == "restart", \
        "at the threshold, liveness restarts the container"

    reset = HealthCheck("x", "liveness", 10, failure_threshold=3)
    reset.record(False)
    reset.record(False)
    assert reset.record(True) == "none"
    assert reset.record(False) == "none", (
        "a healthy probe must RESET the counter. Without that, a flaky network "
        "eventually restarts every replica you have.")

    readiness = HealthCheck("x", "readiness", 3, failure_threshold=2)
    readiness.record(False)
    assert readiness.record(False) == "remove_from_lb", (
        "readiness drains traffic; it must NOT restart. A replica with a full "
        "KV cache is busy, not broken.")

    try:
        HealthCheck("x", "nonsense", 3)
        raise AssertionError("an unknown probe kind must raise ValueError")
    except ValueError:
        pass

    plan = probe_plan(100.0)
    assert set(plan) == {"startup", "readiness", "liveness"}
    startup_budget = plan["startup"]["period_s"] * plan["startup"]["failure_threshold"]
    assert startup_budget > 100, (
        f"the startup probe tolerates only {startup_budget:.0f}s but the model "
        "takes 100s to load. It will be killed mid-load, forever, and the crash "
        "loop will look exactly like a bad image.")
    readiness_budget = (plan["readiness"]["period_s"]
                        * plan["readiness"]["failure_threshold"])
    assert readiness_budget < 30, \
        "readiness should drain fast — a broken replica must leave the LB quickly"


def check_canary() -> None:
    import random as _random

    from rollout import (Rollout, canary_verdict, compare_versions,
                         enough_samples)

    rng = _random.Random(3)
    baseline = [rng.gauss(120, 25) for _ in range(20000)]

    assert not enough_samples(90, 0.001), \
        "90 requests cannot detect a change in a 0.1% error rate"
    assert enough_samples(20000, 0.001), "20k requests can"
    assert enough_samples(100, 0.5), "at a 50% baseline rate, 100 is plenty"

    same = compare_versions(baseline, [rng.gauss(120, 25) for _ in range(20000)],
                            20, 20)
    verdict, _ = canary_verdict(same)
    assert verdict == "promote", f"an identical build should promote, got {verdict}"

    slow = compare_versions(baseline, [rng.gauss(120, 45) for _ in range(20000)],
                            20, 20)
    assert canary_verdict(slow)[0] == "rollback", "a 27% p99 regression must roll back"

    errors = compare_versions(baseline, [rng.gauss(121, 25) for _ in range(20000)],
                              20, 220)
    assert canary_verdict(errors)[0] == "rollback", "a 1% error delta must roll back"

    tiny = compare_versions(baseline, [rng.gauss(500, 25) for _ in range(90)], 20, 0)
    assert tiny["p99_ratio"] > 2.0, "setup: this canary is far slower"
    assert canary_verdict(tiny)[0] == "hold", (
        "this canary is 3x slower but has only seen 90 requests — the verdict "
        "must be 'hold', not 'rollback'. Deciding on 90 samples is guessing, "
        "whichever way it goes.")

    def observe(fraction: float):
        degraded = fraction >= 0.25
        canary = [rng.gauss(300 if degraded else 122, 30) for _ in range(20000)]
        return compare_versions(baseline, canary, 20, 400 if degraded else 21)

    result = Rollout().run(observe)
    assert result["outcome"] == "rolled_back", \
        f"a build that fails at 25% must roll back, got {result['outcome']}"
    assert result["failed_at"] == 0.25, \
        f"it should fail at the 25% stage, got {result['failed_at']}"
    assert len(result["history"]) == 3, (
        "history should record 1%, 5% and 25% — staging is what kept this off "
        "100% of traffic; a single 1% canary would have shipped it")


def check_rollback_triggers() -> None:
    from metrics import SLO
    from rollout import rollback_triggers

    slo = SLO("api", threshold_ms=500, target=0.999)

    should, _ = rollback_triggers(slo, 0.05, 1.0)          # 36x
    assert should, "36x burn rate must auto-revert"

    should, reason = rollback_triggers(slo, 0.015, 1.0)    # 10.8x
    assert not should, (
        "10.8x is above the paging threshold but below auto-revert. Reverting "
        "automatically here is how a deploy system fights a human mid-incident.")
    assert "page" in reason.lower() or "not" in reason.lower()

    should, _ = rollback_triggers(slo, 0.002, 1.0)         # 1.4x
    assert not should, "1.4x is within budget"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("capacity.py", "KV cache and batch-size math", check_kv_math),
    ("capacity.py", "fleet sizing and quorum tolerance", check_fleet_and_quorum),
    ("metrics.py", "percentiles and summaries", check_percentiles),
    ("metrics.py", "queueing and fan-out tails", check_latency_effects),
    ("metrics.py", "SLOs, budgets and burn rate", check_slo),
    ("diagnose.py", "diagnose 6 serving faults", check_diagnose_serving),
    ("diagnose.py", "undersized KV vs overload", check_confusable_serving),
    ("diagnose.py", "diagnose 5 store faults", check_diagnose_store),
    ("diagnose.py", "node down vs strict quorum", check_confusable_store),
    ("rollout.py", "liveness vs readiness probes", check_health_checks),
    ("rollout.py", "canary analysis and staging", check_canary),
    ("rollout.py", "budget-based auto-rollback", check_rollback_triggers),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

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
    except Exception as exc:                       # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}Deploy & Debug — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None

    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue

        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<20} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<20} {title}")
            print(f"      {GREY}not implemented yet"
                  f"{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<20} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you can size, measure, diagnose and ship.{RESET}")
        print(f"  {GREY}Now run each file's own demo to see the measurements,{RESET}")
        print(f"  {GREY}then compare your approach with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The TODO comments in that file walk through it. "
              f"Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
