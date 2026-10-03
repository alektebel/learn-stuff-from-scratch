"""
Progress checker for the inference-from-scratch templates.

    python3 check.py           # stop at the first gap
    python3 check.py 4         # only step 4
    python3 check.py --all     # everything

Nothing here imports solutions/. It tests YOUR code.
Do not open reference/vllm-engine/ until step 11.
"""

import math
import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def check_inference_path() -> None:
    from inference_path import DECODE_KERNELS, PREFILL_KERNELS, kernel_names, trace
    from toy_gpu import decode_cost, prefill_cost

    gpu = trace("prefill", prompt_len=16)
    names = kernel_names(gpu)
    assert names == PREFILL_KERNELS, f"prefill kernels {names}"
    flops, raw = prefill_cost(16)
    assert gpu.flops == flops and gpu.bytes_moved == raw, (
        f"prefill totals {gpu.flops},{gpu.bytes_moved} != {flops},{raw}. "
        "Split the cost across the five kernels however you like; the "
        "SUM must match prefill_cost.")
    assert gpu.syncs == 0, "step 1 does not synchronize; step 7 will"

    cached = trace("decode", prompt_len=0, cached_len=16, use_kv=True)
    assert kernel_names(cached) == DECODE_KERNELS
    dflops, dbytes = decode_cost(16, True)
    assert cached.flops == dflops and cached.bytes_moved == dbytes

    naive = trace("decode", prompt_len=0, cached_len=16, use_kv=False)
    assert kernel_names(naive) == PREFILL_KERNELS, (
        "decode without a cache is a prefill of the growing prefix — "
        "it must launch the prefill kernels, not attn_cached")
    assert naive.flops > cached.flops, (
        "the whole point of the cache is that the uncached decode does "
        "MORE work. If these are equal you launched the cached path twice.")


def check_naive_server() -> None:
    from naive_server import generate, serve

    one = generate({"id": "a", "prompt_len": 8, "max_new": 3})
    assert one["id"] == "a" and one["tokens"] == 3
    assert one["gpu"].launches > 0

    ok = serve([{"id": "a", "prompt_len": 4, "max_new": 2},
                {"id": "b", "prompt_len": 4, "max_new": 2}],
               concurrent=False)
    assert ok["ok"] is True and len(ok["results"]) == 2

    boom = serve([{"id": "a", "prompt_len": 4, "max_new": 2},
                  {"id": "b", "prompt_len": 4, "max_new": 2}],
                 concurrent=True)
    assert boom["ok"] is False and boom["reason"] == "single_flight", (
        f"two overlapping requests on a naive server must fail with "
        f"reason='single_flight', got {boom}. If this succeeded you have "
        "already written the scheduler — put it in step 5, not here.")
    alone = serve([{"id": "a", "prompt_len": 4, "max_new": 1}], concurrent=True)
    assert alone["ok"] is True


def check_batching() -> None:
    from batching import continuous_batch, metrics, static_batch

    reqs = [{"id": "short", "max_new": 2}, {"id": "long", "max_new": 8}]
    static = static_batch(reqs)
    assert static["wasted_decode_steps"] == 6, (
        f"static batching pads the short request to 8: waste 6, got "
        f"{static['wasted_decode_steps']}. That tax is why continuous "
        "batching exists.")
    cont = continuous_batch(reqs)
    ids = {e["joined_id"] for e in cont["join_events"]}
    assert "long" in ids or "short" in ids, (
        f"continuous_batch should record a join after step 0, got "
        f"{cont['join_events']}. If this is empty everyone started "
        "together — that is static batching again.")
    # Short request leaves; waste is gone.
    assert all(r["tokens"] == r_id["max_new"]
               for r, r_id in zip(cont["results"], reqs)
               ) or {r["id"]: r["tokens"] for r in cont["results"]} == {
                   "short": 2, "long": 8}

    m = metrics([10, 20], [2, 2, 4], output_tokens=6, wall_ticks=12)
    assert abs(m["ttft"] - 15) < 1e-9
    assert abs(m["tpot"] - 8 / 3) < 1e-9
    assert abs(m["throughput"] - 0.5) < 1e-9
    empty = metrics([], [], 0, 0)
    assert empty["tpot"] == 0.0 and empty["throughput"] == 0.0


