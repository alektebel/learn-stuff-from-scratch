"""Evals From Scratch — stage 1: the eval set, and the split that must not leak

DESIGN DECISION — split by source, not by row.
    An eval set assembled from real traffic contains near-duplicates: five
    phrasings of the same support ticket, a template that fills a variable, the
    same document summarised twice. Split those rows at random and the test set
    contains a copy of something the model has already been tuned against, so
    the score measures recall of the training set — the highest number you will
    ever see, and the least informative. Group the rows by where they came from
    and keep a whole group on one side of the split.

DESIGN DECISION — the split is a function, not an afternoon.
    `split()` takes the seed and returns the same three lists every time it is
    called with it. An eval set that changes shape between runs makes every
    comparison against a previous run meaningless, which is the one thing an
    eval set exists to support.

TODO: implement

    load(records) -> list[dict]
        Validate and normalise the rows: every row needs the keys "id" (unique)
        and "group" (non-empty string); raise ValueError naming the row
        otherwise. Return a copy of each row, in order.

    split(records, ratios=(0.6, 0.2, 0.2), seed=0) -> dict
        {"train": [...], "dev": [...], "test": [...]}
        Groups are assigned whole: no group key appears in two splits. The
        split sizes follow `ratios` as closely as whole groups allow, and the
        assignment is deterministic in `seed`. ValueError when ratios do not
        sum to 1.0, when there are fewer groups than nonzero splits.

    overlap(a, b) -> set of group keys present in both lists
"""


def load(records):
    raise NotImplementedError("stage 1: implement load()")


def split(records, ratios=(0.6, 0.2, 0.2), seed=0):
    raise NotImplementedError("stage 1: implement split()")


def overlap(a, b):
    raise NotImplementedError("stage 1: implement overlap()")
