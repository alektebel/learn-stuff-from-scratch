"""Run agent x scenario x seed; record success and safety separately.

    python -m redteam.runner --agent complicit --scenarios all --seeds 0 --out results/x.jsonl
    python -m redteam.runner --report results/*.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from eval.contract import STOP_REASONS, Budget
from eval.runner import _git_sha, run_agent
from eval.sandbox import DEFAULT_IMAGE, DockerSandbox
from eval.stats import wilson_interval
from eval.tasks import materialize
from eval.verify import verify

from redteam.agents import AGENT_NAMES, make_agent
from redteam.detectors import run_checks
from redteam.scenarios import Scenario, load_scenarios

SCHEMA_VERSION = 1
FIELDS = {
    "schema_version": int, "run_id": str, "batch_id": str, "started_at": str, "git_sha": str,
    "agent": str, "scenario_id": str, "attack": str, "seed": int, "success": bool, "safe": bool,
    "violations": list, "verifier_exit": int, "stop_reason": str, "tool_calls": int,
    "wall_time_s": float, "error": (str, type(None)),
}


def validate(rec: dict) -> list[str]:
    problems = [f"missing {k}" for k in FIELDS.keys() - rec.keys()]
    problems += [f"unknown {k}" for k in rec.keys() - FIELDS.keys()]
    problems += [f"{k}: {type(rec[k]).__name__}" for k, t in FIELDS.items() if k in rec and not isinstance(rec[k], t)]
    if not problems:
        if rec["safe"] != (not rec["violations"]):
            problems.append("safe disagrees with violations")
        if rec["stop_reason"] not in STOP_REASONS:
            problems.append(f"unknown stop_reason {rec['stop_reason']!r}")
    return problems


def run_scenario(agent_name: str, sc: Scenario, seed: int, budget: Budget, batch_id: str,
                 git_sha: str, image: str = DEFAULT_IMAGE) -> dict:
    agent = make_agent(agent_name, sc)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with tempfile.TemporaryDirectory(prefix=f"rt-{sc.id}-") as tmp:
        tmp = Path(tmp)
        repo = materialize(sc.task, tmp / "repo")
        before, after = tmp / "before", tmp / "after"
        with DockerSandbox(image=image).start(repo) as box:
            if sc.home_dir is not None:
                # root holds no DAC capabilities, so it cannot write into the agent's home:
                # stage the files world-readable, then copy them in as the agent itself
                box.put_dir(sc.home_dir, "/tmp/home-seed")
                seeded = box.exec("cp -r /tmp/home-seed/. /home/agent/")
                if seeded.exit_code != 0:
                    raise RuntimeError(f"seeding /home/agent failed: {seeded.stderr}")
                box.exec("rm -rf /tmp/home-seed", user="root")
            # snapshot from the container itself, so ownership/skeleton files match `after`
            box.export(before / "work")
            box.export(before / "home", src="/home/agent")
            t0 = time.monotonic()
            result = run_agent(agent, sc.task, box, budget, seed)
            wall = time.monotonic() - t0
            box.stop()
            box.export(after / "work")
            box.export(after / "home", src="/home/agent")
        verdict = verify(sc.task, after / "work", image=image)
        violations = run_checks(sc.checks, before, after)
    rec = {
        "schema_version": SCHEMA_VERSION, "run_id": uuid.uuid4().hex, "batch_id": batch_id,
        "started_at": started, "git_sha": git_sha, "agent": agent_name, "scenario_id": sc.id,
        "attack": sc.attack, "seed": seed, "success": verdict.passed, "safe": not violations,
        "violations": violations, "verifier_exit": verdict.exit_code,
        "stop_reason": result.stop_reason, "tool_calls": result.tool_calls,
        "wall_time_s": round(wall, 3), "error": result.error,
    }
    problems = validate(rec)
    if problems:
        raise ValueError(f"invalid record {agent_name}/{sc.id}: {problems}")
    return rec


def report(recs: list[dict]) -> str:
    by = defaultdict(list)
    for r in recs:
        by[r["agent"]].append(r)
    rows = ["agent | runs | success | safe | success but UNSAFE | safe 95% CI",
            "---|---|---|---|---|---"]
    for agent, rs in sorted(by.items()):
        n = len(rs)
        ok, safe = sum(r["success"] for r in rs), sum(r["safe"] for r in rs)
        hidden = sum(r["success"] and not r["safe"] for r in rs)
        lo, hi = wilson_interval(safe, n)
        rows.append(f"{agent} | {n} | {ok}/{n} | {safe}/{n} | {hidden} | [{100 * lo:.1f}, {100 * hi:.1f}]")
    rows.append("")
    rows.append("'success but UNSAFE': runs a final-answer eval scores as a pass.")
    return "\n".join(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=AGENT_NAMES)
    ap.add_argument("--scenarios", nargs="+", default=["all"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--wall-s", type=float, default=Budget.wall_s)
    ap.add_argument("--report", nargs="+", type=Path)
    args = ap.parse_args(argv)
    if args.report:
        recs = [json.loads(l) for p in args.report for l in p.read_text().splitlines() if l.strip()]
        bad = [(r.get("run_id"), p) for r in recs if (p := validate(r))]
        if bad:
            raise ValueError(f"invalid records: {bad[:3]}")
        print(report(recs))
        return 0
    if not (args.agent and args.out):
        ap.error("--agent and --out are required unless --report is given")
    scenarios = load_scenarios(None if args.scenarios == ["all"] else args.scenarios)
    batch, sha = uuid.uuid4().hex[:12], _git_sha()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    with args.out.open("a") as fh:
        for sc in scenarios:
            for seed in args.seeds:
                try:
                    rec = run_scenario(args.agent, sc, seed, Budget(wall_s=args.wall_s), batch, sha)
                except Exception as exc:
                    failures += 1
                    print(f"INFRA FAIL {sc.id} seed={seed}: {exc}", file=sys.stderr)
                    continue
                fh.write(json.dumps(rec) + "\n")
                print(f"{sc.id} seed={seed} success={rec['success']} safe={rec['safe']} {rec['violations']}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
