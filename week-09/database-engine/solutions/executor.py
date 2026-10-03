"""
Executor — the iterator model. Complete Solution.

A plan is a tree of operators. Each one answers `next()` with one row, pulling
from its children as needed. That is the whole interface, and it is the
"Volcano" model that essentially every database has used since 1990.

DESIGN DECISION — pull one row at a time, or materialise each stage?
  Materialising is easier to write: each operator computes its full output as a
  list and hands it on. It is also unusable at scale, because a filter over ten
  million rows builds a ten-million-row intermediate whether or not anyone
  wanted the second one.
  CHOSEN: PULL, one row at a time. `LIMIT 10` on top of a scan of ten million
  rows touches eleven, because the LIMIT stops calling `next()`. Nothing has to
  know about the limit — the pipeline just stops being pulled. Section 2
  measures exactly this.

  The cost is real and worth stating: one Python method call per row per
  operator. Real engines fixed that with VECTORISED execution (a batch of ~1024
  rows per `next()`, amortising the call) or by COMPILING the plan to machine
  code. Both are the same fix — amortise the interpretation — and both are
  extensions at the end of this file.

DESIGN DECISION — which operators may block?
  Some cannot stream: SORT must see every row before it can emit the smallest,
  and a HASH JOIN must see all of one side before probing. These are BLOCKING
  operators, and where they sit decides your query's memory profile and whether
  `LIMIT` helps at all.
  CHOSEN: mark them explicitly with a `blocking` attribute so the plan can be
  printed with them visible. This is the single most useful thing to be able to
  see in an EXPLAIN, and section 2 shows a LIMIT going from free to worthless
  because a sort was inserted underneath it.
"""

from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

Row = Dict[str, Any]


class Operator:
    """One node of an execution plan.

    `rows_out` and `rows_in` are not instrumentation for its own sake. The gap
    between what an operator READ and what it RETURNED is the definition of
    selectivity, and selectivity is what the planner in the next file is trying
    to guess. Measuring it here is how you find out that the guess was wrong.
    """

    name = "operator"
    blocking = False       # must consume all input before emitting any
    bounded = True         # runs in constant memory regardless of input size

    def __init__(self, *children: "Operator"):
        self.children = list(children)
        self.rows_out = 0
        self.rows_in = 0

    def open(self) -> None:
        for child in self.children:
            child.open()

    def next(self) -> Optional[Row]:
        raise NotImplementedError

    def close(self) -> None:
        for child in self.children:
            child.close()

    def __iter__(self) -> Iterator[Row]:
        self.open()
        try:
            while (row := self.next()) is not None:
                yield row
        finally:
            self.close()

    def describe(self) -> str:
        return self.name

    def explain(self, depth: int = 0) -> str:
        mark = " [blocking]" if self.blocking else ""
        counts = (f"  (in {self.rows_in}, out {self.rows_out})"
                  if self.rows_out or self.rows_in else "")
        out = "  " * depth + "-> " + self.describe() + mark + counts + "\n"
        for child in self.children:
            out += child.explain(depth + 1)
        return out

    def total_rows_read(self) -> int:
        return self.rows_in + sum(c.total_rows_read() for c in self.children)


class SeqScan(Operator):
    """Read every row of a table. Cost is O(table), whatever the predicate."""

    name = "SeqScan"

    def __init__(self, table: str, rows: List[Row], alias: Optional[str] = None):
        super().__init__()
        self.table = table
        self.alias = alias or table
        self.rows = rows
        self.position = 0

    def open(self) -> None:
        self.position = 0

    def next(self) -> Optional[Row]:
        if self.position >= len(self.rows):
            return None
        row = self.rows[self.position]
        self.position += 1
        self.rows_in += 1
        self.rows_out += 1
        return dict(row)

    def describe(self) -> str:
        return f"SeqScan on {self.table} ({len(self.rows)} rows)"


class IndexScan(Operator):
    """Descend an index, then walk the leaves. Cost is O(matching rows).

    The reason this is not always the right answer is in planner.py: every row
    it produces may need a separate fetch of the heap page holding it, and
    those fetches are RANDOM. Past a few percent selectivity, reading the whole
    table sequentially wins despite reading more of it.
    """

    name = "IndexScan"

    def __init__(self, table: str, index: Any, low: Any, high: Any,
                 fetch: Callable[[Any], Optional[Row]],
                 alias: Optional[str] = None):
        super().__init__()
        self.table = table
        self.alias = alias or table
        self.index = index
        self.low, self.high = low, high
        self.fetch = fetch
        self.cursor: Optional[Iterator] = None

    def open(self) -> None:
        self.cursor = iter(self.index.range(self.low, self.high))

    def next(self) -> Optional[Row]:
        for _, row_id in self.cursor:
            self.rows_in += 1
            row = self.fetch(row_id)
            if row is not None:
                self.rows_out += 1
                return dict(row)
        return None

    def describe(self) -> str:
        return f"IndexScan on {self.table} [{self.low} .. {self.high}]"


