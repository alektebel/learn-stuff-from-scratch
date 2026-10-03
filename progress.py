#!/usr/bin/env python3
"""
progress.py — where you actually are against the 18-week plan in ROADMAP.md.

    python3 progress.py                 # the core track, this week
    python3 progress.py --track full    # all 41 directories
    python3 progress.py --track spine   # the 12-directory minimum
    python3 progress.py --track ops     # aimed at an AI-ops role, not at coverage
    python3 progress.py --week 7        # pretend it is week 7
    python3 progress.py --checks        # also run every check.py (slower, exact)

Counting is deliberately crude, because a progress tool you do not trust is a
progress tool you stop running. It counts the markers left in the templates:

    Python   `raise NotImplementedError`, falling back to `# TODO`
    Lean     `sorry`
    Haskell  `= undefined` and `-- TODO`
    C / CUDA `TODO`

Two consequences worth knowing before you rely on the number:

  * The Python count is honest — the marker disappears when you implement the
    function, because the function no longer raises.
  * The C, CUDA and Haskell counts are NOT honest unless you DELETE each TODO
    comment as you satisfy it. Do that. It costs nothing and it is the only
    thing keeping those bars meaningful.
  * `--checks` is the number that cannot be gamed: it runs every graded
    checker in the repo and reports what actually passes. Trust that column
    over the bars.

Two directories (vllm-engine, tensorrt-inference) are design briefs with no
template to count. They are tracked by hours only, and their real completion
signal is whether their README's benchmarks run.
"""

import argparse
import datetime
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
START = datetime.date(2026, 8, 24)          # week 1, Monday
WEEKS = 18

GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")

# (directory, estimated hours, week it is DUE on the full track, tracks)
# Hours come from each directory's own README estimate where it states one, and
# otherwise from unit count x a rate calibrated against the ones that do.
PLAN = [
    ("aws-from-scratch",           42,  1, "FCSO"),
    ("autograd",                   30,  2, "FCSO"),
    ("llm-from-scratch",           55,  2, "FCSO"),
    ("rl-posttraining",            30,  3, "FCO"),
    ("context-caching",            28,  3, "FCO"),
    ("inference-from-scratch",    70,  4, "FCSO"),
    ("deploy-and-debug",           10,  4, "FCO"),
    ("contextcite",                13,  5, "FC"),
    ("spade",                      16,  5, "FC"),
    ("mars-sql",                   20,  5, "FC"),
    ("provenance-semirings",       45,  6, "FC"),
    ("scasp",                      45,  7, "F"),
    ("linc",                       30,  8, "F"),
    ("distributed-training",      18,  8, "FO"),
    ("database-engine",           77,  9, "FCSO"),
    ("dynamo-paper",               21, 10, "FCSO"),
    ("raft",                       30, 10, "FCO"),
    ("blockchain-from-scratch",    55, 11, "FC"),
    ("aws-certification",          35, 12, "FCO"),
    ("aws-deploy",                 20, 12, "FCO"),
    ("bash-from-scratch",           8, 13, "FC"),
    ("http-server",                86, 13, "FCSO"),
    ("dns-server",                  9, 14, "F"),
    ("cryptographic-library",       5, 14, "F"),
    ("communication-protocols",    34, 14, "F"),
    ("toralizer",                  21, 14, "F"),
    ("firewall-from-scratch",      25, 15, "F"),
    ("c-compiler",                 27, 15, "FCS"),
    ("compiler-and-vgpu",          16, 15, "FCS"),
    ("quantum-computing-lang",      8, 15, "F"),
    ("cuda-from-scratch",        142, 16, "FCSO"),
    ("database-internals",       45, 17, "FC"),
    ("ray-tracer",                 35, 17, "F"),
    ("haskell-projects",           61, 17, "F"),
    ("spectral-graphs",             5, 18, "F"),
    ("sas-lineage-tool",            8, 18, "F"),
    ("web-scraping",                6, 18, "F"),
    ("ml-in-production",            8, 18, "F"),
    ("mlops",                      12, 18, "F"),
    ("lean-proofs",             151,  0, "F"),      # week 0 = every week, daily
]

TRACKS = {"full": "F", "core": "C", "spine": "S", "ops": "O"}