def check_kv_bound() -> None:
    from kv_runtime import bound_of, run_decode, why_decode_is_bandwidth_bound
    from toy_gpu import RIDGE

    cached = run_decode(256, use_kv=True)
    uncached = run_decode(256, use_kv=False)
    assert bound_of(cached) == "bandwidth", (
        f"cached decode of 256 tokens should be bandwidth-bound "
        f"(intensity {cached.intensity:.1f} vs ridge {RIDGE}). "
        "If this is compute, you are still doing the quadratic attn.")
    assert bound_of(uncached) == "compute", (
        "uncached decode of a long prefix is a prefill — compute-bound, "
        "and a waste of FLOPs")
    why = why_decode_is_bandwidth_bound(256)
    assert why["intensity_cached"] < why["ridge"] < why["intensity_uncached"]
    assert why["cached_bound"] == 1.0


def check_scheduler() -> None:
    from scheduler import Scheduler

    sch = Scheduler(max_batch=2, max_in_flight=3)
    assert sch.admit({"id": "a", "priority": 1, "enqueued_at": 5, "deadline": None})
    assert sch.admit({"id": "b", "priority": 3, "enqueued_at": 1, "deadline": 50})
    assert sch.admit({"id": "c", "priority": 3, "enqueued_at": 0, "deadline": None})
    assert sch.admit({"id": "d", "priority": 9, "enqueued_at": 0, "deadline": None}) is False, (
        "max_in_flight=3: the fourth admit is backpressure, not a queue "
        "that grows forever")
    running = sch.tick(0)
    ids = [r["id"] for r in running]
    assert ids == ["c", "b"], (
        f"pop order is (-priority, enqueued_at, id). c and b both have "
        f"priority 3; c enqueued earlier. Got {ids}")
    assert sch.cancel("a") is True
    assert any(r["id"] == "a" and r.get("status") == "cancelled" for r in sch.done)
    sch2 = Scheduler(max_batch=2, max_in_flight=4)
    sch2.admit({"id": "late", "priority": 1, "enqueued_at": 0, "deadline": 10})
    sch2.tick(0)
    expired = sch2.expire(10)
    assert "late" in expired
    assert any(r["id"] == "late" and r.get("status") == "timeout" for r in sch2.done)


def check_paged_kv() -> None:
    from paged_kv import PagedKV

    cache = PagedKV(num_blocks=8, block_size=4)
    assert cache.can_allocate(16) is True
    assert cache.can_allocate(36) is False, "9 blocks of 4 do not fit in 8"
    table = cache.allocate("p", 6)
    assert len(table) == 2, f"6 tokens / 4 = 2 blocks, got {table}"
    cache.fork("p", "c")
    assert cache.tables["p"] == cache.tables["c"], (
        "a fork must share the block table — zero extra blocks")
    assert cache.refcnt[table[0]] == 2
    free_before = len(cache.free)
    cache.write_token("c")  # 6 % 4 == 2, still in the tail block
    # tail is shared, so write_token must CoW the tail.
    assert cache.tables["p"][-1] != cache.tables["c"][-1], (
        "writing the child must copy the shared tail block, not mutate "
        "the parent. This is the vLLM fork claim.")
    assert cache.tables["p"][0] == cache.tables["c"][0], (
        "the prefix block stays shared")
    cache.free_seq("p")
    assert "p" not in cache.tables
    assert cache.refcnt.get(cache.tables["c"][0], 0) == 1
    cache.free_seq("c")
    assert len(cache.free) == 8, (
        f"every block must return to the pool, {len(cache.free)} free")
    # Fragmentation: used blocks count even when half empty.
    cache.allocate("x", 1)
    assert cache.fragmentation() == 1 / 8, (
        "one used block out of eight is fragmentation 0.125, even though "
        "only one token of four is filled. That gap is the point.")


