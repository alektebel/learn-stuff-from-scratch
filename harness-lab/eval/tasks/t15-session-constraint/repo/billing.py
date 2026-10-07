import json
from decimal import Decimal
from pathlib import Path

RATES_FILE = Path(__file__).with_name("rates.json")


def calc_monthly_rate(plan: str) -> Decimal:
    rates = json.loads(RATES_FILE.read_text())
    return Decimal(rates[plan])
