"""Vector Index From Scratch — stage 5: the frontier, and the set you must not tune on

DESIGN DECISION — the ground truth is the exact index, not a labelled set.
    recall@k is measured against the exact top-k for each query. That is the
    whole reason stage 1 exists: a hand-labelled set can only speak about the
    documents a human thought to label, and it cannot tell a better partition
    from a luckier one. Here the truth is computed, so it is complete.

DESIGN DECISION — tune on one set of queries, report on another.
    A parameter tuned until the numbers look good on the queries you then
    report is a number about your tuning set. It is the cheapest overfitting in
    the field and it is invisible in the output: `nprobe = 8, recall 0.94` looks
    like a result whether the 0.94 came from the same queries that chose the 8
    or from ones the 8 never saw. `report` returns both numbers so the gap is
    visible, and the check builds a corpus where the gap is large on purpose.

TODO: implement

    sweep(index, exact, queries, k, nprobes) -> list[dict]
        one row per nprobe, in the order given:
            {"nprobe": int, "recall": float, "visited": int}
        gold for a query is the exact index's top-k ids for it; recall is the
        mean of recall_at_k(gold, approx_rows, k) over the queries (stage 1 —
        the denominator is the relevant documents, not k). "visited" is the mean
        work per query. recall must not decrease as nprobe grows.

    tune_nprobe(index, exact, queries, k, target, nprobes) -> int
        the smallest nprobe in `nprobes` whose measured recall is >= target.
        ValueError when none of them reaches it — silently returning the largest
        would report a parameter that does not do what it says.

    report(index, exact, tune_queries, held_out, k, target) -> dict
        {"nprobe": int, "tune_recall": float, "held_out_recall": float}
        Tune over every nprobe from 1 to index.nlist (all of them — this is the
        full sweep, not a shortlist), then measure the SAME nprobe on held_out.
        Both recalls come from sweep-like measurement; the point is that they
        are allowed to disagree, and the name says which is which.
"""

from stage_01 import recall_at_k as _recall  # useful, import it if you like


def sweep(index, exact, queries, k, nprobes):
    raise NotImplementedError("stage 5: implement sweep()")


def tune_nprobe(index, exact, queries, k, target, nprobes):
    raise NotImplementedError("stage 5: implement tune_nprobe()")


def report(index, exact, tune_queries, held_out, k, target):
    raise NotImplementedError("stage 5: implement report()")
