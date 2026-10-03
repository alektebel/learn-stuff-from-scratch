"""
DynamoDB — the service, not the paper. Complete Solution.

The `dynamo-paper/` directory implements the 2007 paper: consistent hashing,
vector clocks, sloppy quorums. This is the *product* built on those ideas, and
what it exposes to you is different: a partition key that decides everything,
capacity you pay for and can exhaust, and a query/scan distinction that is the
single biggest cost lever in the service.

DESIGN DECISION — how to model partitions?
  A flat dict keyed by (partition_key, sort_key) is simplest and hides the one
  thing you most need to feel: that the PARTITION KEY decides which physical
  shard serves you, and a key everyone uses is a queue everyone stands in.
  CHOSEN: an explicit dict of partitions, each with its own capacity counter.
  Hot-partition throttling then falls out of the model rather than being
  bolted on — see the limit case.

DESIGN DECISION — eventually or strongly consistent reads?
  CHOSEN: model both. A strongly consistent read costs twice as much and
  cannot be served by a replica. Making the price visible is the point: most
  reads do not need it, and defaulting to strong is a common way to double a
  bill for nothing.
"""

import hashlib
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


class DynamoError(Exception):
    pass


class ThroughputExceeded(DynamoError):
    """ProvisionedThroughputExceededException — the one you must retry."""


class ConditionalCheckFailed(DynamoError):
    """The condition on a write was not met. Not retryable: it means someone
    else got there first, which is exactly what you asked to be told."""


Item = Dict[str, Any]


class Partition:
    """One physical shard. Capacity is enforced HERE, not fleet-wide."""

    def __init__(self, key: str, read_capacity: float, write_capacity: float):
        self.key = key
        self.read_capacity = read_capacity
        self.write_capacity = write_capacity
        # Keyed by the FULL composite key. A partition holds many partition
        # keys; keying by sort key alone would make alice/000 and bob/000
        # collide, which is a silent data-loss bug rather than an error.
        self.items: Dict[Tuple[Any, Any], Item] = {}
        self.read_used = 0.0
        self.write_used = 0.0
        self.window_start = 0.0
        self.throttled = 0

    def consume(self, units: float, kind: str, now: float) -> None:
        if now - self.window_start >= 1.0:    # one-second refill window
            self.window_start = now
            self.read_used = self.write_used = 0.0

        if kind == "read":
            if self.read_used + units > self.read_capacity:
                self.throttled += 1
                raise ThroughputExceeded(
                    f"partition {self.key!r}: {self.read_used + units:.1f} read "
                    f"units requested, {self.read_capacity:.1f} available")
            self.read_used += units
        else:
            if self.write_used + units > self.write_capacity:
                self.throttled += 1
                raise ThroughputExceeded(
                    f"partition {self.key!r}: {self.write_used + units:.1f} write "
                    f"units requested, {self.write_capacity:.1f} available")
            self.write_used += units


