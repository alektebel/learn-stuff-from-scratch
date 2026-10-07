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
        # TODO: Reject a duplicate primary key (KeyError), write the row, add its index entries: all in the caller's transaction.
        raise NotImplementedError("Table.insert")

    def update(self, t: Txn, pk, changes: dict) -> dict:
        # TODO: Read the old row, merge the changes (the primary key may not change), write the row, remove the OLD index entries, add the NEW ones.
        raise NotImplementedError("Table.update")

    def delete(self, t: Txn, pk) -> None:
        # TODO: Delete the row and its index entries.
        raise NotImplementedError("Table.delete")

    def _index_add(self, t: Txn, row: dict) -> None:
        # TODO: For each indexed column present in the row, write index key -> row JSON.
        raise NotImplementedError("Table._index_add")

    def _index_remove(self, t: Txn, row: dict) -> None:
        # TODO: For each indexed column present in the row, delete its index key.
        raise NotImplementedError("Table._index_remove")

    # -- reads ----------------------------------------------------------------------------
    def get(self, t: Txn, pk):
        self.keys_touched += 1
        raw = t.read(self._row_key(pk))
        return None if raw is None else json.loads(raw)

    def find(self, t: Txn, col: str, value) -> list[dict]:
        """Rows with row[col] == value, sorted by primary key."""
        # TODO: Indexed column: scan the index prefix for that value. Otherwise: scan every row and filter. Add the number of keys read to keys_touched. Sort by primary key.
        raise NotImplementedError("Table.find")


class AsyncIndexTable(Table):
    """Row writes commit alone; index maintenance is queued and applied by propagate()."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue: list[tuple[str, str, object]] = []  # ("put", key, value) / ("del", key, None)

    @property
    def lag(self) -> int:
        return len(self.queue)

    def _index_add(self, t: Txn, row: dict) -> None:
        # TODO: Do NOT write in the transaction: append ('put', index key, row JSON) to self.queue.
        raise NotImplementedError("AsyncIndexTable._index_add")

    def _index_remove(self, t: Txn, row: dict) -> None:
        # TODO: Append ('del', index key, None) to self.queue.
        raise NotImplementedError("AsyncIndexTable._index_remove")

    def propagate(self, n: int | None = None) -> int:
        """Apply up to n queued index changes (all if None), each in its own transaction."""
        # TODO: Pop up to n queued changes (all if None) and apply each in its own READ_COMMITTED transaction. Return how many were applied.
        raise NotImplementedError("AsyncIndexTable.propagate")


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
