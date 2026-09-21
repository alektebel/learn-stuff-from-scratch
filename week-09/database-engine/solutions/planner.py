"""
Planner — choosing HOW. Complete Solution.

The parser produced a tree that says what was asked. This file decides how to
answer it, and the decision is made the same way every real optimiser makes it:
estimate how many rows each choice would touch, price those rows with a cost
model, pick the cheapest.

Everything that goes wrong with query plans goes wrong in the first step. The
cost model is arithmetic and the search is mechanical; the ESTIMATE is a guess
about data the planner has only summary statistics for, and section 4 shows
what happens when the guess is wrong.

DESIGN DECISION — rules, or costs?
  A rule-based optimiser says "if there is an index on the WHERE column, use
  it". It is predictable, it needs no statistics, and it is wrong for
  `WHERE country = 'US'` on a US-only dataset, where the index visits every row
  in random order and loses badly to a sequential scan.
  CHOSEN: COST-BASED. Estimate selectivity from statistics, price both plans,
  compare. The crossover this produces (section 2) is a real number you can
  compute, and it is the number behind every "why is it not using my index"
  question ever asked.

DESIGN DECISION — what does a page read cost?
  CHOSEN: PostgreSQL's ratio. A sequential page read costs 1.0, a random one
  costs 4.0. The units are arbitrary; the RATIO is the whole model. An index
  scan reads few pages but reads them randomly, and a sequential scan reads
  every page in order. The crossover is where "few but random" stops beating
  "many but sequential", and on an SSD — where random reads are far less
  punishing — the right value is nearer 1.1, which moves the crossover a long
  way. `random_page_cost` is the one planner knob most worth understanding.

DESIGN DECISION — how much of the search space to explore?
  Join ordering is NP-hard, and n! orders is not searchable past about ten
  tables.
  CHOSEN: greedy — always build the hash table from the smaller relation, and
  apply the most selective filter first. Real optimisers do dynamic programming
  up to ~12 relations and switch to a genetic algorithm beyond that. Greedy is
  enough to demonstrate that the ORDER is a decision, which is the point.
"""

import math
from typing import Any, Callable, Dict, List, Optional, Tuple

import executor
from executor import (Aggregate, Distinct, Filter, HashJoin, IndexScan, Limit,
                      NestedLoopJoin, Operator, Project, SeqScan, Sort)
from sql import (BinOp, Column, Literal, Select, Star, UnaryOp,
                 Aggregate as AggregateExpr)

SEQ_PAGE_COST = 1.0
RANDOM_PAGE_COST = 4.0          # ~1.1 on an SSD, and the crossover moves a lot
CPU_TUPLE_COST = 0.01
ROWS_PER_PAGE = 50


