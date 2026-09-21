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

Learning Path:
1. Statistics.selectivity — the textbook estimates, all of which assume
   independence between columns
2. cost_seq_scan and cost_index_scan — and note WHY the index scan's row term
   is multiplied by RANDOM_PAGE_COST
3. crossover_selectivity — solve the two costs for equality. This is the answer
   to "why is it not using my index".
4. _evaluate — compile an expression to a callable ONCE PER QUERY, never per row
5. Planner._access_path — pick the cheaper path, and attach this table's
   predicates directly to the scan
6. Predicate pushdown across joins, and the safety rule: never push a predicate
   whose column is ambiguous
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
        raise NotImplementedError

    @property
    def pages(self) -> int:
        raise NotImplementedError

    def selectivity(self, predicate: Any) -> float:
        """Fraction of rows a predicate is expected to keep.

        The estimates below are the standard textbook ones, and every one of
        them assumes INDEPENDENCE between columns. That assumption is what
        section 4 breaks, and it is what breaks in production: `WHERE city =
        'Lisbon' AND country = 'Portugal'` is estimated as the product of two
        selectivities, when in truth the second column adds nothing at all.
        """
        raise NotImplementedError


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
        raise NotImplementedError


class PlanChoice:
    """One candidate, with the arithmetic that priced it."""

    def __init__(self, kind: str, cost: float, rows: float, reason: str):
        self.kind, self.cost, self.rows, self.reason = kind, cost, rows, reason

    def __repr__(self) -> str:
        return f"<{self.kind} cost={self.cost:.1f} rows={self.rows:.0f}>"


def cost_seq_scan(stats: Statistics, selectivity: float) -> PlanChoice:
    """Every page, in order. The predicate does not change the cost at all."""
    raise NotImplementedError


def cost_index_scan(stats: Statistics, selectivity: float) -> PlanChoice:
    """Descend the index, then fetch each matching row from its heap page.

    Those fetches are the expensive part and the reason the crossover exists.
    They are RANDOM — the index is ordered by key, the heap is not — so each one
    costs RANDOM_PAGE_COST rather than SEQ_PAGE_COST. Match 10% of a table and
    you may touch nearly every page anyway, in the worst possible order.
    """
    raise NotImplementedError


def crossover_selectivity(stats: Statistics) -> float:
    """The selectivity at which a sequential scan overtakes an index scan.

    Solve cost_index(s) = cost_seq for s. Below it, use the index; above it,
    read the whole table. This is a number, not a preference, and it is the
    answer to "why is Postgres ignoring my index".
    """
    raise NotImplementedError


def _evaluate(expression: Any) -> Callable[[Dict[str, Any]], Any]:
    """Compile an AST expression to a Python callable, once per query.

    Once per QUERY, not once per row. Walking the AST inside the row loop is
    the most common way a toy executor ends up 50x slower than it needs to be —
    the same amortisation argument as vectorised execution, one level up.
    """
    raise NotImplementedError


def _conjuncts(predicate: Any) -> List[Any]:
    """Split `a AND b AND c` into [a, b, c] so each can be placed separately.

    Predicate pushdown needs this. A predicate over one table can be pushed
    down to that table's scan; one that spans two tables cannot move below the
    join. You can only make that distinction on individual conjuncts, which is
    why splitting on AND is the first thing every optimiser does.
    """
    raise NotImplementedError


def _column_names(expression: Any) -> set:
    """Every column an expression mentions, so pushdown can place it."""
    raise NotImplementedError


def _and_all(predicates: List[Any]) -> Any:
    raise NotImplementedError


class Planner:
    def __init__(self, tables: Dict[str, Table]):
        self.tables = tables
        self.notes: List[str] = []

    def plan(self, statement: Select) -> Operator:
        raise NotImplementedError

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
        raise NotImplementedError

    def _name_of(self, expression: Any) -> str:
        raise NotImplementedError

    def _access_path(self, table: Table, predicates: List[Any],
                     alias: Optional[str]) -> Operator:
        """Pick a scan, then attach this table's predicates directly to it.

        Whatever the index cannot absorb becomes a Filter sitting ON the scan,
        not floating somewhere above the joins. That placement is the pushdown:
        the join then sees the filtered row count instead of the table's.
        """
        raise NotImplementedError

    def _index_bounds(self, predicate: BinOp, table: Table) -> Tuple[Any, Any]:
        raise NotImplementedError

    def _equi_join_keys(self, condition: Any) -> Optional[Tuple[str, str]]:
        raise NotImplementedError


def explain(planner: Planner, statement: Select, run: bool = False
            ) -> str:
    raise NotImplementedError


def _base_rows(plan: Operator) -> int:
    """Rows pulled off the table itself, ignoring the operators above it."""
    raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. What the planner knows without reading the table: row count, pages, and
       n_distinct per column.

    2. The crossover. Index cost against sequential cost across selectivities
       from 0.01% to 80%, with the computed crossover marked. Then sweep
       RANDOM_PAGE_COST from 4.0 (spinning disk) to 1.1 (SSD) and watch the
       crossover roughly triple — that knob is the most misconfigured setting
       in the planner.

    3. Four real queries, planned and then actually run, with the note
       explaining each choice.

    4. When the estimate is wrong. Build a column where 49,999 rows share one
       value and one row has another. n_distinct is 2, so the planner believes
       each value covers half the table; for the RARE value it is wrong by
       25,000x and refuses an index that would answer in three page reads.

    5. Predicate pushdown. The same join with the filter below and above the
       join, comparing rows through the join. Same answer, orders of magnitude
       of difference.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
