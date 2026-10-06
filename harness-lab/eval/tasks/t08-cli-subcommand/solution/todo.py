import argparse
import datetime
import json
import sys
from pathlib import Path


def load(db: Path) -> list[dict]:
    return json.loads(db.read_text()) if db.exists() else []


def save(db: Path, items: list[dict]) -> None:
    db.write_text(json.dumps(items, indent=2))


def cmd_add(args) -> int:
    items = load(args.db)
    items.append({"id": len(items) + 1, "title": args.title, "done": False, "due": args.due})
    save(args.db, items)
    print(f"added {len(items)}")
    return 0


def cmd_done(args) -> int:
    items = load(args.db)
    for it in items:
        if it["id"] == args.id:
            it["done"] = True
            save(args.db, items)
            return 0
    print(f"no task {args.id}", file=sys.stderr)
    return 1


def cmd_list(args) -> int:
    for it in load(args.db):
        mark = "x" if it["done"] else " "
        print(f"[{mark}] {it['id']} {it['title']}" + (f" (due {it['due']})" if it.get("due") else ""))
    return 0


def cmd_stats(args) -> int:
    items = load(args.db)
    done = sum(1 for it in items if it["done"])
    print(f"total: {len(items)}")
    print(f"done: {done}")
    print(f"open: {len(items) - done}")
    today = args.today or datetime.date.today().isoformat()
    overdue = sum(1 for it in items if not it["done"] and it.get("due") and it["due"] < today)
    if overdue:
        print(f"overdue: {overdue}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="todo")
    p.add_argument("--db", type=Path, default=Path("todo.json"))
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("title")
    a.add_argument("--due")
    a.set_defaults(func=cmd_add)
    d = sub.add_parser("done")
    d.add_argument("id", type=int)
    d.set_defaults(func=cmd_done)
    sub.add_parser("list").set_defaults(func=cmd_list)
    s = sub.add_parser("stats")
    s.add_argument("--today")
    s.set_defaults(func=cmd_stats)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
