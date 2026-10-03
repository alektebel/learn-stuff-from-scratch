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
        self.stats["statements"] += 1
        statement = parse(text)
        return self._run(statement)

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
        if self.current is not None:
            raise DatabaseError("a transaction is already open")
        self.current = self.store.begin(isolation)
        self.wal_txn = self.wal.begin()
        self.inserted = []
        return self.current

    def commit(self) -> None:
        if self.current is None:
            raise DatabaseError("no transaction to commit")
        self.wal.commit(self.wal_txn)          # log first, then make it visible
        self.store.commit(self.current)
        self.inserted = []
        self.current = None

    def rollback(self) -> None:
        if self.current is None:
            return
        self.wal.abort(self.wal_txn)
        self.store.abort(self.current)
        # The heap has to be rolled back too. A real engine does not need this
        # step because the heap IS the version store — the row it appended
        # simply becomes invisible, since its xmin belongs to an aborted
        # transaction. Keeping two structures means keeping them in step.
        for table_name, row in reversed(self.inserted):
            table = self.tables[table_name]
            if row in table.rows:
                table.rows.remove(row)
            table.analyze()
            for column in list(table.indexes):
                table.create_index(column)
        self.inserted = []
        self.current = None

    # -- DDL ----------------------------------------------------------------

    def _create_table(self, statement: CreateTable) -> str:
        if statement.table in self.tables:
            raise DatabaseError(f"table {statement.table!r} already exists")
        self.tables[statement.table] = Table(statement.table, [])
        self.schemas[statement.table] = statement.columns
        self.primary_keys[statement.table] = statement.primary_key
        if statement.primary_key:
            self.tables[statement.table].create_index(statement.primary_key)
        return f"CREATE TABLE {statement.table}"

    def _create_index(self, statement: CreateIndex) -> str:
        table = self._table(statement.table)
        table.create_index(statement.column)
        return f"CREATE INDEX {statement.name} ON {statement.table}"

    def _table(self, name: str) -> Table:
        if name not in self.tables:
            raise DatabaseError(f"no such table: {name}")
        return self.tables[name]

    # -- DML ----------------------------------------------------------------

    def _insert(self, statement: Insert) -> int:
        table = self._table(statement.table)
        columns = statement.columns or [c for c, _ in self.schemas[statement.table]]
        key_column = self.primary_keys.get(statement.table)
        inserted = 0
        for values in statement.rows:
            row = {column: planner_module._evaluate(value)({})
                   for column, value in zip(columns, values)}
            key = row.get(key_column) if key_column else len(table.rows)
            self.store.write(self.current, (statement.table, key), row)
            self.wal.write(self.wal_txn, page_id=hash(statement.table) % 64,
                           key=key, value=row)
            table.rows.append(row)
            self.inserted.append((statement.table, row))
            inserted += 1
        table.analyze()
        for column in list(table.indexes):
            table.create_index(column)         # rebuild; a real engine appends
        return inserted

    def _select(self, statement: Select) -> List[Dict[str, Any]]:
        plan = self._plan(statement)
        rows = executor.run(plan)
        self.stats["rows_read"] += plan.total_rows_read()
        return rows

    def _plan(self, statement: Select) -> Operator:
        # Validate before planning. Letting a missing table surface as a
        # KeyError from deep inside the planner is the difference between
        # "no such table: usres" and a stack trace, and users only ever see one
        # of those as actionable.
        self._table(statement.table)
        for _, name, _, _ in statement.joins:
            self._table(name)
        self.stats["plans"] += 1
        self.planner = Planner(self.tables)
        return self.planner.plan(statement)

    def _update(self, statement: Update) -> int:
        table = self._table(statement.table)
        predicate = (planner_module._evaluate(statement.where)
                     if statement.where else lambda row: True)
        assignments = [(name, planner_module._evaluate(value))
                       for name, value in statement.assignments]
        key_column = self.primary_keys.get(statement.table)
        changed = 0
        for row in table.rows:
            if not predicate(row):
                continue
            for name, value in assignments:
                row[name] = value(row)
            key = row.get(key_column) if key_column else id(row)
            self.store.write(self.current, (statement.table, key), dict(row))
            self.wal.write(self.wal_txn, page_id=hash(statement.table) % 64,
                           key=key, value=dict(row))
            changed += 1
        table.analyze()
        for column in list(table.indexes):
            table.create_index(column)
        return changed

    def _delete(self, statement: Delete) -> int:
        table = self._table(statement.table)
        predicate = (planner_module._evaluate(statement.where)
                     if statement.where else lambda row: True)
        keep = [row for row in table.rows if not predicate(row)]
        removed = len(table.rows) - len(keep)
        table.rows[:] = keep
        table.analyze()
        for column in list(table.indexes):
            table.create_index(column)
        return removed

    # -- introspection ------------------------------------------------------

    def explain(self, statement: Select, run: bool = True) -> str:
        plan = self._plan(statement)
        out = ""
        if run:
            rows = executor.run(plan)
            out += f"  {len(rows)} rows\n"
        out += plan.explain()
        for note in self.planner.notes:
            out += f"  note: {note}\n"
        return out


