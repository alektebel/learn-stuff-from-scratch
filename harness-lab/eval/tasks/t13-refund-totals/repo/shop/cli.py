import sys

from shop.aggregate import revenue_by_customer
from shop.formatting import euros
from shop.repository import all_orders


def export() -> str:
    totals = revenue_by_customer(all_orders())
    return "\n".join(f"{c};{euros(t)}" for c, t in sorted(totals.items()))


if __name__ == "__main__":
    if sys.argv[1:] == ["export"]:
        print(export())
    else:
        sys.exit("usage: python -m shop.cli export")
