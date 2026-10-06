import inventory


def low_stock(threshold: int) -> list[str]:
    return [s for s in inventory.skus() if inventory.quantity(s) < threshold]
