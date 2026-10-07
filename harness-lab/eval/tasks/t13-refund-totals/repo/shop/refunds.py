from shop.models import Order


def refunded_cents(order: Order) -> int:
    """Total refunded for an order, tax included (refunds are recorded tax-included)."""
    return sum(order.refunds)


def is_fully_refunded(order: Order, net: int) -> bool:
    return refunded_cents(order) >= net
