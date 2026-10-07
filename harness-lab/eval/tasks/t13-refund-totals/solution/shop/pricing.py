from shop.models import Order
from shop.refunds import refunded_cents
from shop.tax import with_tax


def gross_cents(order: Order) -> int:
    return sum(l.qty * l.unit_cents for l in order.lines)


def net_cents(order: Order) -> int:
    """Amount actually kept by the shop for this order, tax included."""
    return max(0, with_tax(gross_cents(order)) - refunded_cents(order))