class Table:
    def __init__(self, name: str, partition_key: str,
                 sort_key: Optional[str] = None,
                 read_capacity: float = 10.0, write_capacity: float = 10.0,
                 num_partitions: int = 4):
        self.name = name
        self.partition_key = partition_key
        self.sort_key = sort_key
        self.num_partitions = num_partitions
        # Capacity is divided ACROSS partitions. This is the whole reason a hot
        # key throttles while the table looks idle.
        self.per_partition_read = read_capacity / num_partitions
        self.per_partition_write = write_capacity / num_partitions
        self.partitions: Dict[str, Partition] = {}
        self.indexes: Dict[str, "GlobalSecondaryIndex"] = {}
        self.stream: List[Dict[str, Any]] = []
        self.stats = {"reads": 0, "writes": 0, "scanned_items": 0,
                      "returned_items": 0, "throttles": 0}

    def _partition(self, key_value: Any) -> Partition:
        # md5, not hash(). Python randomises string hashing per process, so
        # hash() would put a key in a different partition on every run and make
        # every capacity demo below irreproducible.
        digest = hashlib.md5(str(key_value).encode()).hexdigest()
        slot = f"p{int(digest, 16) % self.num_partitions}"
        if slot not in self.partitions:
            self.partitions[slot] = Partition(slot, self.per_partition_read,
                                              self.per_partition_write)
        return self.partitions[slot]

    def _keys(self, item: Item) -> Tuple[Any, Any]:
        if self.partition_key not in item:
            raise DynamoError(f"item is missing the partition key "
                              f"{self.partition_key!r}")
        sort_value = item.get(self.sort_key) if self.sort_key else None
        if self.sort_key and sort_value is None:
            raise DynamoError(f"item is missing the sort key {self.sort_key!r}")
        return item[self.partition_key], sort_value

    # -- writes -------------------------------------------------------------

    def put_item(self, item: Item, condition: Optional[Callable[[Optional[Item]], bool]] = None,
                 now: Optional[float] = None) -> None:
        """Write an item, optionally only if a condition on the CURRENT item holds.

        Conditional writes are how you get correctness without locks: the check
        and the write happen atomically inside one partition. `attribute_not_exists`
        is the idiom for "create only if absent", and it is the difference
        between an idempotent create and a silent overwrite.
        """
        now = time.time() if now is None else now
        partition_value, sort_value = self._keys(item)
        partition = self._partition(partition_value)

        existing = partition.items.get((partition_value, sort_value))
        if condition is not None and not condition(existing):
            raise ConditionalCheckFailed(
                f"condition failed for {partition_value}/{sort_value}")

        try:
            partition.consume(1.0, "write", now)
        except ThroughputExceeded:
            self.stats["throttles"] += 1
            raise

        partition.items[(partition_value, sort_value)] = dict(item)
        self.stats["writes"] += 1
        self.stream.append({"event": "INSERT" if existing is None else "MODIFY",
                            "keys": (partition_value, sort_value),
                            "old": existing, "new": dict(item), "at": now})
        for index in self.indexes.values():
            index.reindex(self)

    def delete_item(self, partition_value: Any, sort_value: Any = None,
                    now: Optional[float] = None) -> Optional[Item]:
        now = time.time() if now is None else now
        partition = self._partition(partition_value)
        partition.consume(1.0, "write", now)
        removed = partition.items.pop((partition_value, sort_value), None)
        if removed is not None:
            self.stream.append({"event": "REMOVE",
                                "keys": (partition_value, sort_value),
                                "old": removed, "new": None, "at": now})
        return removed

    # -- reads --------------------------------------------------------------

    def get_item(self, partition_value: Any, sort_value: Any = None,
                 consistent: bool = False,
                 now: Optional[float] = None) -> Optional[Item]:
        """A strongly consistent read costs twice as much."""
        now = time.time() if now is None else now
        partition = self._partition(partition_value)
        try:
            partition.consume(1.0 if consistent else 0.5, "read", now)
        except ThroughputExceeded:
            self.stats["throttles"] += 1
            raise
        self.stats["reads"] += 1
        # scanned_items means "items touched", which is the BILLABLE quantity.
        # A GetItem touches exactly one, so it belongs in the same counter as
        # the items a Query or a Scan walks past — otherwise a cost model has
        # to guess which calls were which.
        self.stats["scanned_items"] += 1
        item = partition.items.get((partition_value, sort_value))
        if item is not None:
            self.stats["returned_items"] += 1
        return dict(item) if item else None

    def query(self, partition_value: Any,
              sort_condition: Optional[Callable[[Any], bool]] = None,
              consistent: bool = False, limit: Optional[int] = None,
              now: Optional[float] = None) -> List[Item]:
        """Read ONE partition, optionally filtering on the sort key.

        This is the operation the whole data model exists to make cheap. You
        must supply the partition key; that is not a limitation, it is the
        contract that lets the cost be O(items returned) rather than O(table).
        """
        now = time.time() if now is None else now
        partition = self._partition(partition_value)
        matching = [item for (pk, sk), item in sorted(
            partition.items.items(),
            key=lambda kv: (kv[0][1] is not None, str(kv[0][1])))
            if pk == partition_value
            and (sort_condition is None or sort_condition(sk))]

        if limit:
            matching = matching[:limit]
        units = max(0.5, len(matching) * (1.0 if consistent else 0.5))
        try:
            partition.consume(units, "read", now)
        except ThroughputExceeded:
            self.stats["throttles"] += 1
            raise

        self.stats["reads"] += 1
        self.stats["scanned_items"] += len(matching)
        self.stats["returned_items"] += len(matching)
        return [dict(item) for item in matching]

    def scan(self, filter_fn: Optional[Callable[[Item], bool]] = None,
             now: Optional[float] = None) -> List[Item]:
        """Read EVERY item, then filter. You pay for what you read, not what
        you keep.

        The filter runs after the read, so a scan that returns three items out
        of a million still costs a million reads. This is the single biggest
        cost mistake in the service, and the demo below prices it.
        """
        now = time.time() if now is None else now
        results: List[Item] = []
        scanned = 0
        for partition in self.partitions.values():
            for item in partition.items.values():
                scanned += 1
                partition.consume(0.5, "read", now)
                if filter_fn is None or filter_fn(item):
                    results.append(dict(item))
        self.stats["reads"] += 1
        self.stats["scanned_items"] += scanned
        self.stats["returned_items"] += len(results)
        return results

    # -- indexes ------------------------------------------------------------

    def add_gsi(self, name: str, partition_key: str,
                sort_key: Optional[str] = None) -> "GlobalSecondaryIndex":
        index = GlobalSecondaryIndex(name, partition_key, sort_key)
        self.indexes[name] = index
        index.reindex(self)
        return index

    def hot_partition_report(self) -> Dict[str, Dict[str, Any]]:
        return {key: {"items": len(p.items), "throttled": p.throttled}
                for key, p in sorted(self.partitions.items())}


