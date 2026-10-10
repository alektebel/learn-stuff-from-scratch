"""
The skill tree: validate it, find what is ready to work on, render it.

    python3 tree.py check            # validate tree.toml and books.toml (exit 1 on problems)
    python3 tree.py next             # nodes whose prerequisites are all done
    python3 tree.py order            # a full topological order
    python3 tree.py show <id>        # one node, with its prerequisites' status
    python3 tree.py status           # counts per track and status
    python3 tree.py xp               # XP, level, rank and badges
    python3 tree.py render           # rewrite the generated section of README.md

A node is READY when its status is "todo" and every node in `requires` is "done".
"exists" (material without graded checks) never satisfies a prerequisite.

Tracks and the gamification rules (XP by difficulty, capstones, levels, badges) live
in tracks.py so the README and the HTML page agree. Sources come from books.toml:
either a `[book.*]` (cite the chapter) or a `[doc.*]` (a spec, standard or manual).
"""

from __future__ import annotations

import re
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from tracks import (  # noqa: E402
    TRACKS,
    XP_BY_DIFFICULTY,
    badges,
    earned_xp,
    level_for,
    max_xp,
)

REPO = HERE.parent
STATUSES = ("todo", "in-progress", "done", "exists")
KINDS = ("skill", "capstone")
REQUIRED = ("id", "title", "track", "requires", "sources", "deliverable", "build", "accept",
            "limit_cases", "status")
BEGIN, END = "<!-- BEGIN GENERATED: tree.py render -->", "<!-- END GENERATED -->"


def load(tree_path: Path = HERE / "tree.toml", books_path: Path = HERE / "books.toml"):
    nodes = tomllib.loads(tree_path.read_text()).get("node", [])
    data = tomllib.loads(books_path.read_text())
    # one flat registry: books (chapter citations) plus docs (specs, standards, manuals)
    sources = {**data.get("book", {}), **data.get("doc", {})}
    return nodes, sources


def validate(nodes: list[dict], books: dict, repo: Path = REPO) -> list[str]:
    problems: list[str] = []
    ids = [n.get("id", "?") for n in nodes]
    for dup, c in Counter(ids).items():
        if c > 1:
            problems.append(f"duplicate id {dup!r}")
    by_id = {n.get("id"): n for n in nodes}
    for n in nodes:
        nid = n.get("id", "?")
        missing = [f for f in REQUIRED if f not in n]
        if missing:
            problems.append(f"{nid}: missing fields {missing}")
            continue
        if n["track"] not in TRACKS:
            problems.append(f"{nid}: unknown track {n['track']!r}")
        if not re.fullmatch(rf"{re.escape(n['track'])}-\d\d-[a-z0-9-]+", nid):
            problems.append(f"{nid}: id must look like '{n['track']}-NN-slug'")
        if n["status"] not in STATUSES:
            problems.append(f"{nid}: unknown status {n['status']!r}")
        if "difficulty" in n and n["difficulty"] not in XP_BY_DIFFICULTY:
            problems.append(f"{nid}: difficulty {n['difficulty']!r} must be one of "
                            f"{sorted(XP_BY_DIFFICULTY)}")
        if "kind" in n and n["kind"] not in KINDS:
            problems.append(f"{nid}: kind {n['kind']!r} must be one of {list(KINDS)}")
        for r in n["requires"]:
            if r not in by_id:
                problems.append(f"{nid}: requires unknown node {r!r}")
            elif r == nid:
                problems.append(f"{nid}: requires itself")
        for s in n["sources"]:
            book = s.split(":", 1)[0]
            if ":" not in s or book not in books:
                problems.append(f"{nid}: source {s!r} must be 'id:locator' with an id from books.toml")
        if n["status"] != "exists":
            if n["track"] in TRACKS:
                expected = TRACKS[n["track"]].root + "/"
                if not n["deliverable"].startswith(expected):
                    problems.append(f"{nid}: deliverable should live under {expected}")
            if not n["accept"]:
                problems.append(f"{nid}: no acceptance criteria")
        if n["status"] == "done":
            if not (repo / n["deliverable"] / "check.py").exists():
                problems.append(f"{nid}: marked done but {n['deliverable']}/check.py does not exist")
            for r in n["requires"]:
                if r in by_id and by_id[r]["status"] != "done":
                    problems.append(f"{nid}: done although prerequisite {r} is {by_id[r]['status']}")
    if len(set(ids)) == len(ids):  # cycle detection needs unique ids
        try:
            topological_order(nodes)
        except ValueError as exc:
            problems.append(str(exc))
    return problems


def topological_order(nodes: list[dict]) -> list[str]:
    """Kahn's algorithm; ties broken by id so the order is stable.

    Edges to ids that are not in the node set are ignored, so an unknown
    prerequisite is reported by validate() as an unknown node and does not
    masquerade as a cycle here.
    """
    ids = {n["id"] for n in nodes}
    indeg = {i: 0 for i in ids}
    children = defaultdict(list)
    for n in nodes:
        for r in n["requires"]:
            if r in ids:
                indeg[n["id"]] += 1
                children[r].append(n["id"])
    ready = sorted(i for i, d in indeg.items() if d == 0)
    order = []
    while ready:
        i = ready.pop(0)
        order.append(i)
        for c in children[i]:
            indeg[c] -= 1
            if indeg[c] == 0:
                ready.append(c)
                ready.sort()
    if len(order) != len(nodes):
        stuck = sorted(set(indeg) - set(order))
        raise ValueError(f"cycle among: {stuck}")
    return order


