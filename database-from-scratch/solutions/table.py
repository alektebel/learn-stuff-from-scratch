"""
Tables, secondary indexes, and the SQL vs NoSQL trade measured
==============================================================

A relational table on a key-value store is a naming convention plus discipline:

    row:    "<table>/row/<pk>"                       -> JSON of the row
    index:  "<table>/idx/<column>/<value>/<pk>"      -> JSON of the row (projection)

The discipline is the hard part. Every write to a row must update every index on it,
and a reader must never see one without the other. Two ways to keep that promise:

  Table              index entries are written in the SAME transaction as the row.
                     A query by index is always consistent with the rows. (SQL databases.)
  AsyncIndexTable    the row is written in its own transaction; index changes are put on
                     a queue and applied later by propagate(). Writes are cheaper and never
                     contend on index keys, but a query by index can return rows that no
                     longer match, or miss rows that now do. (DynamoDB global secondary
                     indexes are eventually consistent for exactly this reason.)

`keys_touched` counts keys read, so "an index avoids a full scan" is a number, not a slogan.

Limits: equality lookups only (index values are compared as strings, so a range over
numbers would need order-preserving encoding); no joins, no query planner.
"""

from __future__ import annotations

import json

from mvcc import Isolation, MVCCStore, Txn


class Table:
    def __init__(self, store: MVCCStore, name: str, primary_key: str, indexes: tuple[str, ...] = ()):
        self.store, self.name, self.pk, self.indexes = store, name, primary_key, tuple(indexes)
        self.keys_touched = 0

    def _row_key(self, pk) -> str:
        return f"{self.name}/row/{pk}"

    def _idx_key(self, col: str, value, pk) -> str:
        return f"{self.name}/idx/{col}/{value}/{pk}"

    def _idx_prefix(self, col: str, value) -> tuple[str, str]:
        p = f"{self.name}/idx/{col}/{value}/"
        return p, p + "￿"

    # -- writes ---------------------------------------------------------------------------
    def insert(self, t: Txn, row: dict) -> None:
        pk = row[self.pk]
        if t.read(self._row_key(pk)) is not None:
            raise KeyError(f"duplicate primary key {pk!r}")
        t.write(self._row_key(pk), json.dumps(row))
        self._index_add(t, row)

    def update(self, t: Txn, pk, changes: dict) -> dict:
        old = self.get(t, pk)
        if old is None:
            raise KeyError(f"no row {pk!r}")
        if self.pk in changes and changes[self.pk] != pk:
            raise ValueError("primary key cannot change")
        new = {**old, **changes}
        t.write(self._row_key(pk), json.dumps(new))
        self._index_remove(t, old)
        self._index_add(t, new)
        return new

    def delete(self, t: Txn, pk) -> None:
        old = self.get(t, pk)
        if old is None:
            raise KeyError(f"no row {pk!r}")
        t.delete(self._row_key(pk))
        self._index_remove(t, old)

    def _index_add(self, t: Txn, row: dict) -> None:
        for col in self.indexes:
            if col in row:
                t.write(self._idx_key(col, row[col], row[self.pk]), json.dumps(row))

    def _index_remove(self, t: Txn, row: dict) -> None:
        for col in self.indexes:
            if col in row:
                t.delete(self._idx_key(col, row[col], row[self.pk]))

    # -- reads ----------------------------------------------------------------------------
    def get(self, t: Txn, pk):
        self.keys_touched += 1
        raw = t.read(self._row_key(pk))
        return None if raw is None else json.loads(raw)

    def find(self, t: Txn, col: str, value) -> list[dict]:
        """Rows with row[col] == value, sorted by primary key."""
        if col in self.indexes:
            hits = t.scan(*self._idx_prefix(col, value))
            self.keys_touched += len(hits)
            rows = [json.loads(v) for v in hits.values()]
        else:
            lo = f"{self.name}/row/"
            hits = t.scan(lo, lo + "￿")
            self.keys_touched += len(hits)
            rows = [r for r in (json.loads(v) for v in hits.values()) if r.get(col) == value]
        return sorted(rows, key=lambda r: r[self.pk])


class AsyncIndexTable(Table):
    """Row writes commit alone; index maintenance is queued and applied by propagate()."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue: list[tuple[str, str, object]] = []  # ("put", key, value) / ("del", key, None)

    @property
    def lag(self) -> int:
        return len(self.queue)

    def _index_add(self, t: Txn, row: dict) -> None:
        for col in self.indexes:
            if col in row:
                self.queue.append(("put", self._idx_key(col, row[col], row[self.pk]), json.dumps(row)))

    def _index_remove(self, t: Txn, row: dict) -> None:
        for col in self.indexes:
            if col in row:
                self.queue.append(("del", self._idx_key(col, row[col], row[self.pk]), None))

    def propagate(self, n: int | None = None) -> int:
        """Apply up to n queued index changes (all if None), each in its own transaction."""
        applied = 0
        while self.queue and (n is None or applied < n):
            op, key, value = self.queue.pop(0)
            t = self.store.begin(Isolation.READ_COMMITTED)
            t.delete(key) if op == "del" else t.write(key, value)
            t.commit()
            applied += 1
        return applied


if __name__ == "__main__":
    for cls in (Table, AsyncIndexTable):
        s = MVCCStore()
        users = cls(s, "users", "id", indexes=("city",))
        t = s.begin()
        for i in range(1000):
            users.insert(t, {"id": i, "name": f"u{i}", "city": ["Madrid", "Lyon", "Oslo"][i % 3]})
        t.commit()
        if isinstance(users, AsyncIndexTable):
            users.propagate()
        t = s.begin()
        users.update(t, 7, {"city": "Lisbon"})
        t.commit()
        r = s.begin()
        users.keys_touched = 0
        lisbon = users.find(r, "city", "Lisbon")
        by_index = users.keys_touched
        users.keys_touched = 0
        users.find(r, "name", "u7")
        by_scan = users.keys_touched
        print(f"{cls.__name__:16s} find(city=Lisbon) -> {[u['id'] for u in lisbon]}  "
              f"keys touched: index {by_index}, full scan {by_scan}")
