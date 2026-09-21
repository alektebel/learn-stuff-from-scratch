"""
Database — the capstone. Complete Solution.

    SQL text
      -> sql.py        tokenise, parse to an AST that says WHAT
        -> planner.py  estimate, cost, choose HOW
          -> executor.py  pull rows through a tree of operators
            -> btree.py     ordered access to the rows
              -> pager.py   pages, and the memory in front of them
    with wal.py making every write survive a crash and mvcc.py letting
    several transactions run at once without blocking each other.

The point is not that `SELECT` works. It is that the FAILURES compose, and each
one is a mechanism you built and can now recognise in a real engine:

  wrong plan        the statistics lied about selectivity
  slow after a while  dead versions nobody vacuumed, because one txn is idle
  lost update       read committed re-reads per statement; use repeatable read
  nobody on call    snapshot isolation admits write skew; use SERIALIZABLE
  corrupt on crash  a page reached disk before its log record did

Learning Path:
1. execute / _run — dispatch on the statement type
2. _create_table, _insert, _select against the planner and executor
3. begin / commit / rollback, threaded through BOTH the WAL and the MVCC store
4. _update and _delete
5. explain — and make it print the planner's notes, because the note is the
   part a user can act on
"""

from typing import Any, Dict, List, Optional, Tuple

import executor
import planner as planner_module
from executor import Operator
from mvcc import MVCCStore, REPEATABLE_READ, SerializationError, Transaction
from planner import Planner, Table
from sql import (CreateIndex, CreateTable, Delete, Explain, Insert, Select,
                 Transactional, Update, parse)
from wal import Database as WALDatabase


class DatabaseError(Exception):
    pass


class Database:
    """A tiny SQL engine over everything in this directory."""

    def __init__(self, isolation: str = REPEATABLE_READ):
        self.tables: Dict[str, Table] = {}
        self.schemas: Dict[str, List[Tuple[str, str]]] = {}
        self.primary_keys: Dict[str, Optional[str]] = {}
        self.store = MVCCStore(isolation)
        self.wal = WALDatabase()
        self.current: Optional[Transaction] = None
        self.inserted: List[Tuple[str, Dict[str, Any]]] = []
        self.autocommit = True
        self.stats = {"statements": 0, "rows_read": 0, "plans": 0}

    # -- statements ---------------------------------------------------------

    def execute(self, text: str) -> Any:
        raise NotImplementedError

    def _run(self, statement: Any) -> Any:
        if isinstance(statement, Transactional):
            return self._transactional(statement)
        if isinstance(statement, Explain):
            return self.explain(statement.statement)
        if isinstance(statement, CreateTable):
            return self._create_table(statement)
        if isinstance(statement, CreateIndex):
            return self._create_index(statement)

        implicit = self.current is None
        if implicit:
            self.begin()
        try:
            if isinstance(statement, Insert):
                result = self._insert(statement)
            elif isinstance(statement, Select):
                result = self._select(statement)
            elif isinstance(statement, Update):
                result = self._update(statement)
            elif isinstance(statement, Delete):
                result = self._delete(statement)
            else:
                raise DatabaseError(f"cannot execute {type(statement).__name__}")
        except Exception:
            if implicit:
                self.rollback()
            raise
        if implicit:
            self.commit()
        return result

    # -- transactions -------------------------------------------------------

    def _transactional(self, statement: Transactional) -> str:
        if statement.kind == "BEGIN":
            self.begin()
        elif statement.kind == "COMMIT":
            self.commit()
        else:
            self.rollback()
        return statement.kind

    def begin(self, isolation: Optional[str] = None) -> Transaction:
        raise NotImplementedError

    def commit(self) -> None:
        raise NotImplementedError

    def rollback(self) -> None:
        raise NotImplementedError

    # -- DDL ----------------------------------------------------------------

    def _create_table(self, statement: CreateTable) -> str:
        raise NotImplementedError

    def _create_index(self, statement: CreateIndex) -> str:
        raise NotImplementedError

    def _table(self, name: str) -> Table:
        if name not in self.tables:
            raise DatabaseError(f"no such table: {name}")
        return self.tables[name]

    # -- DML ----------------------------------------------------------------

    def _insert(self, statement: Insert) -> int:
        raise NotImplementedError

    def _select(self, statement: Select) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def _plan(self, statement: Select) -> Operator:
        """Validate the tables exist, then plan.

        Check BEFORE planning. Letting a missing table surface as a KeyError
        from deep inside the planner is the difference between "no such table:
        usres" and a stack trace, and only one of those is actionable.
        """
        raise NotImplementedError

    def _update(self, statement: Update) -> int:
        raise NotImplementedError

    def _delete(self, statement: Delete) -> int:
        raise NotImplementedError

    # -- introspection ------------------------------------------------------

    def explain(self, statement: Select, run: bool = True) -> str:
        raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these six things:

    1. Real SQL end to end: CREATE TABLE, INSERT, three SELECTs with WHERE,
       ORDER BY and GROUP BY, and an UPDATE.

    2. BEGIN / INSERT / ROLLBACK, and check the row count before and after.
       Note what rollback had to undo here and why a real engine needs less.

    3. The index decision on real SQL: the same table and index, one equality
       query and one range query, with EXPLAIN showing opposite choices and the
       note saying which number decided it.

    4. Crash and recover with committed and in-flight transactions.

    5. Two concurrent transactions where the second is refused rather than
       losing an update.

    6. A table of the seven files, what each did, and the one thing to remember
       from each.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