def _demo() -> None:
    print("=" * 76)
    print("DATABASE — every file in this directory, wired together")
    print("=" * 76)

    print("\n1. SQL, end to end")
    print("-" * 76)
    db = Database()
    db.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT, age INT, "
               "city TEXT)")
    db.execute("INSERT INTO users (id, name, age, city) VALUES "
               "(1, 'alice', 30, 'lisbon'), (2, 'bob', 25, 'porto'), "
               "(3, 'carol', 35, 'lisbon'), (4, 'dave', 28, 'faro')")
    for text in ("SELECT name, age FROM users WHERE age > 26 ORDER BY age DESC",
                 "SELECT city, COUNT(*) FROM users GROUP BY city",
                 "SELECT name FROM users WHERE city = 'lisbon' AND age < 32"):
        print(f"  {text}")
        for row in db.execute(text):
            print(f"      {row}")

    db.execute("UPDATE users SET age = age + 1 WHERE name = 'alice'")
    after = db.execute("SELECT name, age FROM users WHERE name = 'alice'")
    print(f"  UPDATE ... SET age = age + 1 -> {after}")

    print("\n2. Transactions: commit and rollback")
    print("-" * 76)
    db.execute("BEGIN")
    db.execute("INSERT INTO users (id, name, age, city) VALUES "
               "(5, 'erin', 40, 'braga')")
    print(f"  inside the transaction: "
          f"{len(db.execute('SELECT id FROM users'))} rows")
    db.execute("ROLLBACK")
    print(f"  after ROLLBACK: {len(db.execute('SELECT id FROM users'))} rows")
    print("  Note what rollback had to do here: undo the MVCC version AND")
    print("  remove the row from the heap. A real engine needs only the first,")
    print("  because the heap IS the version store — the appended row just")
    print("  becomes invisible, its xmin belonging to an aborted transaction.")
    print("  Two structures holding the same fact is two chances to disagree.")

    print("\n3. The index decision, on real SQL")
    print("-" * 76)
    big = Database()
    big.execute("CREATE TABLE events (id INT PRIMARY KEY, kind TEXT, value INT)")
    import random
    rng = random.Random(5)
    rows = [(n, rng.choice(['click', 'view', 'buy']), rng.randint(0, 9999))
            for n in range(1, 20001)]
    big.tables["events"].rows = [{"id": i, "kind": k, "value": v}
                                 for i, k, v in rows]
    big.tables["events"].analyze()
    big.tables["events"].create_index("value")
    big.tables["events"].create_index("id")

    present = big.tables["events"].rows[7]["value"]
    for text in (f"SELECT id FROM events WHERE value = {present}",
                 "SELECT id FROM events WHERE value > 100"):
        print(f"  {text}")
        print(big.explain(parse(text)))
    print("  Same table, same index, opposite decisions — and the note says")
    print("  which number decided it. Everything else in a query plan is")
    print("  downstream of that one estimate.")

    print("\n4. Crash and recover, with real committed data")
    print("-" * 76)
    wal = WALDatabase()
    t = wal.begin()
    for n in range(1, 6):
        wal.write(t, page_id=1, key=f"user:{n}", value={"id": n})
    wal.commit(t)
    inflight = wal.begin()
    wal.write(inflight, page_id=1, key="user:99", value={"id": 99})
    print(f"  committed 5 rows, one transaction still open, "
          f"{wal.stats['page_writes']} data pages written")
    wal.crash()
    print(f"  CRASH. On disk: {wal.disk}")
    result = wal.recover()
    print(f"  recovery: redid {result['redone']}, undid {result['undone']}, "
          f"losers {result['losers']}")
    print(f"  rows present: {sorted(wal.pages[1])}")
    assert sorted(wal.pages[1]) == [f"user:{n}" for n in range(1, 6)]
    print("  All five committed rows are back and the in-flight one is gone.")

    print("\n5. Two transactions at once")
    print("-" * 76)
    store = MVCCStore()
    setup = store.begin()
    store.write(setup, "stock:widget", 10)
    store.commit(setup)

    a = store.begin()
    b = store.begin()
    print(f"  t{a.xid} reads stock = {store.read(a, 'stock:widget')}")
    print(f"  t{b.xid} reads stock = {store.read(b, 'stock:widget')}")
    store.write(a, "stock:widget", 9)
    store.commit(a)
    print(f"  t{a.xid} sold one and committed; t{b.xid} still reads "
          f"{store.read(b, 'stock:widget')} — its snapshot did not move")
    try:
        store.write(b, "stock:widget", 9)
        print("  t2's write succeeded — an increment was lost")
    except SerializationError as error:
        print(f"  t{b.xid} REFUSED to write: {error}")
    print("  Neither transaction ever waited on a lock. The conflict surfaces")
    print("  at write time as a retryable error, which is the trade MVCC makes.")

    print("\n6. What each file did")
    print("-" * 76)
    layers = [
        ("sql.py", "tokenise and parse", "an AST that says WHAT, never HOW"),
        ("planner.py", "estimate and cost", "index below 0.74% selectivity, "
                                            "scan above"),
        ("executor.py", "pull rows", "LIMIT is free until a Sort blocks it"),
        ("btree.py", "ordered access", "fanout 250 turns 100M rows into 4 levels"),
        ("pager.py", "pages and memory", "a scan evicts the working set"),
        ("wal.py", "survive a crash", "log record durable BEFORE the page"),
        ("mvcc.py", "run concurrently", "readers never block writers"),
    ]
    print(f"    {'file':<14}{'job':<22}the one thing to remember")
    for name, job, lesson in layers:
        print(f"    {name:<14}{job:<22}{lesson}")

    print("\n" + "=" * 76)
    print("Every one of those is a decision with a rejected alternative and a")
    print("limit case that forced it. That is the whole directory.")
    print("=" * 76)


if __name__ == "__main__":
    _demo()