def ready_nodes(nodes: list[dict]) -> list[dict]:
    by_id = {n["id"]: n for n in nodes}
    return [n for n in nodes if n["status"] == "todo"
            and all(by_id[r]["status"] == "done" for r in n["requires"])]


def render(nodes: list[dict]) -> str:
    style = {"done": ":::done", "in-progress": ":::wip", "exists": ":::exists", "todo": ""}
    done = sum(1 for n in nodes if n["status"] == "done")
    settled = sum(1 for n in nodes if n["status"] in ("done", "exists"))
    per = []
    for t in TRACKS:
        mem = [n for n in nodes if n["track"] == t]
        if mem:
            per.append(f"{t} {sum(1 for n in mem if n['status'] == 'done')}/{len(mem)}")
    xp, cap = earned_xp(nodes), max_xp(nodes)
    level, rank, nxt = level_for(xp)
    badge = badges(nodes)
    earned = [TRACKS[t].label for t, ok in badge["tracks"].items() if ok]
    lines = [f"**{done} of {len(nodes)} nodes graded** — {settled} settled "
             f"(graded or already in the repo). Per track (graded/total): {', '.join(per)}.", "",
             f"**Level {level} · {rank}** — {xp:,} / {cap:,} XP"
             + (f", next at {nxt:,}." if nxt else "."),
             "Badges: " + (" · ".join(f"{b} ✓" for b in earned) if earned else "none yet")
             + (f" · domains: {', '.join(k for k, v in badge['domains'].items() if v)}"
                if any(badge["domains"].values()) else ""),
             "", "```mermaid", "graph LR"]
    for track in TRACKS:
        members = [n for n in nodes if n["track"] == track]
        if not members:
            continue
        lines.append(f"  subgraph {track}")
        for n in members:
            label = n["id"].split("-", 2)[1] + " " + n["title"].replace('"', "'")
            lines.append(f'    {n["id"]}["{label}"]{style[n["status"]]}')
        lines.append("  end")
    for n in nodes:
        for r in n["requires"]:
            lines.append(f"  {r} --> {n['id']}")
    lines += ["  classDef done fill:#2e7d32,color:#fff", "  classDef wip fill:#f9a825",
              "  classDef exists fill:#90a4ae", "```", ""]
    lines += ["| Node | Track | Requires | Status |", "|---|---|---|---|"]
    for i in topological_order(nodes):
        n = next(x for x in nodes if x["id"] == i)
        lines.append(f"| `{i}` {n['title']} | {n['track']} | {', '.join(n['requires']) or '—'} | {n['status']} |")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "check"
    nodes, sources = load()
    problems = validate(nodes, sources)
    if cmd == "check" or problems:
        for p in problems:
            print(f"  ✗ {p}")
        print(f"{len(nodes)} nodes, {len(sources)} sources: "
              f"{'OK' if not problems else f'{len(problems)} problems'}")
        return 1 if problems else 0
    if cmd == "next":
        for n in ready_nodes(nodes):
            print(f"{n['id']:40s} {n['title']}")
    elif cmd == "order":
        print("\n".join(topological_order(nodes)))
    elif cmd == "show":
        n = next((x for x in nodes if x["id"] == argv[1]), None)
        if n is None:
            print(f"no node {argv[1]!r}")
            return 1
        by_id = {x["id"]: x for x in nodes}
        print(f"{n['id']}: {n['title']}  [{n['status']}]\n  deliverable: {n['deliverable']}")
        print("  requires: " + (", ".join(f"{r} ({by_id[r]['status']})" for r in n["requires"]) or "nothing"))
        print("  sources:  " + ", ".join(n["sources"]))
        for key in ("build", "accept", "limit_cases"):
            print(f"  {key}:")
            for item in n[key]:
                print(f"    - {item}")
    elif cmd == "status":
        c = Counter((n["track"], n["status"]) for n in nodes)
        for track in TRACKS:
            row = {s: c[(track, s)] for s in STATUSES if c[(track, s)]}
            if row:
                print(f"{track:13s} {row}")
    elif cmd == "xp":
        xp, cap = earned_xp(nodes), max_xp(nodes)
        level, rank, nxt = level_for(xp)
        print(f"Level {level} · {rank}: {xp} / {cap} XP"
              + (f" (next at {nxt})" if nxt else ""))
        badge = badges(nodes)
        for t, ok in badge["tracks"].items():
            mem = [n for n in nodes if n["track"] == t]
            d = sum(1 for n in mem if n["status"] in ("done", "exists"))
            print(f"  {'★' if ok else '·'} {TRACKS[t].label:22s} {d}/{len(mem)}"
                  f"  [{TRACKS[t].domain}]")
        print("domains: " + ", ".join(f"{d}{' ✓' if ok else ''}"
                                      for d, ok in badge["domains"].items()))
    elif cmd == "render":
        readme = HERE / "README.md"
        text = readme.read_text()
        if BEGIN not in text or END not in text:
            print("README.md has no generated-section markers")
            return 1
        head, rest = text.split(BEGIN, 1)
        _, tail = rest.split(END, 1)
        readme.write_text(f"{head}{BEGIN}\n{render(nodes)}\n{END}{tail}")
        print("README.md updated")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