# Unit counts measured when the plan was written, by remaining_units() itself.
# "Done" is baseline minus what is left, so a directory you have not touched
# reads 0% rather than 100%. Regenerate these with --rebaseline if you fork the
# templates; a baseline computed by any other rule than the one above invents
# progress you did not make.
BASELINE = {
    "autograd": 67, "aws-certification": 40, "aws-deploy": 32,
    "aws-from-scratch": 140, "bash-from-scratch": 18,
    "blockchain-from-scratch": 46, "c-compiler": 149,
    "communication-protocols": 115, "compiler-and-vgpu": 53,
    "context-caching": 94, "contextcite": 42, "cryptographic-library": 12,
    "cuda-from-scratch": 37, "database-engine": 124, "database-internals": 36,
    "deploy-and-debug": 34, "distributed-training": 8, "dns-server": 20,
    "dynamo-paper": 70, "firewall-from-scratch": 68, "haskell-projects": 67,
    "http-server": 16, "inference-from-scratch": 49, "lean-proofs": 504,
    "linc": 22, "llm-from-scratch": 49, "mars-sql": 15, "ml-in-production": 7,
    "mlops": 13, "provenance-semirings": 76, "quantum-computing-lang": 17,
    "raft": 30, "ray-tracer": 41, "rl-posttraining": 32,
    "sas-lineage-tool": 23, "scasp": 22, "spade": 19, "spectral-graphs": 11,
    "toralizer": 46, "web-scraping": 0,
}


def locate(name: str) -> pathlib.Path:
    """Find a project directory, wherever the weekly layout put it.

    The repo is ordered into week-01/ .. week-18/, but a directory's home week
    is a scheduling fact, not an identity — so nothing here hard-codes a path.
    Look it up, and keep working if the layout changes again.
    """
    direct = ROOT / name
    if direct.is_dir():
        return direct
    for week in sorted(ROOT.glob("week-*")):
        candidate = week / name
        if candidate.is_dir():
            return candidate
    return direct


def remaining_units(directory: pathlib.Path) -> int:
    """Markers still standing. Python prefers the marker that cannot lie."""
    nie = todo = lean = haskell = 0
    for path in directory.rglob("*"):
        if not path.is_file() or "solutions" in path.parts:
            continue
        if path.name in ("check.py", "progress.py"):
            continue
        if path.suffix not in (".py", ".c", ".h", ".cu", ".hs", ".lean"):
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        if path.suffix == ".py":
            nie += len(re.findall(r"raise NotImplementedError", text))
            todo += len(re.findall(r"#\s*TODO", text))
        elif path.suffix == ".lean":
            lean += len(re.findall(r"\bsorry\b", text))
        elif path.suffix == ".hs":
            haskell += len(re.findall(r"=\s*undefined|--\s*TODO", text))
        else:
            todo += len(re.findall(r"\bTODO\b", text))
    # A directory with real NotImplementedError stubs is measured by those; the
    # TODO comments beside them are guidance, not work items, and counting both
    # would make an implemented file look half done forever.
    return (nie or todo) + lean + haskell


def checker_score(directory: pathlib.Path):
    """Run the directory's own check.py and return (passing, total)."""
    checker = directory / "check.py"
    if not checker.exists():
        return None
    try:
        result = subprocess.run([sys.executable, "check.py", "--all"],
                                cwd=directory, capture_output=True, text=True,
                                timeout=180)
    except subprocess.TimeoutExpired:
        return None
    match = re.search(r"(\d+)/(\d+) passing", result.stdout)
    return (int(match.group(1)), int(match.group(2))) if match else None


