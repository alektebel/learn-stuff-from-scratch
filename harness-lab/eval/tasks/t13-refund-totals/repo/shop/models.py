from dataclasses import dataclass, field


@dataclass
class Line:
    sku: str
    qty: int
    unit_cents: int


@dataclass
class Order:
    id: int
    customer: str
    lines: list[Line] = field(default_factory=list)
    refunds: list[int] = field(default_factory=list)  # refunded amounts in cents