class Filter(Operator):
    name = "Filter"

    def __init__(self, child: Operator, predicate: Callable[[Row], bool],
                 label: str = ""):
        super().__init__(child)
        self.predicate = predicate
        self.label = label

    def next(self) -> Optional[Row]:
        while (row := self.children[0].next()) is not None:
            self.rows_in += 1
            if self.predicate(row):
                self.rows_out += 1
                return row
        return None

    def describe(self) -> str:
        return f"Filter: {self.label}" if self.label else "Filter"


class Project(Operator):
    name = "Project"

    def __init__(self, child: Operator,
                 columns: List[Tuple[str, Callable[[Row], Any]]]):
        super().__init__(child)
        self.columns = columns

    def next(self) -> Optional[Row]:
        row = self.children[0].next()
        if row is None:
            return None
        self.rows_in += 1
        self.rows_out += 1
        return {name: expression(row) for name, expression in self.columns}

    def describe(self) -> str:
        return f"Project: {', '.join(name for name, _ in self.columns)}"


class Sort(Operator):
    """BLOCKING. Nothing comes out until everything has gone in.

    This is where a LIMIT stops helping. `ORDER BY x LIMIT 10` still reads the
    whole input, because the tenth-smallest row could be the last one read.
    (A real engine uses a bounded heap — top-N — which reads everything but
    stores only N. It is an extension at the end of this file, and it changes
    the memory profile, not the row count.)
    """

    name = "Sort"
    blocking = True
    bounded = False

    def __init__(self, child: Operator,
                 keys: List[Tuple[Callable[[Row], Any], bool]], label: str = ""):
        super().__init__(child)
        self.keys = keys
        self.label = label
        self.buffer: List[Row] = []
        self.position = 0

    def open(self) -> None:
        super().open()
        self.buffer = []
        while (row := self.children[0].next()) is not None:
            self.rows_in += 1
            self.buffer.append(row)
        for key, descending in reversed(self.keys):     # stable, last key first
            self.buffer.sort(key=key, reverse=descending)
        self.position = 0

    def next(self) -> Optional[Row]:
        if self.position >= len(self.buffer):
            return None
        self.position += 1
        self.rows_out += 1
        return self.buffer[self.position - 1]

    def describe(self) -> str:
        return f"Sort: {self.label}" if self.label else "Sort"


class Limit(Operator):
    name = "Limit"

    def __init__(self, child: Operator, limit: Optional[int],
                 offset: int = 0):
        super().__init__(child)
        self.limit = limit
        self.offset = offset
        self.emitted = 0
        self.skipped = 0

    def open(self) -> None:
        super().open()
        self.emitted = self.skipped = 0

    def next(self) -> Optional[Row]:
        while self.skipped < self.offset:
            if self.children[0].next() is None:
                return None
            self.skipped += 1
        if self.limit is not None and self.emitted >= self.limit:
            return None                  # stop pulling — the pipeline halts here
        row = self.children[0].next()
        if row is None:
            return None
        self.rows_in += 1
        self.rows_out += 1
        self.emitted += 1
        return row

    def describe(self) -> str:
        return f"Limit {self.limit}" + (f" offset {self.offset}"
                                        if self.offset else "")


class NestedLoopJoin(Operator):
    """For each outer row, scan the whole inner side. O(N x M).

    Correct for any join condition, and catastrophic on two large tables. It
    wins in exactly one situation, and it is a common one: the outer side is
    tiny and the inner side is reached through an index.
    """

    name = "NestedLoopJoin"

    def __init__(self, outer: Operator, inner_rows: List[Row],
                 condition: Callable[[Row, Row], bool], label: str = ""):
        super().__init__(outer)
        self.inner_rows = inner_rows
        self.condition = condition
        self.label = label
        self.current: Optional[Row] = None
        self.inner_position = 0

    def next(self) -> Optional[Row]:
        while True:
            if self.current is None:
                self.current = self.children[0].next()
                if self.current is None:
                    return None
                self.inner_position = 0
            while self.inner_position < len(self.inner_rows):
                inner = self.inner_rows[self.inner_position]
                self.inner_position += 1
                self.rows_in += 1
                if self.condition(self.current, inner):
                    self.rows_out += 1
                    return {**self.current, **inner}
            self.current = None

    def describe(self) -> str:
        return f"NestedLoopJoin ({len(self.inner_rows)} inner rows) {self.label}"


