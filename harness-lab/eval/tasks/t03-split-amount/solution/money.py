def split_amount(total_cents: int, n: int) -> list[int]:
    if n < 1 or total_cents < 0:
        raise ValueError("need n >= 1 and total_cents >= 0")
    base, extra = divmod(total_cents, n)
    return [base + 1] * extra + [base] * (n - extra)