class GlobalSecondaryIndex:
    """A GSI is a separate table maintained for you — asynchronously.

    That word is the whole point: a GSI is EVENTUALLY consistent, always. You
    cannot request a strongly consistent read from one, because the index write
    happens after the base write commits. Writing an item and immediately
    querying a GSI for it is a race you will sometimes lose.
    """

    def __init__(self, name: str, partition_key: str,
                 sort_key: Optional[str] = None):
        self.name = name
        self.partition_key = partition_key
        self.sort_key = sort_key
        self.entries: Dict[Any, List[Item]] = {}

    def reindex(self, table: Table) -> None:
        self.entries = {}
        for partition in table.partitions.values():
            for item in partition.items.values():
                if self.partition_key in item:
                    self.entries.setdefault(item[self.partition_key], []).append(
                        dict(item))

    def query(self, value: Any) -> List[Item]:
        return [dict(item) for item in self.entries.get(value, [])]


def _demo() -> None:
    print("=== The partition key decides everything ===")
    table = Table("orders", partition_key="customer_id", sort_key="order_id",
                  read_capacity=40, write_capacity=40, num_partitions=4)
    for customer in ("alice", "erin", "frank", "heidi"):
        for n in range(3):
            table.put_item({"customer_id": customer, "order_id": f"{n:03d}",
                            "total": (n + 1) * 10,
                            "status": "shipped" if n else "pending"}, now=0)
    print(f"  items per partition: "
          f"{ {k: v['items'] for k, v in table.hot_partition_report().items()} }")

    print("\n=== Query vs Scan: the same answer, very different bills ===")
    before = dict(table.stats)
    found = table.query("alice", now=1)
    query_scanned = table.stats["scanned_items"] - before["scanned_items"]

    before = dict(table.stats)
    scanned_result = table.scan(lambda i: i["customer_id"] == "alice", now=2)
    scan_scanned = table.stats["scanned_items"] - before["scanned_items"]

    print(f"  query('alice'): {len(found)} items, read {query_scanned}")
    print(f"  scan(filter):   {len(scanned_result)} items, read {scan_scanned}")
    print("  Identical results. The filter runs AFTER the read, so a scan")
    print("  returning 3 of a million items still costs a million reads.")

    print("\n=== Strong consistency costs double ===")
    priced = Table("t", partition_key="pk", read_capacity=100, num_partitions=1)
    priced.put_item({"pk": "x", "v": 1}, now=0)
    p = priced.partitions["p0"]
    p.read_used = 0.0
    priced.get_item("x", consistent=False, now=0)
    eventual = p.read_used
    p.read_used = 0.0
    priced.get_item("x", consistent=True, now=0)
    print(f"  eventually consistent: {eventual} read units")
    print(f"  strongly consistent:   {p.read_used} read units")
    print("  Most reads do not need strong. Defaulting to it doubles the bill.")

    print("\n=== The limit case: a hot partition ===")
    hot = Table("events", partition_key="day", sort_key="seq",
                read_capacity=40, write_capacity=40, num_partitions=4)
    print(f"  table capacity: 40 WCU, spread over 4 partitions = "
          f"{hot.per_partition_write:.0f} per partition")
    written = 0
    try:
        for n in range(30):
            hot.put_item({"day": "2024-01-01", "seq": f"{n:04d}"}, now=0)
            written += 1
    except ThroughputExceeded as exc:
        print(f"  wrote {written} items, then: {exc}")
    print(f"  partitions: {hot.hot_partition_report()}")
    print("\n  The TABLE has 40 WCU and used 10. It still throttled, because")
    print("  every item shared one partition key. Adding capacity would not")
    print("  help — the fix is to spread the key (add a suffix, shard the day).")
    print("  This is the single most common DynamoDB surprise.")

    print("\n=== Conditional writes replace locks ===")
    accounts = Table("accounts", partition_key="user", read_capacity=100,
                     write_capacity=100, num_partitions=1)
    accounts.put_item({"user": "dave", "balance": 100},
                      condition=lambda existing: existing is None, now=0)
    print("  created dave (condition: must not exist)")
    try:
        accounts.put_item({"user": "dave", "balance": 999},
                          condition=lambda existing: existing is None, now=0)
    except ConditionalCheckFailed as exc:
        print(f"  second create: {exc}")
    print("  The check and the write are atomic within the partition. This is")
    print("  how you get idempotent creates and optimistic locking with no")
    print("  lock service at all.")

    print("\n=== A GSI is a separate, eventually consistent table ===")
    index = table.add_gsi("by-status", partition_key="status")
    print(f"  query GSI status=pending: "
          f"{len(index.query('pending'))} items")
    table.put_item({"customer_id": "dave", "order_id": "000",
                    "total": 5, "status": "pending"}, now=3)
    print(f"  after a write, before propagation, a real GSI may still show the")
    print(f"  old count. You cannot ask a GSI for a strongly consistent read —")
    print(f"  the index write happens after the base write commits.")

    print("\n=== Streams: the change log ===")
    for event in table.stream[-3:]:
        print(f"  {event['event']:<7}{event['keys']}")
    print("  This is what triggers Lambda, and what makes a table a source of")
    print("  events rather than just a store.")


if __name__ == "__main__":
    _demo()
