"""Writes logs/app.log (~60k lines, ~5 MB) and config/upstreams.json.

The answer is deliberately not findable by reading the head or tail of the log: the
failing host's TIMEOUT lines and its largest OK latency are spread through the middle.
EXPECTED_HOST / EXPECTED_TIMEOUT are asserted by tests/test_generators.py.
"""

import json
import random
from pathlib import Path

HOSTS = {f"svc-{n}.internal": t for n, t in zip(
    ["auth", "billing", "search", "media", "geo", "mail", "ledger", "users"],
    [800, 1200, 600, 2500, 700, 900, 1500, 500])}
BAD = "svc-ledger.internal"
EXPECTED_HOST = BAD
EXPECTED_TIMEOUT = 3400  # 2 * 1687 = 3374 -> 3400


def build(dest: Path) -> None:
    rng = random.Random(19)
    lines = []
    names = list(HOSTS)
    for i in range(60_000):
        host = rng.choice(names)
        rid = f"{rng.getrandbits(64):016x}"
        ts = f"2025-03-{1 + i // 2400:02d}T{(i // 100) % 24:02d}:{(i // 2) % 60:02d}:{i % 60:02d}Z"
        timeout = HOSTS[host]
        if host == BAD:
            latency = int(rng.triangular(300, 1687, 900))
            if 15_000 < i < 45_000 and rng.random() < 0.15:
                lines.append(f"{ts} req={rid} upstream={host} status=TIMEOUT after_ms={timeout}")
                continue
        else:
            latency = int(rng.triangular(20, timeout * 0.9, timeout * 0.3))
        lines.append(f"{ts} req={rid} upstream={host} status=OK latency_ms={latency}")
    # pin the maximum in the middle of the file
    lines.insert(31_337, f"2025-03-14T07:00:00Z req={'f' * 16} upstream={BAD} status=OK latency_ms=1687")
    (dest / "logs").mkdir(exist_ok=True)
    (dest / "logs" / "app.log").write_text("\n".join(lines) + "\n")
    (dest / "config").mkdir(exist_ok=True)
    cfg = {"upstreams": [{"host": h, "timeout_ms": t if h != BAD else 1500} for h, t in HOSTS.items()]}
    (dest / "config" / "upstreams.json").write_text(json.dumps(cfg, indent=2) + "\n")