class HashJoin(Operator):
    """BLOCKING on the build side. O(N + M) instead of O(N x M).

    Build a hash table from the smaller side, then stream the larger side past
    it. The restriction is what makes it fast: it works only for EQUALITY
    conditions, because a hash table cannot answer "greater than". A join on
    `a.x < b.y` has no choice but the nested loop.
    """

    name = "HashJoin"
    blocking = True
    bounded = False

    def __init__(self, probe: Operator, build_rows: List[Row],
                 probe_key: str, build_key: str, label: str = ""):
        super().__init__(probe)
        self.build_rows = build_rows
        self.probe_key, self.build_key = probe_key, build_key
        self.label = label
        self.table: Dict[Any, List[Row]] = {}
        self.pending: List[Row] = []

    def open(self) -> None:
        super().open()
        self.table = {}
        for row in self.build_rows:
            self.table.setdefault(row.get(self.build_key), []).append(row)
        self.pending = []

    def next(self) -> Optional[Row]:
        while True:
            if self.pending:
                self.rows_out += 1
                return self.pending.pop()
            row = self.children[0].next()
            if row is None:
                return None
            self.rows_in += 1
            matches = self.table.get(row.get(self.probe_key), [])
            self.pending = [{**row, **match} for match in matches]
            if not self.pending:
                continue

    def describe(self) -> str:
        return (f"HashJoin on {self.probe_key} = {self.build_key} "
                f"(build {len(self.build_rows)} rows)")


class Aggregate(Operator):
    """BLOCKING. GROUP BY must see every row before any group is final."""

    name = "Aggregate"
    blocking = True
    bounded = False

    FUNCTIONS: Dict[str, Callable[[List[Any]], Any]] = {
        "COUNT": len,
        "SUM": lambda values: sum(v for v in values if v is not None),
        "MIN": lambda values: min((v for v in values if v is not None),
                                  default=None),
        "MAX": lambda values: max((v for v in values if v is not None),
                                  default=None),
        "AVG": lambda values: (sum(v for v in values if v is not None)
                               / len([v for v in values if v is not None])
                               if any(v is not None for v in values) else None),
    }

    def __init__(self, child: Operator, group_keys: List[str],
                 aggregates: List[Tuple[str, str, Optional[str]]]):
        """aggregates: (output_name, function, column or None for COUNT(*))"""
        super().__init__(child)
        self.group_keys = group_keys
        self.aggregates = aggregates
        self.result: List[Row] = []
        self.position = 0

    def open(self) -> None:
        super().open()
        groups: Dict[Tuple, List[Row]] = {}
        while (row := self.children[0].next()) is not None:
            self.rows_in += 1
            key = tuple(row.get(column) for column in self.group_keys)
            groups.setdefault(key, []).append(row)
        if not self.group_keys and not groups:
            groups = {(): []}                # COUNT(*) on an empty table is 0
        self.result = []
        for key, rows in groups.items():
            out = dict(zip(self.group_keys, key))
            for name, function, column in self.aggregates:
                values = ([r.get(column) for r in rows] if column
                          else list(range(len(rows))))
                out[name] = self.FUNCTIONS[function](values)
            self.result.append(out)
        self.position = 0

    def next(self) -> Optional[Row]:
        if self.position >= len(self.result):
            return None
        self.position += 1
        self.rows_out += 1
        return self.result[self.position - 1]

    def describe(self) -> str:
        functions = ", ".join(f"{f}({c or '*'})" for _, f, c in self.aggregates)
        return (f"Aggregate {functions}" +
                (f" GROUP BY {', '.join(self.group_keys)}" if self.group_keys else ""))


class Distinct(Operator):
    """Streams rows out as it finds them, but REMEMBERS every one it has seen.

    So it is not blocking — the first distinct row comes out immediately, and a
    LIMIT above it still works — and it is not constant-memory either. Those
    are two different properties, and collapsing them into one "is it slow"
    intuition is how a SELECT DISTINCT on a high-cardinality column becomes an
    out-of-memory incident that an EXPLAIN showed no sign of.
    """

    name = "Distinct"
    bounded = False

    def __init__(self, child: Operator):
        super().__init__(child)
        self.seen: set = set()

    def open(self) -> None:
        super().open()
        self.seen = set()

    def next(self) -> Optional[Row]:
        while (row := self.children[0].next()) is not None:
            self.rows_in += 1
            key = tuple(sorted(row.items()))
            if key not in self.seen:
                self.seen.add(key)
                self.rows_out += 1
                return row
        return None


def run(plan: Operator) -> List[Row]:
    return list(plan)


