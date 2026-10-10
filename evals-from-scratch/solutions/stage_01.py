"""Evals From Scratch — stage 1: the eval set, and the split that must not leak

SOLUTION. load() validates and copies; split() shuffles GROUPS (never rows) with
a seeded RNG, fills the splits to their target sizes, and parks any leftover
group in the split that is furthest under its target. Nothing here is subtle —
which is the point: the leak is not a bug in this function, it is a bug in
every function downstream of it that treats the test set as unseen.
"""

import random

NAMES = ("train", "dev", "test")


def load(records):
    rows = []
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"row is not a mapping: {record!r}")
        rid = record.get("id")
        if not rid:
            raise ValueError(f"row without an id: {record!r}")
        group = record.get("group")
        if not group:
            raise ValueError(
                f"row {rid!r} does not say which group it belongs to: rows that "
                f"come from one source have to be marked, or the split cannot "
                f"keep them together")
        if rid in seen:
            raise ValueError(
                f"duplicate id {rid!r}: one row wearing two ids is one row too "
                f"many in every count that follows")
        seen.add(rid)
        rows.append(dict(record))
    return rows


def split(records, ratios=(0.6, 0.2, 0.2), seed=0):
    if len(ratios) != len(NAMES):
        raise ValueError(f"ratios must describe {len(NAMES)} splits: {ratios!r}")
    if abs(sum(ratios) - 1.0) > 1e-9:
        raise ValueError(
            f"ratios must sum to 1.0: {ratios!r} sums to {sum(ratios):.6f}")

    rows = load(records)
    groups = {}
    for row in rows:
        groups.setdefault(row["group"], []).append(row)

    active = [name for name, share in zip(NAMES, ratios) if share > 0]
    if len(groups) < len(active):
        raise ValueError(
            f"{len(groups)} group(s) cannot fill {len(active)} non-empty "
            f"splits: whichever split is short would have to borrow rows from "
            f"an identical one")
    if not rows:
        raise ValueError("no rows to split")

    order = sorted(groups)
    random.Random(seed).shuffle(order)

    targets = {name: len(rows) * share for name, share in zip(NAMES, ratios)}
    out = {name: [] for name in NAMES}
    filled = {name: 0 for name in NAMES}

    for name in NAMES:
        if name not in active:
            continue
        while order and filled[name] < targets[name]:
            take = order.pop()
            out[name].extend(groups[take])
            filled[name] += len(groups[take])

    while order:                     # whole groups that no split had room for
        take = order.pop()
        name = min(active, key=lambda n: filled[n] - targets[n])
        out[name].extend(groups[take])
        filled[name] += len(groups[take])

    return out


def overlap(left, right):
    return {row["group"] for row in left} & {row["group"] for row in right}