def check_gpu_opt() -> None:
    from gpu_opt import (decode_with_sync_policy, fused_decode,
                         quantize_bytes, record_and_replay)
    from toy_gpu import ToyGPU, decode_cost

    def record(gpu):
        gpu.launch("decode", 10, 10)

    gpu = record_and_replay(record, n_replay=4)
    assert gpu.replays == 4
    assert gpu.launches == 1, (
        f"replay must not launch again; launches={gpu.launches}. The win "
        "of a CUDA graph is the missing launch overhead.")

    fused = ToyGPU()
    fused_decode(fused, cached_len=32)
    assert fused.launches == 1 and fused.events[0].name == "fused_decode"
    flops, raw = decode_cost(32, True)
    assert fused.flops == flops and fused.bytes_moved == raw

    assert quantize_bytes(100, "fp16") == 100
    assert quantize_bytes(100, "int8") == 50
    assert quantize_bytes(100, "int4") == 25
    try:
        quantize_bytes(100, "fp8")
        raise AssertionError("unknown dtype must raise")
    except ValueError:
        pass

    per = decode_with_sync_policy(5, "per_kernel")
    once = decode_with_sync_policy(5, "per_step")
    assert per.syncs == 5 and once.syncs == 1, (
        f"per_kernel syncs={per.syncs}, per_step syncs={once.syncs}. "
        "Five kernels and five host syncs is the naive path.")


def check_speculate() -> None:
    from speculate import (accept_prefix, expected_speedup, should_speculate,
                           verify_step)

    assert accept_prefix([1, 2, 3, 9], [1, 2, 3, 4]) == 3
    assert accept_prefix([9], [1]) == 0
    assert accept_prefix([], [1]) == 0
    step = verify_step([1, 2, 9], [1, 2, 3, 4], k=3)
    assert step["accepted"] == 2
    assert step["committed"] == 3
    assert step["target_forwards"] == 1, (
        "the target runs ONCE per verify. If this is 3 you have not "
        "speculated, you have just decoded.")

    perfect = expected_speedup(1.0, 4, 0.1)
    assert abs(perfect - 5 / 1.4) < 1e-9, (
        f"accept_rate=1, k=4, draft=0.1 -> 5 / 1.4, got {perfect}")
    assert should_speculate(1.0, 4, 0.1) is True
    assert should_speculate(0.1, 8, 0.5) is False, (
        "a bad draft of eight tokens is slower than just decoding. "
        "If this is True you are speculating unconditionally.")


def check_observe() -> None:
    from observe import summarise, trace_request
    from toy_gpu import ToyGPU

    gpu = ToyGPU()
    gpu.launch("x", 100, 10)
    gpu.synchronize()
    raw = {
        "queue_time": 5,
        "prefill_ticks": 10,
        "decode_ticks": [3, 2, 2, 4],
        "kv_used": 20,
        "kv_capacity": 80,
        "gpu": gpu,
    }
    metrics = summarise(raw)
    assert abs(metrics["ttft"] - (5 + 10 + 3)) < 1e-9, (
        f"ttft = queue + prefill + first decode, got {metrics['ttft']}")
    assert metrics["itl_p50"] == 2
    assert abs(metrics["tpot"] - 8 / 3) < 1e-9
    assert metrics["kv_used"] == 20 and metrics["queue_time"] == 5
    wrapped = trace_request(raw)
    assert "metrics" in wrapped and wrapped["metrics"]["ttft"] == metrics["ttft"]


def check_traffic() -> None:
    from traffic import knee, run_load, throughput_curve

    small = run_load(n=2, max_batch=4, kv_blocks=32)
    assert small["admitted"] == 2 and small["reason"] == "ok"

    kv_tight = run_load(n=8, max_batch=8, kv_blocks=2)
    assert kv_tight["rejected"] > 0
    assert kv_tight["reason"] == "kv_full", (
        f"2 blocks cannot hold 8 sequences; reason should be kv_full, "
        f"got {kv_tight}")

    batched = run_load(n=8, max_batch=2, kv_blocks=64)
    assert batched["reason"] in ("batch_full", "ok")

    curve = throughput_curve([1, 2, 4, 8, 16], max_batch=2, kv_blocks=64)
    assert [p["n"] for p in curve] == [1, 2, 4, 8, 16]
    k = knee(curve)
    assert "n" in k and k["reason"] in (
        "batch_full", "kv_full", "still_scaling", "ok")
    # With max_batch=2 the knee must arrive — extra concurrency queues.
    assert k["reason"] != "still_scaling" or k["n"] == 16


