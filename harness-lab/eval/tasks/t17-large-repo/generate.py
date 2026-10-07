"""Generates bigapp/: ~350 modules, ~1.5 MB of Python, far beyond a context window.

Only four modules matter (api, registry, handlers/discount, codes/normalize). The rest are
plausible, importable filler with overlapping vocabulary (codes, discounts, amounts), so
that grep for a single keyword returns many hits and reading everything does not fit.
"""

import random
from pathlib import Path

API = '''from bigapp.registry import HANDLERS


def handle(kind: str, **kwargs):
    return HANDLERS[kind](**kwargs)
'''

REGISTRY = '''from bigapp.handlers.discount import apply_discount
from bigapp.handlers.refund_window import refund_window_days

HANDLERS = {
    "discount": apply_discount,
    "refund_window": refund_window_days,
}
'''

DISCOUNT = '''from bigapp.codes.normalize import normalize_code
from bigapp.codes.table import PROMOTIONS


def apply_discount(code: str, amount_cents: int) -> int:
    pct = PROMOTIONS.get(normalize_code(code), 0)
    return amount_cents - amount_cents * pct // 100
'''

REFUND = '''def refund_window_days(tier: str = "standard") -> int:
    return {"standard": 14, "gold": 30}.get(tier, 14)
'''

NORMALIZE = '''def normalize_code(code: str) -> str:
    """Canonical form used as the key of PROMOTIONS."""
    return code.strip().lower()
'''

TABLE = '''PROMOTIONS = {
    "SPRING25": 25,
    "WELCOME10": 10,
    "BLACKFRIDAY40": 40,
}
'''

WORDS = ["code", "discount", "amount", "promo", "ledger", "invoice", "tax", "cart", "sku", "rate",
         "batch", "quota", "window", "tier", "region", "coupon", "audit", "export", "token", "price"]


def _filler(rng: random.Random, idx: int) -> str:
    out = [f'"""Module {idx}: {" ".join(rng.sample(WORDS, 4))} utilities."""', ""]
    for f in range(rng.randint(12, 20)):
        a, b = rng.sample(WORDS, 2)
        name = f"{a}_{b}_{idx}_{f}"
        const = rng.randint(1, 999)
        out += [
            f"def {name}(value, factor={const}):",
            f'    """Compute {a} {b} adjustment for {" ".join(rng.sample(WORDS, 3))}."""',
            "    if value is None:",
            "        return 0",
            f"    if isinstance(value, str):",
            f"        value = value.strip().upper().replace('-', '')",
            f"        return len(value) * factor % {rng.randint(7, 97)}",
            f"    return (value * factor + {rng.randint(0, 50)}) // {rng.randint(2, 9)}",
            "",
            "",
        ]
    return "\n".join(out)


def build(dest: Path) -> None:
    rng = random.Random(17)
    pkg = dest / "bigapp"
    for sub in ["", "handlers", "codes"] + [f"area{i:02d}" for i in range(14)]:
        (pkg / sub).mkdir(parents=True, exist_ok=True)
        (pkg / sub / "__init__.py").write_text("")
    (pkg / "api.py").write_text(API)
    (pkg / "registry.py").write_text(REGISTRY)
    (pkg / "handlers" / "discount.py").write_text(DISCOUNT)
    (pkg / "handlers" / "refund_window.py").write_text(REFUND)
    (pkg / "codes" / "normalize.py").write_text(NORMALIZE)
    (pkg / "codes" / "table.py").write_text(TABLE)
    idx = 0
    for area in range(14):
        for _ in range(25):
            (pkg / f"area{area:02d}" / f"{rng.choice(WORDS)}_{idx:03d}.py").write_text(_filler(rng, idx))
            idx += 1
