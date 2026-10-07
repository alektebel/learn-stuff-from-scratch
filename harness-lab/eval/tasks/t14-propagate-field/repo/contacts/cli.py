import argparse
import sys
from pathlib import Path

from contacts.export import to_csv
from contacts.store import Store


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="contacts")
    p.add_argument("--db", type=Path, default=Path("contacts.json"))
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("name")
    a.add_argument("email")
    s = sub.add_parser("show")
    s.add_argument("name")
    sub.add_parser("export")
    args = p.parse_args(argv)
    store = Store(args.db)
    if args.cmd == "add":
        store.add(args.name, args.email)
    elif args.cmd == "show":
        c = store.get(args.name)
        if c is None:
            print(f"no contact {args.name}", file=sys.stderr)
            return 1
        print(f"name: {c.name}")
        print(f"email: {c.email}")
    elif args.cmd == "export":
        sys.stdout.write(to_csv(store.all()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
