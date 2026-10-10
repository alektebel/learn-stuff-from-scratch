"""Vector Index From Scratch — stage 10: the frontier, and choosing a point on it

DESIGN DECISION — compare at equal recall, never at equal parameters.
    "IVF with nprobe=8 is 12x faster than exact" is not a result: recall is the
    axis that got dropped. Every index here is a dial (nprobe, ef, bits per
    dimension), and a dial turns two numbers at once. So the comparison function
    takes indexes that have ALREADY been tuned — binding a dial is a decision,
    made before the measurement — and reports what each one costs and what it
    gets. Choosing is then a policy on top of measured rows, not a guess from
    parameter values that do not share a scale.

    The three numbers are the whole subject: bytes per vector (what it costs to
    hold), recall@k against the exact index (what it gets), and visited vectors
    per query (what it costs to ask).

TODO: implement

    compare(entries, exact, queries, k) -> list[dict]
        `entries` is an iterable of:
            {"name": str, "search": callable, "bytes_per_vector": int}
        and search(query, k) -> (rows, visited): the rows the tuned index
        returns (a list of (key, score)) and the work it did. Binding an
        index's dials into that closure is the caller's job — it is what
        "already tuned" means.
        One row per entry:
            {"name", "bytes_per_vector", "recall", "visited"}
        recall: the mean of recall_at_k(gold, rows, k) over the queries, where
        gold is the exact index's top-k ids for the query (stage 1's metric: the
        denominator is the relevant documents, not k). visited: the mean work
        per query. Rows sorted by bytes_per_vector ascending, ties by name —
        the cheap end of the frontier first.

    choose(rows, recall_floor) -> str
        the name of the row with the fewest bytes whose recall >= recall_floor;
        ties by name. ValueError when no row reaches the floor: a fallback that
        quietly returns the fastest index regardless is how a recall floor stops
        meaning anything.
"""

from stage_01 import recall_at_k as _recall  # useful, import it if you like


def compare(entries, exact, queries, k):
    raise NotImplementedError("stage 10: implement compare()")


def choose(rows, recall_floor):
    raise NotImplementedError("stage 10: implement choose()")