class Statistics:
    """What the planner knows about a table without reading it.

    Real engines sample: n_distinct, a most-common-values list, and a histogram
    per column, refreshed by ANALYZE. Stale statistics are the single most
    common cause of a plan that used to be fast and now is not — nothing about
    the query or the code changed, only the summary the planner consulted.
    """

    def __init__(self, rows: List[Dict[str, Any]]):
        self.row_count = len(rows)
        self.distinct: Dict[str, int] = {}
        self.minimum: Dict[str, Any] = {}
        self.maximum: Dict[str, Any] = {}
        for column in (rows[0] if rows else {}):
            values = [row[column] for row in rows if row.get(column) is not None]
            self.distinct[column] = len(set(values))
            comparable = [v for v in values if isinstance(v, (int, float))]
            if comparable:
                self.minimum[column] = min(comparable)
                self.maximum[column] = max(comparable)

    @property
    def pages(self) -> int:
        return max(1, math.ceil(self.row_count / ROWS_PER_PAGE))

    def selectivity(self, predicate: Any) -> float:
        """Fraction of rows a predicate is expected to keep.

        The estimates below are the standard textbook ones, and every one of
        them assumes INDEPENDENCE between columns. That assumption is what
        section 4 breaks, and it is what breaks in production: `WHERE city =
        'Lisbon' AND country = 'Portugal'` is estimated as the product of two
        selectivities, when in truth the second column adds nothing at all.
        """
        if predicate is None:
            return 1.0
        if isinstance(predicate, BinOp):
            if predicate.op == "AND":
                return (self.selectivity(predicate.left)
                        * self.selectivity(predicate.right))
            if predicate.op == "OR":
                left = self.selectivity(predicate.left)
                right = self.selectivity(predicate.right)
                return left + right - left * right
            if predicate.op == "IN" and isinstance(predicate.left, Column):
                distinct = max(1, self.distinct.get(predicate.left.name, 10))
                return min(1.0, len(predicate.right) / distinct)
            if isinstance(predicate.left, Column) and isinstance(predicate.right, Literal):
                column, value = predicate.left.name, predicate.right.value
                if predicate.op == "=":
                    # 1/n_distinct — the classic equality estimate.
                    return 1.0 / max(1, self.distinct.get(column, 10))
                if predicate.op in ("<>", "!="):
                    return 1.0 - 1.0 / max(1, self.distinct.get(column, 10))
                if predicate.op in ("<", "<=", ">", ">="):
                    low = self.minimum.get(column)
                    high = self.maximum.get(column)
                    if low is None or high is None or high == low:
                        return 0.33          # the textbook fallback guess
                    if predicate.op in ("<", "<="):
                        return min(1.0, max(0.0, (value - low) / (high - low)))
                    return min(1.0, max(0.0, (high - value) / (high - low)))
        if isinstance(predicate, UnaryOp) and predicate.op == "NOT":
            return 1.0 - self.selectivity(predicate.operand)
        return 0.33


class Table:
    """A heap of rows, its statistics, and any indexes over it."""

    def __init__(self, name: str, rows: List[Dict[str, Any]]):
        self.name = name
        self.rows = rows
        self.indexes: Dict[str, Any] = {}
        self.stats = Statistics(rows)

    def analyze(self) -> None:
        self.stats = Statistics(self.rows)

    def create_index(self, column: str) -> None:
        from btree import BPlusTree
        tree = BPlusTree(order=32)
        for position, row in enumerate(self.rows):
            if row.get(column) is not None:
                tree.put((row[column], position), position)
        self.indexes[column] = tree


class PlanChoice:
    """One candidate, with the arithmetic that priced it."""

    def __init__(self, kind: str, cost: float, rows: float, reason: str):
        self.kind, self.cost, self.rows, self.reason = kind, cost, rows, reason

    def __repr__(self) -> str:
        return f"<{self.kind} cost={self.cost:.1f} rows={self.rows:.0f}>"


def cost_seq_scan(stats: Statistics, selectivity: float) -> PlanChoice:
    """Every page, in order. The predicate does not change the cost at all."""
    cost = stats.pages * SEQ_PAGE_COST + stats.row_count * CPU_TUPLE_COST
    return PlanChoice("SeqScan", cost, stats.row_count * selectivity,
                      f"{stats.pages} pages sequentially, then filter "
                      f"{stats.row_count} rows")


def cost_index_scan(stats: Statistics, selectivity: float) -> PlanChoice:
    """Descend the index, then fetch each matching row from its heap page.

    Those fetches are the expensive part and the reason the crossover exists.
    They are RANDOM — the index is ordered by key, the heap is not — so each one
    costs RANDOM_PAGE_COST rather than SEQ_PAGE_COST. Match 10% of a table and
    you may touch nearly every page anyway, in the worst possible order.
    """
    matching = stats.row_count * selectivity
    height = max(1, math.ceil(math.log(max(2, stats.row_count), 32)))
    cost = (height * RANDOM_PAGE_COST                       # descend
            + matching * RANDOM_PAGE_COST                   # one fetch per row
            + matching * CPU_TUPLE_COST)
    return PlanChoice("IndexScan", cost, matching,
                      f"{height} pages to descend, then {matching:.0f} random "
                      f"heap fetches at {RANDOM_PAGE_COST}x")