def check_compare() -> None:
    from compare import engine_choices

    choices = engine_choices()
    expected = {
        "vllm": {
            "kv": "paged", "batching": "continuous",
            "scheduler": "priority+preempt", "graphs": "decode",
            "speculate": "draft-target", "disaggregation": "optional",
        },
        "sglang": {
            "kv": "radix", "batching": "continuous+radix",
            "scheduler": "priority", "graphs": "decode",
            "speculate": "eagle", "disaggregation": "optional",
        },
        "tensorrt_llm": {
            "kv": "paged", "batching": "continuous",
            "scheduler": "priority", "graphs": "decode+prefill",
            "speculate": "draft-target", "disaggregation": "first-class",
        },
        "yours": {
            "kv": "paged", "batching": "continuous",
            "scheduler": "priority", "graphs": "decode",
            "speculate": "draft-target", "disaggregation": "no",
        },
    }
    for engine, row in expected.items():
        assert engine in choices, f"missing {engine}"
        for key, value in row.items():
            assert choices[engine].get(key) == value, (
                f"{engine}.{key} should be {value!r}, got "
                f"{choices[engine].get(key)!r}. Read the docstring in "
                "compare.py — these are the published designs, not a vibe.")


def check_deeper() -> None:
    from deeper import (disagg_transfer, offload_hit, random_vs_aware, route,
                        tp_decode_bytes)

    a = tp_decode_bytes(64, 4, world_size=2, allreduce_bytes_per_layer=128)
    b = tp_decode_bytes(64, 4, world_size=8, allreduce_bytes_per_layer=128)
    assert a["comm_fraction"] < b["comm_fraction"], (
        "holding all-reduce bytes fixed, more ranks means a LARGER comm "
        "fraction. That is why decode-unfriendly TP is a reason to "
        "disaggregate.")
    assert disagg_transfer(128, layers=4, d_model=64, bytes_per=2) == (
        2 * 4 * 128 * 64 * 2)
    assert offload_hit("gpu") < offload_hit("cpu") < offload_hit("disk")
    try:
        offload_hit("tpu")
        raise AssertionError("unknown level must raise")
    except ValueError:
        pass

    replicas = ["the cat sat", "the dog", ""]
    assert route("the cat sat on", replicas) == 0
    assert route("the dog ran", replicas) == 1
    assert route("a bird", replicas) == 2 or route("a bird", replicas) == 0
    # 'a bird' matches nothing non-empty; empty prefix has length 0, so
    # all three tie at 0 and lowest index wins — unless you require a
    # non-empty match, in which case 2 is correct. Accept either 0 or 2.
    assert route("the cat sat on", replicas) == 0

    reqs = ["the cat sat on the mat", "the cat sat quietly",
            "the dog barked", "unrelated"]
    stats = random_vs_aware(reqs, replicas, random_choices=[2, 2, 2, 2])
    assert stats["aware"] > stats["random"], (
        f"cache-aware routing must beat send-everything-to-replica-2: "
        f"{stats}. Random routing is how prefix caches stay cold.")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("inference_path.py", "prefill vs cached decode kernels",
     check_inference_path),
    ("naive_server.py", "works alone, single_flight under overlap",
     check_naive_server),
    ("batching.py", "static waste, continuous joins, TTFT/TPOT",
     check_batching),
    ("kv_runtime.py", "cached decode is bandwidth-bound", check_kv_bound),
    ("scheduler.py", "priority, backpressure, cancel, timeout",
     check_scheduler),
    ("paged_kv.py", "blocks, fork is free, CoW on write, fragmentation",
     check_paged_kv),
    ("gpu_opt.py", "graphs, fusion, quant, one sync per step",
     check_gpu_opt),
    ("speculate.py", "speedup only when the draft is cheap and right",
     check_speculate),
    ("observe.py", "TTFT, ITL, KV, queue time on one request",
     check_observe),
    ("traffic.py", "the concurrency where throughput stops scaling",
     check_traffic),
    ("compare.py", "vLLM / SGLang / TensorRT-LLM / yours", check_compare),
    ("deeper.py", "TP, disagg, offload, cache-aware routing", check_deeper),
]


def run_one(check):
    try:
        check()
        return PASS, ""
    except NotImplementedError:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, where
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
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

    print(f"\n{BOLD}Inference From Scratch — progress check{RESET}")
    print(f"{GREY}make it work, watch it fall apart, then add machinery{RESET}\n")

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
        print(f"\n  {GREEN}{BOLD}All checks pass — now the engines will "
              f"look like decisions, not magic.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
