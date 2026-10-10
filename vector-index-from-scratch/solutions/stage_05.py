"""Vector Index From Scratch — stage 5: the frontier, and the set you must not tune on

SOLUTION. recall is measured against the exact index's top-k for the same
query, never against the approximate answer; `report` tunes on one set and
measures the same nprobe on another, and returns both numbers so the gap is
visible in the output rather than inferred from the code.
"""

from stage_01 import recall_at_k


def _measure(index, exact, queries, k, nprobe):
    total_recall = 0.0
    total_work = 0.0
    for query in queries:
        gold = [key for key, _ in exact.search(query, k)]
        rows = index.search(query, k, nprobe=nprobe)
        total_recall += recall_at_k(gold, [key for key, _ in rows], k)
        total_work += index.visited
    n = len(queries)
    return total_recall / n, total_work / n


def sweep(index, exact, queries, k, nprobes):
    rows = []
    for nprobe in nprobes:
        recall, work = _measure(index, exact, queries, k, nprobe)
        rows.append({"nprobe": nprobe, "recall": recall,
                     "visited": round(work)})
    return rows


def tune_nprobe(index, exact, queries, k, target, nprobes):
    for row in sorted(sweep(index, exact, queries, k, nprobes),
                      key=lambda r: r["nprobe"]):
        if row["recall"] >= target:
            return row["nprobe"]
    raise ValueError(
        f"no nprobe in {list(nprobes)} reaches a recall of {target} on these "
        f"queries")


def report(index, exact, tune_queries, held_out, k, target):
    candidates = list(range(1, index.nlist + 1))
    nprobe = tune_nprobe(index, exact, tune_queries, k, target, candidates)
    tune_recall = _measure(index, exact, tune_queries, k, nprobe)[0]
    held_recall = _measure(index, exact, held_out, k, nprobe)[0]
    return {"nprobe": nprobe, "tune_recall": tune_recall,
            "held_out_recall": held_recall}
