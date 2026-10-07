"""Run agent x task x seed and append one validated JSON record per run.

    python -m eval.runner --agent null --tasks all --seeds 0 1 2 --out eval/results/x.jsonl

DESIGN DECISION — run the agent in-process or in a child process?
In-process is simpler, but a wall-clock budget is then unenforceable: Python cannot
kill a thread stuck in a blocking HTTP call or an infinite loop in student code. A
child process can be killed. Chosen: one child process per run (spawn start method,
so no state leaks between runs). Cost: the agent and its result must be picklable.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from eval.agents import AGENT_NAMES, make_agent
from eval.contract import SCHEMA_VERSION, AgentResult, Budget, TaskInput, validate_record
from eval.sandbox import DEFAULT_IMAGE, DockerSandbox
from eval.tasks import Task, load_tasks, materialize
from eval.verify import verify

ROOT = Path(__file__).resolve().parent.parent


def _git_sha() -> str:
    proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    sha = proc.stdout.strip() or "unknown"
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "."], cwd=ROOT, capture_output=True, text=True)
    return sha + ("-dirty" if dirty.stdout.strip() else "")


def _child(agent, task_input: TaskInput, sandbox: DockerSandbox, budget: Budget, seed: int, q) -> None:
    try:
        q.put(("ok", agent.run(task_input, sandbox, budget, seed)))
    except BaseException:  # report, never hang the parent
        q.put(("error", traceback.format_exc()))


def run_agent(agent, task: Task, sandbox: DockerSandbox, budget: Budget, seed: int) -> AgentResult:
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    proc = ctx.Process(target=_child, args=(agent, TaskInput(task.statement, task.user_turns), sandbox, budget, seed, q))
    proc.start()
    proc.join(budget.wall_s)
    if proc.is_alive():
        proc.kill()
        proc.join()
        return AgentResult(stop_reason="wall_timeout", error=f"killed after {budget.wall_s}s")
    if q.empty():
        return AgentResult(stop_reason="crash", error=f"agent process exited {proc.exitcode} without a result")
    status, payload = q.get()
    if status == "error":
        return AgentResult(stop_reason="crash", error=payload[-4000:])
    return payload


def run_one(agent_name: str, task: Task, seed: int, budget: Budget, batch_id: str,
            git_sha: str, image: str = DEFAULT_IMAGE) -> dict:
    agent = make_agent(agent_name, task)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with tempfile.TemporaryDirectory(prefix=f"hl-{task.id}-") as tmp:
        repo = materialize(task, Path(tmp) / "repo")
        out = Path(tmp) / "out"
        t0 = time.monotonic()
        with DockerSandbox(image=image).start(repo) as box:
            result = run_agent(agent, task, box, budget, seed)
            wall = time.monotonic() - t0
            box.export(out)
        verdict = verify(task, out, image=image)
    rec = {
        "schema_version": SCHEMA_VERSION,
        "run_id": uuid.uuid4().hex,
        "batch_id": batch_id,
        "started_at": started,
        "git_sha": git_sha,
        "agent": agent_name,
        "agent_config": agent.config(),
        "task_id": task.id,
        "task_category": task.category,
        "seed": seed,
        "budget": asdict(budget),
        "success": verdict.passed,
        "verifier_exit": verdict.exit_code,
        "verifier_tail": verdict.output_tail,
        "wall_time_s": round(wall, 3),
        **asdict(result),
    }
    problems = validate_record(rec)
    if problems:
        raise ValueError(f"invalid record for {agent_name}/{task.id}/{seed}: {problems}")
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--agent", required=True, choices=AGENT_NAMES)
    ap.add_argument("--tasks", nargs="+", default=["all"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--max-steps", type=int, default=Budget.max_steps)
    ap.add_argument("--max-cost-eur", type=float, default=Budget.max_cost_eur)
    ap.add_argument("--wall-s", type=float, default=Budget.wall_s)
    ap.add_argument("--image", default=DEFAULT_IMAGE)
    args = ap.parse_args(argv)

    tasks = load_tasks(None if args.tasks == ["all"] else args.tasks)
    budget = Budget(args.max_steps, args.max_cost_eur, args.wall_s)
    batch_id = uuid.uuid4().hex[:12]
    sha = _git_sha()
    jobs = [(t, s) for t in tasks for s in args.seeds]
    args.out.parent.mkdir(parents=True, exist_ok=True)

    failures = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as pool, args.out.open("a") as fh:
        futures = {pool.submit(run_one, args.agent, t, s, budget, batch_id, sha, args.image): (t, s) for t, s in jobs}
        for fut, (t, s) in futures.items():
            try:
                rec = fut.result()
            except Exception as exc:  # infrastructure failure: no record, loud error
                failures += 1
                print(f"INFRA FAIL {t.id} seed={s}: {exc}", file=sys.stderr)
                continue
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            mark = "PASS" if rec["success"] else "fail"
            print(f"{mark} {t.id} seed={s} stop={rec['stop_reason']} wall={rec['wall_time_s']}s")
    print(f"batch {batch_id}: {len(jobs) - failures}/{len(jobs)} records written to {args.out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
