class Order:
    def __init__(self, customer: str, lines=None):
        self.customer = customer
        self.lines = list(lines) if lines is not None else []

    def add(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        self.lines.append((sku, qty))

    def total_qty(self) -> int:
        return sum(q for _, q in self.lines)

    def merge(self, other: "Order") -> "Order":
        if other.customer != self.customer:
            raise ValueError("cannot merge orders of different customers")
        return Order(self.customer, self.lines + other.lines)
