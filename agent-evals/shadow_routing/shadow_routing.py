"""shadow_routing — mirror a slice of traffic to a second model and diff the two.

Project #2 (BUILD: eval infrastructure). The safe way to try a new model on real traffic
is to *shadow* it: send a request to the incumbent (primary) and answer from that, then
send the same request to the candidate (shadow) off to the side and compare. The primary
must never notice.

This runs against the shared [simulated service](../simulated_service/): the primary is
served for every request, a deterministic sample is mirrored to the shadow, and the two
are diffed into a report that keeps **cost and quality apart** — a shadow that is better
and dearer is not the same as one that is better and cheaper.

The guarantee that makes it safe is structural and testable: the primary is served
independently of the shadow, and the service answers a request the same way whatever ran
before it, so the primary path is byte-identical with or without shadowing. A slow shadow
adds to the shadow's own latency column and to nothing else.
"""

from __future__ import annotations

import argparse
import sys
import zlib
from dataclasses import dataclass
from typing import Protocol, Sequence

from simulated_service import SimulatedService, Response, totals


class _Service(Protocol):
    def run(self, requests: Sequence, model: str) -> list: ...
    def serve(self, request, model: str) -> object: ...


@dataclass(frozen=True)
class ShadowConfig:
    """`fraction` of requests (0..1) is mirrored from `primary` to `shadow`."""

    primary: str = "small"
    shadow: str = "large"
    fraction: float = 0.1
    seed: int = 0


@dataclass(frozen=True)
class Comparison:
    """Primary vs shadow on the mirrored subset. Cost and quality are separate fields."""

    n_total: int
    n_sampled: int
    primary: dict
    shadow: dict
    disagreements: tuple  # (request_id, primary_success, shadow_success)

    @property
    def delta_success(self) -> float:
        return self.shadow["success"] - self.primary["success"]

    @property
    def delta_cost_eur(self) -> float:
        return self.shadow["cost_eur"] - self.primary["cost_eur"]

    @property
    def delta_latency_ms(self) -> float:
        return self.shadow["latency_ms"] - self.primary["latency_ms"]

    @property
    def fixed(self) -> int:
        """Requests the primary failed and the shadow solved."""
        return sum(1 for _, p, s in self.disagreements if not p and s)

    @property
    def broke(self) -> int:
        """Requests the primary solved and the shadow failed."""
        return sum(1 for _, p, s in self.disagreements if p and not s)

    def report(self) -> str:
        frac = (self.n_sampled / self.n_total * 100) if self.n_total else 0.0
        rows = [
            ("primary", self.primary), ("shadow", self.shadow),
        ]
        width = max(len(r[0]) for r in rows) + 2
        lines = [
            f"shadow routing: {self.n_sampled}/{self.n_total} mirrored ({frac:.1f}%)",
            f"{'':<{width}}{'success':>9}{'cost EUR':>12}{'latency ms':>12}",
        ]
        for name, t in rows:
            lines.append(f"{name:<{width}}{t['success']:>9.3f}{t['cost_eur']:>12.4f}"
                         f"{t['latency_ms']:>12.1f}")
        lines.append(f"{'delta':<{width}}{self.delta_success:>+9.3f}{self.delta_cost_eur:>+12.4f}"
                     f"{self.delta_latency_ms:>+12.1f}")
        lines.append(f"disagreements: {len(self.disagreements)} "
                     f"(shadow fixed {self.fixed}, broke {self.broke})")
        return "\n".join(lines)


def is_sampled(request_id: str, fraction: float, seed: int) -> bool:
    """Deterministic, order-independent membership: a stable hash compared to `fraction`."""
    if fraction <= 0.0:
        return False
    if fraction >= 1.0:
        return True
    bucket = zlib.crc32(f"{seed}:{request_id}".encode("utf-8")) % 1_000_000
    return bucket / 1_000_000 < fraction


def sampled_ids(requests: Sequence, fraction: float, seed: int) -> list[str]:
    return [r.id for r in requests if is_sampled(r.id, fraction, seed)]


def shadow_run(service: _Service, requests: Sequence, config: ShadowConfig):
    """Return `(primary, shadow, mirrored_ids)`: primary for all, shadow for the sample."""
    primary = service.run(requests, config.primary)
    ids = sampled_ids(requests, config.fraction, config.seed)
    by_id = {r.id: r for r in requests}
    shadow = [service.serve(by_id[i], config.shadow) for i in ids]
    return primary, shadow, ids


def compare(service: _Service, requests: Sequence, config: ShadowConfig | None = None) -> Comparison:
    config = config or ShadowConfig()
    primary, shadow, ids = shadow_run(service, requests, config)
    primary_by_id = {r.request_id: r for r in primary}
    mirrored_primary = [primary_by_id[i] for i in ids]
    disagreements = tuple(
        (i, primary_by_id[i].success, s.success)
        for i, s in zip(ids, shadow)
        if primary_by_id[i].success != s.success
    )
    return Comparison(
        n_total=len(requests), n_sampled=len(ids),
        primary=totals(mirrored_primary), shadow=totals(shadow),
        disagreements=disagreements,
    )


def _ask_drift(spec: str):
    from simulated_service import _parse_drift
    return _parse_drift(spec)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="shadow_routing",
                                 description="Mirror a slice of synthetic traffic to a second model.")
    ap.add_argument("--per-segment", type=int, default=60)
    ap.add_argument("--segments", type=int, default=7)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--primary", default="small")
    ap.add_argument("--shadow", default="large")
    ap.add_argument("--fraction", type=float, default=0.1)
    ap.add_argument("--drift", action="append", type=_ask_drift, default=[],
                    metavar="AFTER:PENALTY[:TENANT[:CATEGORY]]")
    args = ap.parse_args(argv)

    service = SimulatedService(seed=args.seed, drift=args.drift)
    requests = service.traffic(per_segment=args.per_segment, segments=args.segments)
    config = ShadowConfig(primary=args.primary, shadow=args.shadow, fraction=args.fraction,
                          seed=args.seed)
    print(compare(service, requests, config).report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