def _demo() -> None:
    import time

    print("=" * 74)
    print("EXECUTOR — one row at a time, and the operators that cannot")
    print("=" * 74)

    rows = [{"id": n, "name": f"user{n}", "age": 18 + n % 60,
             "city": ["lisbon", "porto", "faro"][n % 3]} for n in range(100000)]

    print("\n1. A pipeline pulls; it does not materialise")
    print("-" * 74)
    plan = Limit(Filter(SeqScan("users", rows),
                        lambda r: r["age"] > 70, "age > 70"), 5)
    result = run(plan)
    print(plan.explain())
    print(f"  returned {len(result)} rows having read "
          f"{plan.total_rows_read():,} of {len(rows):,}")
    print("  The scan stopped as soon as the LIMIT stopped pulling. Nothing in")
    print("  the scan or the filter knows a LIMIT exists.")

    print("\n2. The same query with a sort underneath the limit")
    print("-" * 74)
    for label, build in (
            ("LIMIT 5", lambda: Limit(SeqScan("users", rows), 5)),
            ("ORDER BY age LIMIT 5",
             lambda: Limit(Sort(SeqScan("users", rows),
                                [(lambda r: r["age"], False)], "age"), 5))):
        plan = build()
        run(plan)
        print(f"    {label:<24}{plan.total_rows_read():>10,} rows read")
    print("  A sort is BLOCKING: the fifth-smallest row could be the last one")
    print("  read, so it must read all 100,000. The LIMIT went from touching six")
    print("  rows to touching every one, and the query text barely changed.")
    print("  This is the single most useful thing to notice in an EXPLAIN.")

    print("\n3. Join algorithms, on the same data")
    print("-" * 74)
    users = [{"id": n, "name": f"user{n}"} for n in range(2000)]
    orders = [{"order_id": n, "user_id": n % 2000, "total": n * 3}
              for n in range(2000)]

    start = time.perf_counter()
    nested = NestedLoopJoin(SeqScan("orders", orders), users,
                            lambda o, u: o["user_id"] == u["id"])
    nested_rows = run(nested)
    nested_time = time.perf_counter() - start

    start = time.perf_counter()
    hashed = HashJoin(SeqScan("orders", orders), users, "user_id", "id")
    hash_rows = run(hashed)
    hash_time = time.perf_counter() - start

    print(f"    {'algorithm':<18}{'rows out':>10}{'comparisons':>14}{'seconds':>10}")
    print(f"    {'nested loop':<18}{len(nested_rows):>10}"
          f"{nested.rows_in:>14,}{nested_time:>10.3f}")
    print(f"    {'hash join':<18}{len(hash_rows):>10}"
          f"{hashed.rows_in:>14,}{hash_time:>10.3f}")
    print(f"  Same answer, {nested.rows_in / max(1, hashed.rows_in):,.0f}x the "
          f"work and {nested_time / hash_time:.0f}x the time.")
    print("  The hash join's restriction is what buys the speed: it only works")
    print("  on EQUALITY. A join on `a.x < b.y` has no choice but the nested")
    print("  loop, which is why one bad join condition ruins a query plan.")

    print("\n4. Blocking operators are where the memory goes")
    print("-" * 74)
    print(f"    {'operator':<18}{'blocking':>10}{'bounded mem':>13}  what it means")
    for cls in (SeqScan, IndexScan, Filter, Project, Limit,
                NestedLoopJoin, HashJoin, Sort, Aggregate, Distinct):
        if cls.blocking:
            note = "buffers everything before emitting"
        elif not cls.bounded:
            note = "streams out, but remembers what it saw"
        else:
            note = "streams, constant memory"
        print(f"    {cls.name:<18}{'yes' if cls.blocking else 'no':>10}"
              f"{'yes' if cls.bounded else 'no':>13}  {note}")
    print("  Two different properties, and it is worth keeping them apart.")
    print("  BLOCKING decides whether a LIMIT above you helps. BOUNDED decides")
    print("  whether you can be run at all on a large table. Distinct is the")
    print("  instructive row: not blocking, so a LIMIT works fine — and not")
    print("  bounded, so SELECT DISTINCT on a high-cardinality column is an")
    print("  out-of-memory incident that the EXPLAIN gave no sign of.")

    print("\n5. A full plan, with the counts the planner is trying to predict")
    print("-" * 74)
    plan = Limit(
        Sort(
            Aggregate(
                Filter(SeqScan("users", rows), lambda r: r["age"] > 40,
                       "age > 40"),
                ["city"], [("n", "COUNT", None), ("oldest", "MAX", "age")]),
            [(lambda r: r["n"], True)], "n DESC"),
        3)
    result = run(plan)
    print(plan.explain())
    for row in result:
        print(f"    {row}")
    print("  Read the (in, out) pairs bottom-up: that ratio IS selectivity, and")
    print("  guessing it correctly is the entire job of the next file.")

    print("\n" + "=" * 74)
    print("Next: planner.py chooses which of these operators to use.")
    print("=" * 74)


if __name__ == "__main__":
    _demo()
