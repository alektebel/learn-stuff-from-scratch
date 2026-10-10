"""Vector Index From Scratch — stage 10: the frontier, and choosing a point on it

SOLUTION. compare() measures three numbers per index — bytes per vector, recall
against the exact index, and work per query — and sorts the cheap end first.
choose() is a filter plus a sort: the fewest bytes that still meet the floor.
"""

from stage_01 import recall_at_k


def compare(entries, exact, queries, k):
    rows = []
    for entry in entries:
        total_recall = 0.0
        total_work = 0.0
        for query in queries:
            gold = [key for key, _ in exact.search(query, k)]
            got, visited = entry["search"](query, k)
            total_recall += recall_at_k(gold, [key for key, _ in got], k)
            total_work += visited
        n = len(queries)
        rows.append({"name": entry["name"],
                     "bytes_per_vector": entry["bytes_per_vector"],
                     "recall": total_recall / n,
                     "visited": round(total_work / n)})
    rows.sort(key=lambda r: (r["bytes_per_vector"], r["name"]))
    return rows


def choose(rows, recall_floor):
    eligible = [r for r in rows if r["recall"] >= recall_floor]
    if not eligible:
        raise ValueError(f"no index in these rows reaches recall {recall_floor}")
    eligible.sort(key=lambda r: (r["bytes_per_vector"], r["name"]))
    return eligible[0]["name"]
