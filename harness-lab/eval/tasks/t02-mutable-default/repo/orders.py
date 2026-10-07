from dataclasses import dataclass


class Order:
    def __init__(self, customer: str, lines=[]):
        self.customer = customer
        self.lines = lines

    def add(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        self.lines.append((sku, qty))

    def total_qty(self) -> int:
        return sum(q for _, q in self.lines)

    def merge(self, other: "Order") -> "Order":
        if other.customer != self.customer:
            raise ValueError("cannot merge orders of different customers")
        merged = other
        merged.lines.extend(self.lines)
        return merged
