"""
tiny_sql_env.py — a zero-dependency text-to-SQL environment.

Everything here uses only the Python standard library (sqlite3, math), so the
RL exercises run on a laptop CPU with no model download and no pip install.

The environment gives you three things every text-to-SQL RL setup needs:

  1. A database with a known schema (so schema-linking rewards are computable).
  2. A set of (natural-language question, gold SQL) tasks.
  3. An *executor* that turns a candidate SQL string into a result set, so you
     can compute an execution-accuracy reward by comparing result sets.

Think of this as the "gym" for the whole curriculum. Later phases wrap it in an
agent loop (Phase 5) or hide the schema (schema discovery as an action).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Iterable


# --------------------------------------------------------------------------- #
# Schema + seed data. A deliberately small "e-commerce" DB with joins, so that
# schema-linking and multi-table grounding actually matter.
# --------------------------------------------------------------------------- #
SCHEMA_SQL = """
CREATE TABLE customers (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    country  TEXT NOT NULL,
    signup   TEXT NOT NULL           -- ISO date
);
CREATE TABLE products (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    category TEXT NOT NULL,
    price    REAL NOT NULL
);
CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    order_date  TEXT NOT NULL
);
"""

SEED = {
    "customers": [
        (1, "Ana",   "ES", "2023-01-04"),
        (2, "Bruno", "BR", "2023-03-19"),
        (3, "Chen",  "CN", "2023-02-11"),
        (4, "Dara",  "ES", "2023-05-02"),
    ],
    "products": [
        (1, "Keyboard", "electronics", 45.0),
        (2, "Desk",     "furniture",   120.0),
        (3, "Mouse",    "electronics", 25.0),
        (4, "Chair",    "furniture",   80.0),
    ],
    "orders": [
        (1, 1, 1, 2, "2023-06-01"),
        (2, 1, 3, 1, "2023-06-03"),
        (3, 2, 2, 1, "2023-06-05"),
        (4, 3, 4, 4, "2023-06-09"),
        (5, 4, 1, 1, "2023-06-11"),
        (6, 4, 4, 2, "2023-06-12"),
    ],
}

# The "gold" schema linking targets, used by schema-linking rewards (Phase 2).
SCHEMA_TABLES = ["customers", "products", "orders"]
SCHEMA_COLUMNS = {
    "customers": ["id", "name", "country", "signup"],
    "products": ["id", "name", "category", "price"],
    "orders": ["id", "customer_id", "product_id", "quantity", "order_date"],
}


@dataclass
class Task:
    """One text-to-SQL problem."""
    qid: str
    question: str
    gold_sql: str
    # Tables/columns a correct query *must* touch — supervision for schema-link
    # rewards. Kept explicit so you never have to parse gold SQL to grade.
    gold_tables: list[str] = field(default_factory=list)
    gold_columns: list[str] = field(default_factory=list)


TASKS: list[Task] = [
    Task("q1",
         "How many customers are from Spain (ES)?",
         "SELECT COUNT(*) FROM customers WHERE country = 'ES';",
         ["customers"], ["country"]),
    Task("q2",
         "What is the average price of electronics products?",
         "SELECT AVG(price) FROM products WHERE category = 'electronics';",
         ["products"], ["price", "category"]),
    Task("q3",
         "List the names of products that have never been ordered.",
         "SELECT name FROM products WHERE id NOT IN (SELECT product_id FROM orders);",
         ["products", "orders"], ["name", "product_id"]),
    Task("q4",
         "Total quantity ordered by customer Ana.",
         "SELECT SUM(o.quantity) FROM orders o "
         "JOIN customers c ON o.customer_id = c.id WHERE c.name = 'Ana';",
         ["orders", "customers"], ["quantity", "customer_id", "name"]),
    Task("q5",
         "Which category has the highest total revenue "
         "(price times quantity)?",
         "SELECT p.category FROM orders o JOIN products p "
         "ON o.product_id = p.id GROUP BY p.category "
         "ORDER BY SUM(p.price * o.quantity) DESC LIMIT 1;",
         ["orders", "products"], ["category", "price", "quantity", "product_id"]),
]


class SQLEnv:
    """An in-memory SQLite database plus a safe-ish executor.

    Not a security boundary — it is a *learning* sandbox. It runs queries in a
    fresh in-memory copy so a bad generated query cannot corrupt anything.
    """

    def __init__(self) -> None:
        self._conn = sqlite3.connect(":memory:")
        self._conn.executescript(SCHEMA_SQL)
        for table, rows in SEED.items():
            placeholders = ",".join("?" * len(rows[0]))
            self._conn.executemany(
                f"INSERT INTO {table} VALUES ({placeholders})", rows
            )
        self._conn.commit()

    # -- execution ---------------------------------------------------------- #
    def execute(self, sql: str) -> tuple[bool, Any]:
        """Run `sql`. Returns (ok, result). On error, result is the message.

        Result rows are normalized to a *sorted list of tuples* so that two
        semantically-equal result sets compare equal regardless of row order.
        """
        try:
            cur = self._conn.execute(sql)
            rows = cur.fetchall()
            return True, _normalize(rows)
        except Exception as exc:  # noqa: BLE001 — any sqlite error is a failure
            return False, str(exc)

    def gold_result(self, task: Task) -> Any:
        ok, res = self.execute(task.gold_sql)
        assert ok, f"gold SQL failed for {task.qid}: {res}"
        return res

    def schema_prompt(self) -> str:
        """A compact schema string you can put in the model prompt."""
        lines = []
        for t in SCHEMA_TABLES:
            cols = ", ".join(SCHEMA_COLUMNS[t])
            lines.append(f"{t}({cols})")
        return "\n".join(lines)


def _normalize(rows: Iterable[tuple]) -> list[tuple]:
    """Sort rows and round floats so comparison is order- and jitter-robust."""
    def _cell(x: Any) -> Any:
        if isinstance(x, float):
            return round(x, 6)
        return x
    return sorted(tuple(_cell(c) for c in row) for row in rows)


if __name__ == "__main__":
    env = SQLEnv()
    print("Schema:\n" + env.schema_prompt() + "\n")
    for task in TASKS:
        gold = env.gold_result(task)
        print(f"[{task.qid}] {task.question}")
        print(f"     gold SQL : {task.gold_sql}")
        print(f"     gold rows: {gold}\n")
