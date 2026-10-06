import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

RATES_FILE = Path(__file__).with_name("rates.json")


def calc_monthly_rate(plan: str) -> Decimal:
    rates = json.loads(RATES_FILE.read_text())
    return Decimal(rates[plan])


def calc_subscription_price(plan: str, months: int) -> Decimal:
    if months < 1:
        raise ValueError("months must be >= 1")
    total = calc_monthly_rate(plan) * months
    if months >= 12:
        total *= Decimal("0.9")
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
