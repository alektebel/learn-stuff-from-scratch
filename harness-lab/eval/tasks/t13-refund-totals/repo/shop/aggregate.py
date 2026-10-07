from collections import defaultdict

from shop.pricing import net_cents


def revenue_by_customer(orders) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for o in orders:
        totals[o.customer] += net_cents(o)
    return dict(totals)
