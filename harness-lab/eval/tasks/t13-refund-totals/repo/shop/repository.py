from shop.models import Line, Order

_ORDERS = [
    Order(1, "ana", [Line("book", 2, 1500)]),
    Order(2, "ana", [Line("pen", 10, 120)], refunds=[500]),
    Order(3, "bob", [Line("lamp", 1, 4000)], refunds=[4840]),
    Order(4, "carla", [Line("mug", 3, 800), Line("tea", 1, 650)]),
    Order(5, "bob", [Line("desk", 1, 20000)], refunds=[1000, 2000]),
]


def all_orders() -> list[Order]:
    return list(_ORDERS)
