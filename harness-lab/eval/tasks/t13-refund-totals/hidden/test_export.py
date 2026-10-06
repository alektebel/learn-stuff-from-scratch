from shop.cli import export
from shop.models import Line, Order
from shop.pricing import net_cents


def test_export():
    # ana: 3630 + (1452 - 500) = 4582; bob: (4840 - 4840) + (24200 - 3000) = 21200; carla: 3691
    assert export().splitlines() == ["ana;45.82", "bob;212.00", "carla;36.91"]


def test_full_refund_is_zero_and_never_negative():
    o = Order(9, "z", [Line("x", 1, 100)], refunds=[121, 50])
    assert net_cents(o) == 0
