"""Summarise run records.

    python -m eval.report eval/results/*.jsonl
    python -m eval.report eval/results/*.jsonl --compare oracle null
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from eval.contract import validate_record
from eval.stats import mcnemar_exact, wilson_interval


def load_records(paths: list[Path]) -> list[dict]:
    recs = []
    for p in paths:
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if not line.strip():
                continue
            rec = json.loads(line)
            problems = validate_record(rec)
            if problems:
                raise ValueError(f"{p}:{i}: {problems}")
            recs.append(rec)
    return recs


def summarise(recs: list[dict]) -> str:
    by_agent: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        by_agent[r["agent"]].append(r)
    rows = ["agent | runs | tasks | success | 95% CI (runs) | med turns | med in tok | med out tok | med cost EUR | med wall s | stop reasons",
            "---|---|---|---|---|---|---|---|---|---|---"]
    for agent, rs in sorted(by_agent.items()):
        k, n = sum(r["success"] for r in rs), len(rs)
        lo, hi = wilson_interval(k, n)
        med = lambda key: statistics.median(r[key] for r in rs)  # noqa: E731
        stops = ", ".join(f"{s}:{c}" for s, c in Counter(r["stop_reason"] for r in rs).most_common())
        rows.append(f"{agent} | {n} | {len({r['task_id'] for r in rs})} | {k}/{n} = {100 * k / n:.1f}% | "
                    f"[{100 * lo:.1f}, {100 * hi:.1f}] | {med('turns')} | {med('input_tokens')} | "
                    f"{med('output_tokens')} | {med('cost_eur'):.4f} | {med('wall_time_s'):.2f} | {stops}")
    return "\n".join(rows)


def compare(recs: list[dict], a: str, b: str) -> str:
    """Paired comparison on (task, seed) pairs both agents ran."""
    res = {(r["agent"], r["task_id"], r["seed"]): r["success"] for r in recs}
    keys = sorted({(t, s) for (ag, t, s) in res if ag == a} & {(t, s) for (ag, t, s) in res if ag == b})
    if not keys:
        return f"no (task, seed) pairs shared by {a} and {b}"
    both = sum(res[(a, *k)] and res[(b, *k)] for k in keys)
    only_a = sum(res[(a, *k)] and not res[(b, *k)] for k in keys)
    only_b = sum(res[(b, *k)] and not res[(a, *k)] for k in keys)
    neither = len(keys) - both - only_a - only_b
    tasks = len({t for t, _ in keys})
    return (f"{a} vs {b}: {len(keys)} pairs over {tasks} tasks\n"
            f"  both pass {both}, only {a} {only_a}, only {b} {only_b}, neither {neither}\n"
            f"  exact McNemar p = {mcnemar_exact(only_a, only_b):.4g}\n"
            f"  caveat: seeds of one task are not independent; with several seeds per task this p is optimistic.")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"))
    args = ap.parse_args(argv)
    recs = load_records(args.files)
    print(summarise(recs))
    if args.compare:
        print()
        print(compare(recs, *args.compare))


if __name__ == "__main__":
    main()
