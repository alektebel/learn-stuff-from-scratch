from inventory import Inventory


def low_stock(inv: Inventory, threshold: int) -> list[str]:
    return [s for s in inv.skus() if inv.quantity(s) < threshold]