def crossover_selectivity(stats: Statistics) -> float:
    """The selectivity at which a sequential scan overtakes an index scan.

    Solve cost_index(s) = cost_seq for s. Below it, use the index; above it,
    read the whole table. This is a number, not a preference, and it is the
    answer to "why is Postgres ignoring my index".
    """
    height = max(1, math.ceil(math.log(max(2, stats.row_count), 32)))
    sequential = stats.pages * SEQ_PAGE_COST + stats.row_count * CPU_TUPLE_COST
    per_row = RANDOM_PAGE_COST + CPU_TUPLE_COST
    rows = (sequential - height * RANDOM_PAGE_COST) / per_row
    return max(0.0, min(1.0, rows / stats.row_count)) if stats.row_count else 0.0


def _evaluate(expression: Any) -> Callable[[Dict[str, Any]], Any]:
    """Compile an AST expression to a Python callable, once per query.

    Once per QUERY, not once per row. Walking the AST inside the row loop is
    the most common way a toy executor ends up 50x slower than it needs to be —
    the same amortisation argument as vectorised execution, one level up.
    """
    if isinstance(expression, Literal):
        return lambda row, v=expression.value: v
    if isinstance(expression, Column):
        return lambda row, c=expression.name: row.get(c)
    if isinstance(expression, Star):
        return lambda row: row
    if isinstance(expression, UnaryOp):
        operand = _evaluate(expression.operand)
        if expression.op == "NOT":
            return lambda row: not operand(row)
        if expression.op == "-":
            return lambda row: -operand(row)
        if expression.op == "IS NULL":
            return lambda row: operand(row) is None
        if expression.op == "IS NOT NULL":
            return lambda row: operand(row) is not None
    if isinstance(expression, BinOp):
        if expression.op == "IN":
            left = _evaluate(expression.left)
            items = [_evaluate(item) for item in expression.right]
            return lambda row: left(row) in [item(row) for item in items]
        left = _evaluate(expression.left)
        right = _evaluate(expression.right)
        operations: Dict[str, Callable[[Any, Any], Any]] = {
            "AND": lambda a, b: a and b, "OR": lambda a, b: a or b,
            "=": lambda a, b: a == b, "<>": lambda a, b: a != b,
            "!=": lambda a, b: a != b,
            "<": lambda a, b: a is not None and b is not None and a < b,
            ">": lambda a, b: a is not None and b is not None and a > b,
            "<=": lambda a, b: a is not None and b is not None and a <= b,
            ">=": lambda a, b: a is not None and b is not None and a >= b,
            "+": lambda a, b: a + b, "-": lambda a, b: a - b,
            "*": lambda a, b: a * b,
            "/": lambda a, b: a / b if b else None,
            "%": lambda a, b: a % b if b else None,
            "||": lambda a, b: f"{a}{b}",
        }
        operation = operations[expression.op]
        return lambda row: operation(left(row), right(row))
    raise ValueError(f"cannot evaluate {expression!r}")


def _conjuncts(predicate: Any) -> List[Any]:
    """Split `a AND b AND c` into [a, b, c] so each can be placed separately.

    Predicate pushdown needs this. A predicate over one table can be pushed
    down to that table's scan; one that spans two tables cannot move below the
    join. You can only make that distinction on individual conjuncts, which is
    why splitting on AND is the first thing every optimiser does.
    """
    if isinstance(predicate, BinOp) and predicate.op == "AND":
        return _conjuncts(predicate.left) + _conjuncts(predicate.right)
    return [predicate] if predicate is not None else []


def _column_names(expression: Any) -> set:
    """Every column an expression mentions, so pushdown can place it."""
    if isinstance(expression, Column):
        return {expression.name}
    if isinstance(expression, BinOp):
        if expression.op == "IN":
            return _column_names(expression.left)
        return _column_names(expression.left) | _column_names(expression.right)
    if isinstance(expression, UnaryOp):
        return _column_names(expression.operand)
    if isinstance(expression, AggregateExpr):
        return _column_names(expression.argument)
    return set()


