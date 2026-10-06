"""Writes docs/changelog.md: ~600 deterministic entries (~60 KB) so that reading it in
full pushes the session's early constraint far back in the context."""

import random
from pathlib import Path

AREAS = ["auth", "invoices", "exports", "search", "billing", "notifications", "reports", "api"]
VERBS = ["Fix", "Improve", "Refactor", "Add", "Remove", "Document", "Speed up"]


def build(dest: Path) -> None:
    rng = random.Random(15)
    lines = ["# Changelog", ""]
    for i in range(600, 0, -1):
        area = rng.choice(AREAS)
        detail = " ".join(rng.choice(["edge", "case", "handling", "retry", "cache", "format",
                                      "timezone", "pagination", "locale", "rounding"]) for _ in range(8))
        lines.append(f"- 2.{i // 50}.{i % 50}: {rng.choice(VERBS)} {area}: {detail}.")
    (dest / "docs").mkdir(exist_ok=True)
    (dest / "docs" / "changelog.md").write_text("\n".join(lines) + "\n")
