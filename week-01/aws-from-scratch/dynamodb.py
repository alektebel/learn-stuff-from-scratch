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
        raise NotImplementedError


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
        raise NotImplementedError

    def _keys(self, item: Item) -> Tuple[Any, Any]:
        raise NotImplementedError
    # -- writes -------------------------------------------------------------

    def put_item(self, item: Item, condition: Optional[Callable[[Optional[Item]], bool]] = None,
                 now: Optional[float] = None) -> None:
        """Write an item, optionally only if a condition on the CURRENT item holds.

        Conditional writes are how you get correctness without locks: the check
        and the write happen atomically inside one partition. `attribute_not_exists`
        is the idiom for "create only if absent", and it is the difference
        between an idempotent create and a silent overwrite.

        TODO: refill the bucket if a second has passed, then check the
        request against THIS PARTITION's capacity and raise ThroughputExceeded
        if it does not fit.

        Capacity lives on the partition, not the table. That is the entire
        reason a hot key throttles while the table sits idle.

        TODO: hash the partition key value to one of num_partitions slots,
        creating the Partition lazily.

        Use hashlib, NOT Python's hash(). String hashing is randomised per
        process, so hash() would place a key in a different partition on every
        run and make every capacity result irreproducible.
        """
        raise NotImplementedError

    def delete_item(self, partition_value: Any, sort_value: Any = None,
                    now: Optional[float] = None) -> Optional[Item]:
        raise NotImplementedError
    # -- reads --------------------------------------------------------------

    def get_item(self, partition_value: Any, sort_value: Any = None,
                 consistent: bool = False,
                 now: Optional[float] = None) -> Optional[Item]:
        """A strongly consistent read costs twice as much.

        Count this call in BOTH stats["reads"] and stats["scanned_items"].
        scanned_items means "items touched", which is the billable quantity —
        a GetItem touches exactly one, so it belongs in the same counter as the
        items a Query or a Scan walks past. Keep them in separate counters and
        every cost model built on these stats has to guess which calls were
        which.
        """
        raise NotImplementedError

    def query(self, partition_value: Any,
              sort_condition: Optional[Callable[[Any], bool]] = None,
              consistent: bool = False, limit: Optional[int] = None,
              now: Optional[float] = None) -> List[Item]:
        """Read ONE partition, optionally filtering on the sort key.

        This is the operation the whole data model exists to make cheap. You
        must supply the partition key; that is not a limitation, it is the
        contract that lets the cost be O(items returned) rather than O(table).
        """
        raise NotImplementedError

    def scan(self, filter_fn: Optional[Callable[[Item], bool]] = None,
             now: Optional[float] = None) -> List[Item]:
        """Read EVERY item, then filter. You pay for what you read, not what
        you keep.

        The filter runs after the read, so a scan that returns three items out
        of a million still costs a million reads. This is the single biggest
        cost mistake in the service, and the demo below prices it.
        """
        raise NotImplementedError
    # -- indexes ------------------------------------------------------------

    def add_gsi(self, name: str, partition_key: str,
                sort_key: Optional[str] = None) -> "GlobalSecondaryIndex":
        raise NotImplementedError

    def hot_partition_report(self) -> Dict[str, Dict[str, Any]]:
        raise NotImplementedError


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
        raise NotImplementedError

    def query(self, value: Any) -> List[Item]:
        raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS the behaviour.

    The solution's demo is the reference — but write yours first and predict
    the numbers before running it. A result that surprises you is a gap in your
    model that passing tests did not reveal.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
