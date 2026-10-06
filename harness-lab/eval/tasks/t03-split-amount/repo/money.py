def split_amount(total_cents: int, n: int) -> list[int]:
    share = round(total_cents / n)
    return [share] * n
