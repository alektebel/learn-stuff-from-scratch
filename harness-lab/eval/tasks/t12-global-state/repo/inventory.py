_STOCK: dict[str, int] = {}


def add(sku: str, qty: int) -> None:
    if qty <= 0:
        raise ValueError("qty must be positive")
    _STOCK[sku] = _STOCK.get(sku, 0) + qty


def remove(sku: str, qty: int) -> None:
    if qty <= 0:
        raise ValueError("qty must be positive")
    have = _STOCK.get(sku, 0)
    if qty > have:
        raise KeyError(f"insufficient stock for {sku}: have {have}, need {qty}")
    _STOCK[sku] = have - qty


def quantity(sku: str) -> int:
    return _STOCK.get(sku, 0)


def skus() -> list[str]:
    return sorted(s for s, q in _STOCK.items() if q > 0)
