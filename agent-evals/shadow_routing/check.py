"""Runnable check for shadow_routing (standard library only).

    python3 agent-evals/shadow_routing/check.py

Asserts the properties #2 promises: the primary is byte-identical with or without
shadowing, sampling is deterministic and order-independent, and the report keeps cost and
quality apart. Exits non-zero with a message on the first failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # agent-evals/

from shadow_routing import ShadowConfig, compare, is_sampled, sampled_ids, shadow_run  # noqa: E402
from simulated_service import SimulatedService  # noqa: E402


def check() -> None:
    service = SimulatedService(seed=4)
    requests = service.traffic(per_segment=80, segments=6)
    off = ShadowConfig(fraction=0.0)
    on = ShadowConfig(fraction=0.25)

    # 1. The primary path is byte-identical: shadowing changes nothing the incumbent sees.
    assert shadow_run(service, requests, off)[0] == shadow_run(service, requests, on)[0], \
        "shadowing moved the primary"

    # 2. Sampling is deterministic and independent of request order.
    ids_a = sampled_ids(requests, 0.25, seed=0)
    ids_b = sampled_ids(list(reversed(requests)), 0.25, seed=0)
    assert ids_a == list(reversed(ids_b)), "sampling depends on order"
    assert 0 < len(ids_a) < len(requests)
    assert is_sampled("x", 1.0, 0) and not is_sampled("x", 0.0, 0)

    # 3. The report separates cost from quality, and the deltas have the right sign.
    cmp = compare(service, requests, on)
    assert cmp.n_sampled == len(ids_a)
    assert cmp.shadow["cost_eur"] > cmp.primary["cost_eur"], "large is not dearer"
    assert cmp.delta_cost_eur > 0 and cmp.delta_success == cmp.shadow["success"] - cmp.primary["success"]
    assert cmp.fixed + cmp.broke == len(cmp.disagreements)
    text = cmp.report()
    assert "success" in text and "cost EUR" in text and "latency ms" in text

    # 4. A slow shadow adds to the shadow column and to nothing else.
    slow = compare(service, requests, ShadowConfig(fraction=1.0, shadow="large"))
    fast = compare(service, requests, ShadowConfig(fraction=1.0, shadow="small"))
    assert slow.primary["latency_ms"] == fast.primary["latency_ms"], "shadow moved primary latency"
    assert slow.shadow["latency_ms"] > fast.shadow["latency_ms"], "shadow latency not its own"


if __name__ == "__main__":
    try:
        check()
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print("shadow_routing: OK (primary byte-identical, deterministic sample, cost and quality apart)")
