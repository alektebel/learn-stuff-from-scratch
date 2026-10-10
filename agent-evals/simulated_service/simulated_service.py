"""simulated_service — a fake production service with synthetic traffic and injected drift.

Three eval projects need production traffic they do not have: #2 (shadow routing), #9
(drift monitor) and #10 (cost-quality Pareto). Instead of stubbing each one, this is a
single deterministic double they all run against. It teaches the *mechanics* — sampling
traffic over time and tenants, mirroring a request to two models, watching a quality
regression appear, trading cost against success — and its numbers say nothing about any
real system (see ../../README.md).

Everything is the standard library and every value is a pure function of (seed, request
id): no numpy, no network, no model calls, no message history. Two consequences the
projects rely on:

- **A run is reproducible.** The same seed and traffic give byte-identical responses.
- **A response is independent of its neighbours.** Serving a request twice, in any order,
  or after mirroring it to another model, yields the same answer — so a shadow model can
  never move the primary's numbers (#2).

The service has three parts:

- `traffic()` — a synthetic request stream spread over tenants, categories and time
  segments, each request with a hidden difficulty.
- `serve()` — one request against a model: a success sampled from a latent quality that
  drops when a `Drift` rule is active.
- `write_jsonl()` / `read_jsonl()` — the trace store the projects read.

`quality` is the latent probability; `success` is one draw from it. A drift `penalty` is a
reduction of the logit, so a larger penalty means a worse service from `after_segment` on.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import zlib
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

TENANTS = ("acme", "globex", "initech")
CATEGORIES = ("lookup", "summarise", "refactor", "classify")

# The difficulty->logit slope. Fixed so a request's difficulty means the same thing
# across models; only `ModelConfig.strength` moves between them.
DIFFICULTY_SLOPE = 1.6


@dataclass(frozen=True)
class ModelConfig:
    """One served model: how good it is and what it costs.

    `strength` is the base logit (higher is better); `in_price`/`out_price` are EUR per
    1000 tokens; `out_tokens` is the typical completion size, scaled by difficulty.
    """

    name: str
    strength: float
    in_price: float
    out_price: float
    base_latency_ms: float
    out_tokens: int


# A cheap weak model and an expensive strong one, so cost and quality actually trade off.
MODELS: dict[str, ModelConfig] = {
    "small": ModelConfig("small", 1.7, 0.00015, 0.0006, 280.0, 220),
    "large": ModelConfig("large", 2.7, 0.0025, 0.0100, 820.0, 260),
}


@dataclass(frozen=True)
class Drift:
    """A quality regression that starts at `after_segment` and lowers the logit.

    `tenant`/`category` scope it; `None` matches all. `penalty` is subtracted from the
    logit (positive = worse), so a planted drop is exactly the thing a monitor has to
    find. Kept out of the trace on purpose: a monitor must detect it from success alone.
    """

    after_segment: int
    penalty: float
    tenant: str | None = None
    category: str | None = None


@dataclass(frozen=True)
class Request:
    id: str
    tenant: str
    category: str
    difficulty: float
    segment: int
    prompt_tokens: int


@dataclass(frozen=True)
class Response:
    request_id: str
    model: str
    tenant: str
    category: str
    segment: int
    success: bool
    quality: float           # latent p, before sampling
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_eur: float


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class SimulatedService:
    """The double. Construct once, then `run(traffic, model)`."""

    def __init__(self, seed: int = 0, models: Mapping[str, ModelConfig] | None = None,
                 drift: Sequence[Drift] = ()) -> None:
        self.seed = seed
        self.models = dict(models or MODELS)
        self.drift = tuple(drift)

    # -- determinism: a private rng per (purpose, key), independent of call order ------
    def _rng(self, *parts: object) -> random.Random:
        key = ":".join(str(p) for p in parts).encode("utf-8")
        return random.Random((self.seed * 1_000_003) ^ zlib.crc32(key))

    def _penalty(self, tenant: str, category: str, segment: int) -> float:
        return sum(
            d.penalty for d in self.drift
            if segment >= d.after_segment
            and (d.tenant is None or d.tenant == tenant)
            and (d.category is None or d.category == category)
        )

    # -- the synthetic stream ----------------------------------------------------------
    def traffic(self, n: int = 420, tenants: Sequence[str] = TENANTS,
                categories: Sequence[str] = CATEGORIES, segments: int = 1,
                per_segment: int | None = None) -> list[Request]:
        """`n` requests spread evenly over `segments` and round-robin over tenant/category.

        `per_segment` overrides `n` with `per_segment * segments`.
        """
        if per_segment is not None:
            n = per_segment * segments
        if n < 0:
            raise ValueError("n must be non-negative")
        requests: list[Request] = []
        for i in range(n):
            rid = f"r{i:05d}"
            rng = self._rng("traffic", rid)
            requests.append(Request(
                id=rid,
                tenant=tenants[i % len(tenants)],
                category=categories[(i // len(tenants)) % len(categories)],
                difficulty=round(rng.random(), 4),
                segment=(i * segments) // n if n else 0,
                prompt_tokens=rng.randint(120, 900),
            ))
        return requests

    # -- the service -------------------------------------------------------------------
    def serve(self, request: Request, model: str = "small") -> Response:
        cfg = self.models[model]
        logit = cfg.strength - DIFFICULTY_SLOPE * request.difficulty \
            - self._penalty(request.tenant, request.category, request.segment)
        quality = _sigmoid(logit)
        rng = self._rng("serve", model, request.id)
        success = rng.random() < quality
        out_tokens = max(1, int(cfg.out_tokens * (0.6 + 0.8 * request.difficulty))
                         + rng.randint(-20, 20))
        latency = cfg.base_latency_ms * (0.7 + 0.6 * request.difficulty) + rng.uniform(0.0, 120.0)
        cost = request.prompt_tokens / 1000 * cfg.in_price + out_tokens / 1000 * cfg.out_price
        return Response(
            request_id=request.id, model=model, tenant=request.tenant,
            category=request.category, segment=request.segment, success=success,
            quality=round(quality, 6), input_tokens=request.prompt_tokens,
            output_tokens=out_tokens, latency_ms=round(latency, 2), cost_eur=round(cost, 8),
        )

    def run(self, requests: Iterable[Request], model: str = "small") -> list[Response]:
        return [self.serve(r, model) for r in requests]

    def drift_schedule(self) -> list[Drift]:
        """The planted drops, for scoring a monitor. Never part of the trace."""
        return list(self.drift)


# -- the trace store -------------------------------------------------------------------

def write_jsonl(responses: Iterable[Response], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in responses:
            fh.write(json.dumps(asdict(r), sort_keys=True) + "\n")
    return out


def read_jsonl(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


# -- small aggregations the projects would otherwise rewrite ---------------------------

def success_rate(rows: Sequence[Response | dict], key: str = "segment") -> dict[object, float]:
    groups: dict[object, list[int]] = defaultdict(lambda: [0, 0])
    for r in rows:
        value = r[key] if isinstance(r, dict) else getattr(r, key)
        groups[value][1] += 1
        groups[value][0] += int(bool(r["success"] if isinstance(r, dict) else r.success))
    return {k: s / n for k, (s, n) in groups.items()}


def totals(rows: Sequence[Response | dict]) -> dict[str, float]:
    def get(r, k):
        return r[k] if isinstance(r, dict) else getattr(r, k)
    n = len(rows)
    return {
        "runs": n,
        "success": sum(int(bool(get(r, "success"))) for r in rows) / n if n else 0.0,
        "cost_eur": sum(float(get(r, "cost_eur")) for r in rows),
        "latency_ms": sum(float(get(r, "latency_ms")) for r in rows) / n if n else 0.0,
    }


# -- CLI: emit a trace the projects can read -------------------------------------------

def _parse_drift(spec: str) -> Drift:
    """`after:penalty[:tenant[:category]]`, e.g. ``7:1.4:acme``."""
    parts = spec.split(":")
    if len(parts) < 2:
        raise argparse.ArgumentTypeError("drift must be after:penalty[:tenant[:category]]")
    after, penalty = int(parts[0]), float(parts[1])
    tenant = parts[2] or None if len(parts) > 2 else None
    category = parts[3] or None if len(parts) > 3 else None
    return Drift(after, penalty, tenant, category)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="simulated_service",
                                 description="Emit a synthetic traffic trace with injected drift.")
    ap.add_argument("--out", required=True, help="trace JSONL to write")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default="small", choices=sorted(MODELS))
    ap.add_argument("--tenants", default=",".join(TENANTS))
    ap.add_argument("--categories", default=",".join(CATEGORIES))
    ap.add_argument("--segments", type=int, default=1)
    ap.add_argument("--per-segment", type=int, default=None)
    ap.add_argument("--n", type=int, default=420)
    ap.add_argument("--drift", action="append", type=_parse_drift, default=[],
                    metavar="AFTER:PENALTY[:TENANT[:CATEGORY]]")
    args = ap.parse_args(argv)

    svc = SimulatedService(seed=args.seed, drift=args.drift)
    reqs = svc.traffic(n=args.n, tenants=tuple(args.tenants.split(",")),
                       categories=tuple(args.categories.split(",")),
                       segments=args.segments, per_segment=args.per_segment)
    rows = svc.run(reqs, model=args.model)
    path = write_jsonl(rows, args.out)
    summary = totals(rows)
    print(f"{path}: {summary['runs']} runs · success {summary['success']:.1%} · "
          f"cost {summary['cost_eur']:.4f} EUR · {len(svc.drift_schedule())} drift rule(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