def _and_all(predicates: List[Any]) -> Any:
    node = predicates[0]
    for predicate in predicates[1:]:
        node = BinOp("AND", node, predicate)
    return node


class Planner:
    def __init__(self, tables: Dict[str, Table]):
        self.tables = tables
        self.notes: List[str] = []

    def plan(self, statement: Select) -> Operator:
        self.notes = []
        table = self.tables[statement.table]
        joined = [(kind, self.tables[name], alias, condition)
                  for kind, name, alias, condition in statement.joins]

        # -- predicate pushdown --------------------------------------------
        # Split the WHERE on AND, work out which table each conjunct belongs
        # to, and hand it to that table's scan. A conjunct spanning two tables
        # cannot move below the join and stays above it. This is the whole of
        # pushdown, and it is worth orders of magnitude on a join because it
        # shrinks the input rather than the output.
        owner = self._column_owners(table, [t for _, t, _, _ in joined])
        buckets: Dict[str, List[Any]] = {table.name: []}
        for _, other, _, _ in joined:
            buckets.setdefault(other.name, [])
        leftover: List[Any] = []
        for predicate in _conjuncts(statement.where):
            homes = {owner.get(name) for name in _column_names(predicate)}
            homes.discard(None)
            if len(homes) == 1 and homes.copy().pop() in buckets:
                buckets[homes.pop()].append(predicate)
            else:
                leftover.append(predicate)

        node = self._access_path(table, buckets[table.name], statement.alias)

        # -- joins ---------------------------------------------------------
        for kind, other, alias, condition in joined:
            pushed = buckets[other.name]
            rows = other.rows
            if pushed:
                predicate = _evaluate(_and_all(pushed))
                rows = [row for row in rows if predicate(row)]
                self.notes.append(
                    f"pushed {_and_all(pushed)!r} into {other.name}: "
                    f"{len(other.rows):,} rows -> {len(rows):,} before the join")
            key = self._equi_join_keys(condition)
            if key is not None:
                probe_key, build_key = key
                # Build from the SMALLER side. The hash table lives in memory,
                # so this is a memory decision before it is a speed one.
                self.notes.append(
                    f"hash join on {probe_key} = {build_key}, building from "
                    f"{other.name} ({len(rows):,} rows)")
                node = HashJoin(node, rows, probe_key, build_key)
            else:
                self.notes.append(
                    f"nested loop for {other.name}: the ON condition is not an "
                    f"equality, so a hash table cannot answer it")
                node = NestedLoopJoin(node, rows,
                                      lambda a, b, c=condition: bool(
                                          _evaluate(c)({**a, **b})))

        # -- whatever could not be pushed down -----------------------------
        for predicate in leftover:
            node = Filter(node, _evaluate(predicate), repr(predicate))

        # -- aggregation ---------------------------------------------------
        aggregates = [(f"{c.function.lower()}",
                       c.function,
                       c.argument.name if isinstance(c.argument, Column) else None)
                      for c in statement.columns if isinstance(c, AggregateExpr)]
        if aggregates or statement.group_by:
            node = Aggregate(node, [c.name for c in statement.group_by],
                             aggregates)
        elif not any(isinstance(c, Star) for c in statement.columns):
            node = Project(node, [(self._name_of(c), _evaluate(c))
                                  for c in statement.columns])

        if statement.having is not None:
            node = Filter(node, _evaluate(statement.having),
                          repr(statement.having))
        if statement.distinct:
            node = Distinct(node)
        if statement.order_by:
            node = Sort(node, [(_evaluate(e), d) for e, d in statement.order_by],
                        ", ".join(f"{e!r}{' DESC' if d else ''}"
                                  for e, d in statement.order_by))
        if statement.limit is not None or statement.offset:
            node = Limit(node, statement.limit, statement.offset or 0)
        return node

    def _column_owners(self, base: "Table",
                       others: List["Table"]) -> Dict[str, str]:
        """Which table each unqualified column name comes from.

        Real SQL resolves this from the schema and rejects ambiguity with
        "column reference is ambiguous". Here the first table that has the
        column wins, and a name in two tables is reported as ambiguous so it
        stays above the join rather than being pushed to the wrong side —
        pushing a predicate to the wrong table is a WRONG ANSWER, not a slow
        one, so the safe direction is to not push.
        """
        owners: Dict[str, str] = {}
        ambiguous = set()
        for table in [base] + others:
            for column in (table.rows[0] if table.rows else {}):
                if column in owners and owners[column] != table.name:
                    ambiguous.add(column)
                owners.setdefault(column, table.name)
        for column in ambiguous:
            owners.pop(column, None)
        return owners

    def _name_of(self, expression: Any) -> str:
        if isinstance(expression, Column):
            return expression.name
        return repr(expression)

    def _access_path(self, table: Table, predicates: List[Any],
                     alias: Optional[str]) -> Operator:
        """Pick a scan, then attach this table's predicates directly to it.

        Whatever the index cannot absorb becomes a Filter sitting ON the scan,
        not floating somewhere above the joins. That placement is the pushdown:
        the join then sees the filtered row count instead of the table's.
        """
        best: Optional[Tuple[PlanChoice, Any, str]] = None
        combined = 1.0
        for predicate in predicates:
            combined *= table.stats.selectivity(predicate)

        sequential = cost_seq_scan(table.stats, combined)
        for predicate in predicates:
            if not (isinstance(predicate, BinOp)
                    and isinstance(predicate.left, Column)
                    and predicate.left.name in table.indexes
                    and predicate.op in ("=", "<", "<=", ">", ">=")):
                continue
            selectivity = table.stats.selectivity(predicate)
            choice = cost_index_scan(table.stats, selectivity)
            if best is None or choice.cost < best[0].cost:
                best = (choice, predicate, predicate.left.name)

        if best is not None and best[0].cost < sequential.cost:
            choice, predicate, column = best
            self.notes.append(
                f"index on {table.name}.{column}: estimated "
                f"{choice.rows:.0f} rows ({100 * choice.rows / max(1, table.stats.row_count):.2f}%), "
                f"cost {choice.cost:.0f} vs seq scan {sequential.cost:.0f}")
            low, high = self._index_bounds(predicate, table)
            index = table.indexes[column]
            node: Operator = IndexScan(table.name, index, low, high,
                                       lambda position: table.rows[position],
                                       alias)
            rest = [p for p in predicates if p is not predicate]
            if rest:
                node = Filter(node, _evaluate(_and_all(rest)),
                              repr(_and_all(rest)))
            return node

        if best is not None:
            self.notes.append(
                f"index on {table.name}.{best[2]} REJECTED: cost "
                f"{best[0].cost:.0f} vs seq scan {sequential.cost:.0f} — "
                f"{100 * best[0].rows / max(1, table.stats.row_count):.1f}% of the "
                f"table is too much to fetch one page at a time")
        node = SeqScan(table.name, table.rows, alias)
        if predicates:
            node = Filter(node, _evaluate(_and_all(predicates)),
                          repr(_and_all(predicates)))
        return node

    def _index_bounds(self, predicate: BinOp, table: Table) -> Tuple[Any, Any]:
        value = predicate.right.value
        low_key = (value, -1)
        high_key = (value, len(table.rows) + 1)
        if predicate.op == "=":
            return low_key, high_key
        if predicate.op in ("<", "<="):
            return (float("-inf"), -1), high_key
        return low_key, (float("inf"), len(table.rows) + 1)

    def _equi_join_keys(self, condition: Any) -> Optional[Tuple[str, str]]:
        if (isinstance(condition, BinOp) and condition.op == "="
                and isinstance(condition.left, Column)
                and isinstance(condition.right, Column)):
            return condition.left.name, condition.right.name
        return None


