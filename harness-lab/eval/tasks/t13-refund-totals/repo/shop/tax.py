RATE_PERCENT = 21


def with_tax(cents: int) -> int:
    return cents + (cents * RATE_PERCENT + 50) // 100