def current_week(today: datetime.date) -> int:
    if today < START:
        return 0
    return min(WEEKS, (today - START).days // 7 + 1)


def bar(fraction: float, width: int = 16) -> str:
    filled = int(round(fraction * width))
    colour = GREEN if fraction >= 0.999 else YELLOW
    head = f"{colour}{'#' * filled}" if filled else ""
    return f"{head}{GREY}{'.' * (width - filled)}{RESET}"


def rebaseline() -> int:
    """Rewrite BASELINE in this file from the templates as they stand now."""
    counts = {name: remaining_units(locate(name)) for name, *_ in PLAN
              if locate(name).is_dir()}
    lines, row = [], "    "
    for key in sorted(counts):
        piece = f'"{key}": {counts[key]}, '
        if len(row) + len(piece) > 79:
            lines.append(row.rstrip())
            row = "    "
        row += piece
    lines.append(row.rstrip().rstrip(","))
    block = "BASELINE = {\n" + "\n".join(lines) + ",\n}"
    source = pathlib.Path(__file__)
    text = re.sub(r"BASELINE = \{.*?\n\}", block, source.read_text(), flags=re.S)
    source.write_text(text)
    print(f"BASELINE rewritten for {len(counts)} directories "
          f"({sum(counts.values())} units outstanding)")
    return 0


def main(argv) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--track", default="core", choices=sorted(TRACKS))
    parser.add_argument("--week", type=int, default=None)
    parser.add_argument("--checks", action="store_true",
                        help="also run every check.py (slower, and exact)")
    parser.add_argument("--rebaseline", action="store_true",
                        help="rewrite BASELINE from the templates as they are "
                             "now, and exit — use after forking or adding a "
                             "directory, never to hide a bad week")
    args = parser.parse_args(argv)

    if args.rebaseline:
        return rebaseline()

    flag = TRACKS[args.track]
    plan = [row for row in PLAN if flag in row[3]]
    week = args.week if args.week is not None else current_week(datetime.date.today())
    total_hours = sum(row[1] for row in plan)

    monday = START + datetime.timedelta(weeks=max(0, week - 1))
    sunday = monday + datetime.timedelta(days=6)

    print(f"\n{BOLD}learn-stuff-from-srcatch — progress against ROADMAP.md{RESET}")
    print(f"  track {BOLD}{args.track}{RESET}: {len(plan)} directories, "
          f"{total_hours} h estimated, {total_hours / WEEKS:.0f} h/week")
    if week == 0:
        print(f"  {GREY}not started — week 1 begins {START}{RESET}\n")
    else:
        print(f"  week {BOLD}{week}{RESET} of {WEEKS}   "
              f"{monday.strftime('%b %d')} – {sunday.strftime('%b %d, %Y')}\n")

    print(f"  {'due':>3} {'directory':<24}{'units':>12}{'h':>5}  progress")
    print("  " + "-" * 66)

    done_hours = 0.0
    done_units = total_units = 0
    checks_line = []

    for name, hours, scheduled, _ in plan:
        directory = locate(name)
        if not directory.is_dir():
            continue
        base = BASELINE.get(name, 0)
        left = remaining_units(directory)
        finished = max(0, base - left)
        fraction = (finished / base) if base else 0.0
        done_units += finished
        total_units += base
        done_hours += fraction * hours

        when = "daily" if scheduled == 0 else f"{scheduled:>2}"
        units = f"{finished}/{base}" if base else f"{GREY}brief{RESET}"
        overdue = scheduled and week and scheduled < week and fraction < 0.999
        mark = f"{RED}!{RESET}" if overdue else " "
        pad = 12 + (len(GREY) + len(RESET) if not base else 0)
        print(f"  {when:>3}{mark} {name:<24}{units:>{pad}}{hours:>5}  "
              f"{bar(fraction)} {100 * fraction:>3.0f}%")

        if args.checks:
            score = checker_score(directory)
            if score:
                checks_line.append((name, score))

    print("  " + "-" * 66)
    print(f"  {'':>3}  {'TOTAL':<24}{f'{done_units}/{total_units}':>12}"
          f"{total_hours:>5}  {bar(done_hours / total_hours)} "
          f"{100 * done_hours / total_hours:>3.0f}%")

    if checks_line:
        print(f"\n  {BOLD}graded checkers{RESET} "
              f"{GREY}(the number that cannot be gamed){RESET}")
        for name, (passing, out_of) in checks_line:
            colour = GREEN if passing == out_of else YELLOW
            print(f"    {name:<24}{colour}{passing:>3}/{out_of}{RESET} passing")

    if week:
        target = total_hours * week / WEEKS
        delta = done_hours - target
        weeks_of_slip = abs(delta) / (total_hours / WEEKS)
        print(f"\n  {done_hours:.0f} h of work done; the plan says {target:.0f} h "
              f"by the end of week {week}.")
        if delta >= 0:
            print(f"  {GREEN}Ahead by {delta:.0f} h "
                  f"({weeks_of_slip:.1f} weeks).{RESET}")
        else:
            print(f"  {RED}Behind by {-delta:.0f} h "
                  f"({weeks_of_slip:.1f} weeks).{RESET}")
            print(f"  {GREY}Slip is normal. Cut scope, not the daily block — "
                  f"a track you finish{RESET}")
            print(f"  {GREY}beats a track you abandon in November. "
                  f"`--track spine` is the smaller one.{RESET}")

    if not args.checks:
        print(f"\n  {GREY}Bars count markers left in the templates. Run with "
              f"--checks for the{RESET}")
        print(f"  {GREY}graded result, and delete each TODO comment in the C "
              f"and Haskell files{RESET}")
        print(f"  {GREY}as you satisfy it — otherwise those bars never move."
              f"{RESET}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