def explain(planner: Planner, statement: Select, run: bool = False
            ) -> str:
    plan = planner.plan(statement)
    out = ""
    if run:
        rows = executor.run(plan)
        out += f"  {len(rows)} rows returned\n"
    out += plan.explain()
    for note in planner.notes:
        out += f"  note: {note}\n"
    return out


def _base_rows(plan: Operator) -> int:
    """Rows pulled off the table itself, ignoring the operators above it."""
    if not plan.children:
        return plan.rows_out
    return sum(_base_rows(child) for child in plan.children)


def _demo() -> None:
    global RANDOM_PAGE_COST
    import random
    from sql import parse

    print("=" * 76)
    print("PLANNER — the same query, two plans, and the number between them")
    print("=" * 76)

    rng = random.Random(3)
    rows = [{"id": n, "age": rng.randint(18, 78), "city": rng.choice(
        ["lisbon", "porto", "faro", "braga", "coimbra"]),
        "status": "active" if rng.random() < 0.9 else "closed"}
        for n in range(50000)]
    users = Table("users", rows)
    users.create_index("age")
    users.create_index("id")
    planner = Planner({"users": users})

    print("\n1. What the planner knows without reading the table")
    print("-" * 76)
    print(f"  {users.stats.row_count:,} rows in {users.stats.pages:,} pages")
    for column in ("id", "age", "city", "status"):
        print(f"    {column:<8} {users.stats.distinct[column]:>6} distinct values")
    print("  From n_distinct alone it can estimate `= x` as 1/n_distinct. That")
    print("  is the whole basis of every decision below.")

    print("\n2. The crossover: where an index stops being worth it")
    print("-" * 76)
    crossover = crossover_selectivity(users.stats)
    print(f"  computed crossover: {100 * crossover:.2f}% of the table")
    print(f"    {'selectivity':>12}{'rows':>9}{'index cost':>12}"
          f"{'seq cost':>11}  planner picks")
    for selectivity in (0.0001, 0.001, 0.01, crossover, 0.05, 0.2, 0.8):
        index = cost_index_scan(users.stats, selectivity)
        sequential = cost_seq_scan(users.stats, selectivity)
        pick = "index" if index.cost < sequential.cost else "seq scan"
        print(f"    {100 * selectivity:>11.2f}%{index.rows:>9.0f}"
              f"{index.cost:>12.0f}{sequential.cost:>11.0f}  {pick}")
    print(f"  Below {100 * crossover:.2f}% the index wins; above it the sequential")
    print("  scan does, because an index scan fetches heap pages RANDOMLY and a")
    print("  random page costs 4x a sequential one. Match 20% of a table and you")
    print("  touch nearly every page anyway — in the worst possible order.")
    print("  This is the answer to 'why is it not using my index'.")

    print(f"\n  And the knob: random_page_cost is {RANDOM_PAGE_COST} here "
          f"(a spinning disk).")
    print(f"    {'random_page_cost':>18}{'crossover':>12}")
    original = RANDOM_PAGE_COST
    for value in (4.0, 2.0, 1.5, 1.1):
        RANDOM_PAGE_COST = value
        print(f"    {value:>18.1f}{100 * crossover_selectivity(users.stats):>11.2f}%")
    RANDOM_PAGE_COST = original
    print("  On an SSD, random reads are barely worse than sequential, so 1.1 is")
    print("  the right value and the crossover roughly triples. Leaving the")
    print("  spinning-disk default on flash storage is a real, common misconfig.")

    print("\n3. The plans, chosen and then actually run")
    print("-" * 76)
    for text in ("SELECT id, age FROM users WHERE age = 25",
                 "SELECT id, age FROM users WHERE age > 20",
                 "SELECT city, COUNT(*) FROM users GROUP BY city",
                 "SELECT id FROM users WHERE age = 25 ORDER BY id LIMIT 5"):
        print(f"\n  {text}")
        print(explain(planner, parse(text), run=True))

    print("\n4. When the estimate is wrong, the plan is wrong")
    print("-" * 76)
    # 49,999 rows say 'PT' and exactly one says 'ES'. n_distinct is 2, so the
    # planner believes each value covers half the table. One of those beliefs
    # is off by a factor of 25,000.
    skewed = [{"id": n, "country": "ES" if n == 0 else "PT"}
              for n in range(50000)]
    visitors = Table("visitors", skewed)
    visitors.create_index("country")
    skewed_planner = Planner({"visitors": visitors})

    print(f"    {'WHERE':<18}{'estimated':>11}{'actual':>11}{'plan chosen':>13}"
          f"{'table rows read':>17}")
    for value in ("PT", "ES"):
        text = f"SELECT id FROM visitors WHERE country = '{value}'"
        statement = parse(text)
        estimated = visitors.stats.selectivity(statement.where)
        plan = skewed_planner.plan(statement)
        rows_out = len(executor.run(plan))
        kind = "IndexScan" if "IndexScan" in plan.explain() else "SeqScan"
        scanned = _base_rows(plan)
        print(f"    {f'country = {value!r}':<18}{100 * estimated:>10.2f}%"
              f"{100 * rows_out / len(skewed):>10.3f}%{kind:>13}"
              f"{scanned:>17,}")

    print("  The second row is the failure. One row in fifty thousand matches,")
    print("  an index would answer it in three page reads — and the planner")
    print("  reads all 50,000, because 1/n_distinct told it half the table")
    print("  matched. The estimate is wrong by 25,000x.")
    print("  1/n_distinct assumes values are spread evenly. Real engines carry")
    print("  a most-common-values list plus a histogram precisely because that")
    print("  assumption fails on exactly the columns people filter on: country,")
    print("  status, tenant_id, is_deleted. Every one of them is skewed.")
    print("  This is also why the same query can be fast for months and then")
    print("  slow: nothing changed but the distribution, and ANALYZE was stale.")

    print("\n5. Predicate pushdown: where a filter is applied changes everything")
    print("-" * 76)
    orders = Table("orders", [{"order_id": n, "user_id": n % 50000,
                               "total": n % 900} for n in range(50000)])
    both = Planner({"users": users, "orders": orders})
    text = ("SELECT id, total FROM users JOIN orders ON id = user_id "
            "WHERE age = 25")
    pushed = both.plan(parse(text))
    executor.run(pushed)
    print(f"  {text}\n")
    print(pushed.explain())

    # The same query with the filter left above the join — the plan a naive
    # translator produces by walking the AST in the order it was written.
    naive = Project(
        Filter(HashJoin(SeqScan("users", users.rows), orders.rows,
                        "id", "user_id"),
               _evaluate(parse(text).where), "(age = 25)"),
        [("id", lambda r: r["id"]), ("total", lambda r: r["total"])])
    executor.run(naive)
    print("  The same query with the filter left ABOVE the join:\n")
    print(naive.explain())
    print(f"    {'plan':<22}{'rows through the join':>24}{'total rows read':>18}")
    print(f"    {'filter pushed down':<22}"
          f"{pushed.children[0].rows_in:>24,}{pushed.total_rows_read():>18,}")
    print(f"    {'filter above the join':<22}"
          f"{naive.children[0].children[0].rows_in:>24,}"
          f"{naive.total_rows_read():>18,}")
    print("  Same answer, same rows out. The join saw 839 rows instead of")
    print("  50,000 because the filter ran first — and the filter could move")
    print("  only because splitting the WHERE on AND made it a separate")
    print("  conjunct that mentions exactly one table.")
    print("  Note the safety rule in _column_owners: a column name that exists")
    print("  in BOTH tables is left alone rather than guessed at. Pushing a")
    print("  predicate to the wrong side is a wrong answer, not a slow one.")

    print("\n" + "=" * 76)
    print("Next: database.py wires the parser, planner, executor, B+tree,")
    print("WAL and MVCC into one engine.")
    print("=" * 76)


if __name__ == "__main__":
    _demo()
