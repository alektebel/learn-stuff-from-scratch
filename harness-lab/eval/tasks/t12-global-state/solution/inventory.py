class Inventory:
    def __init__(self) -> None:
        self._stock: dict[str, int] = {}

    def add(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        self._stock[sku] = self._stock.get(sku, 0) + qty

    def remove(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        have = self._stock.get(sku, 0)
        if qty > have:
            raise KeyError(f"insufficient stock for {sku}: have {have}, need {qty}")
        self._stock[sku] = have - qty

    def quantity(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def skus(self) -> list[str]:
        return sorted(s for s, q in self._stock.items() if q > 0)
