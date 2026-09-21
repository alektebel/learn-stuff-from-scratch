"""LSM trees: the other answer, and the triangle you cannot escape.

`btree.py` optimises for reads. Every lookup is O(log n) page touches and every
WRITE is a random page touch, because the key must land in its ordered position
right now.

An LSM tree refuses that. Writes go to a sorted in-memory table and then to an
IMMUTABLE sorted file, sequentially, never updating anything in place. Reads pay
for it: a key might be in the memtable, or in any of several files, and you must
check them in age order until you find it.

    B+tree     read O(log n) pages, write O(log n) RANDOM pages, ~1x space
    LSM        write O(1) sequential, read up to (levels x runs) files, and
               space amplification until compaction catches up

The design decision is not "which is better". It is which of THREE things you
are willing to give up, because you cannot have all of them:

    READ amplification    how many pages a lookup touches
    WRITE amplification   how many times a byte is rewritten by compaction
    SPACE amplification   how much dead data is on disk waiting to be merged

Pick two. That is the RUM conjecture (Athanassoulis et al., EDBT 2016) and the
demo measures all three across leveled and tiered compaction so you can see the
corner you are standing in rather than take it on faith.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

TOMBSTONE = object()          # a delete is a WRITE, which is the whole trick


class BloomFilter:
    """k hashes over m bits. No false negatives, tunable false positives.

    The point in an LSM is not the filter, it is what it saves: without one,
    a lookup for an ABSENT key must open every run at every level. With one,
    it opens almost none. That difference is the reason LSM reads are tolerable
    at all, and the demo measures it by counting file opens.

    TODO
    """


class MemTable:
    """The sorted in-memory buffer. Writes land here and nowhere else.

    TODO
    """


class SSTable:
    """An immutable sorted run on disk, with a sparse index and a bloom filter.

    Immutable is doing all the work: no locking, no in-place update, no torn
    write, and a reader never blocks a writer. Everything hard about an LSM is
    the price of that one property.

    TODO
    """


class LSMTree:
    """memtable -> L0 -> L1 ... with a compaction policy.

    `policy` is "leveled" or "tiered":

      leveled  each level holds ONE sorted run. A merge into level n rewrites
               overlapping data, so write amplification is high and read
               amplification is low.
      tiered   each level holds SEVERAL runs, merged only when the level fills.
               Cheap writes, and a read may check every run in every level.

    RocksDB is leveled, Cassandra is tiered by default, and the difference is
    exactly the trade above. Neither is a bug.

    TODO
    """


def read_amplification(*args, **kwargs) -> float:
    """Mean files opened per successful lookup. TODO"""
    raise NotImplementedError


def write_amplification(*args, **kwargs) -> float:
    """Bytes written to disk / bytes handed to put(). TODO"""
    raise NotImplementedError


def space_amplification(*args, **kwargs) -> float:
    """Bytes on disk / bytes of live data. TODO"""
    raise NotImplementedError


def compare_with_btree(*args, **kwargs) -> Dict[str, Any]:
    """The same workload through both. Sequential-write and random-read shapes.

    Run it twice: a write-heavy workload and a read-heavy one. If one structure
    wins both, the workload is not exercising the difference.

    TODO
    """
    raise NotImplementedError
