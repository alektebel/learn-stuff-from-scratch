"""
B+Tree — the index. Complete Solution.

A table without an index answers "where is key K" by reading every page. A
B+tree answers it in log_b(N) page reads, and for realistic fanouts that is
three or four reads for hundreds of millions of rows. The whole design exists
to make that logarithm's BASE large, because the base is what turns a
disk-bound problem into a memory-bound one.

DESIGN DECISION — binary tree, or a tree with hundreds of children?
  A balanced binary tree over 100M keys is 27 levels deep. At one page read per
  level that is 27 disk reads for one lookup. The tree is asymptotically
  perfect and practically useless, because the cost model it was designed
  against (comparisons) is not the cost model of a disk (page reads).
  CHOSEN: a B+tree, with as many keys per node as fit in one page. At 4 KB
  pages and ~16-byte entries the fanout is ~250, so 100M keys is 4 levels —
  and the top two are almost always in the buffer pool. This is the single most
  important number in the file: it is why databases use B-trees and not the
  tree you learned first.

DESIGN DECISION — values in every node (B-tree), or only in the leaves (B+tree)?
  A plain B-tree stores values beside keys at every level, so a lookup can
  finish early at an internal node. That sounds like a win.
  CHOSEN: B+tree — values ONLY in leaves, internal nodes hold nothing but
  separator keys. Two consequences, both decisive:
    * Internal nodes get much higher fanout, because they store no payload.
      Fanout is the base of the logarithm, so this makes the tree shallower.
    * The leaves form a linked list, so a RANGE scan is one descent plus a walk
      along the leaves. In a plain B-tree a range scan is an in-order traversal
      that bounces up and down the tree, which is random I/O.
  `WHERE created_at BETWEEN ... AND ...` is the query that pays for this
  decision, and it is most queries.

DESIGN DECISION — how does the tree stay balanced?
  CHOSEN: grow at the ROOT, not at the leaves. A full node splits and pushes
  its middle key up; if that reaches a full root, the root splits and a NEW
  root is created above it. Every leaf therefore stays at exactly the same
  depth, always, without any rebalancing pass. That is the trick — the tree is
  balanced by construction rather than by maintenance.

MVP FIRST, THEN THE LIMIT CASES — the order to build this in:
  1. Insert into a single leaf. Works until the leaf is full.
  2. Split a leaf. Works until the parent is full.
  3. Split an internal node. Works until the ROOT is full.
  4. Split the root and grow a level. Now insert is complete.
  5. Delete, which is where the symmetry breaks: a node that falls below half
     full must borrow from a sibling or merge with one, and merging can cascade
     upward and shrink the tree. Most real systems cheat here — see below.

Learning Path — build it in this order, and do not skip ahead:
1. _find_leaf and get — descend, recording the path
2. put, for a leaf that does not overflow
3. _split for a LEAF (copy the middle key up) — then for an INTERNAL node
   (move it up). That difference is the thing to get right.
4. The root split, which is the only place the tree gets taller
5. range — one descent, then walk the leaf chain
6. delete, then _rebalance: borrow from a sibling, else merge, and let a merge
   cascade upward
7. check_invariants, and run it after every experiment
"""

import bisect
from typing import Any, Iterator, List, Optional, Tuple

from pager import PAGE_INTERNAL, PAGE_LEAF, BufferPool, DiskManager, Page


class Node:
    """An in-memory B+tree node. The pager holds bytes; this holds meaning.

    DESIGN DECISION — serialise nodes to pages, or keep them as objects?
      Real engines pack nodes into page bytes directly, so a node IS a page and
      nothing is copied.
      CHOSEN here: objects, with page_id as identity and an explicit page-read
      counter. The serialisation is mechanical and would triple the length of
      this file while teaching nothing the pager did not already teach. What it
      would cost you is visibility into the number that matters — pages touched
      per operation — so that is counted explicitly instead.
    """

    __slots__ = ("page_id", "leaf", "keys", "values", "children", "next_leaf")

    def __init__(self, page_id: int, leaf: bool = True):
        self.page_id = page_id
        self.leaf = leaf
        self.keys: List[Any] = []
        self.values: List[Any] = []        # leaves only
        self.children: List[int] = []      # internal only
        self.next_leaf: Optional[int] = None

    def __repr__(self) -> str:
        kind = "leaf" if self.leaf else "internal"
        return f"<{kind} p{self.page_id} keys={self.keys}>"


class BPlusTree:
    """An ordered index over a pager, with every page access counted."""

    def __init__(self, pool: Optional[BufferPool] = None, order: int = 4):
        """`order` is the maximum number of keys in a node.

        Four is deliberately tiny. A real fanout of 250 means you would have to
        insert thousands of rows before seeing a single split, and every bug in
        this file lives in a split. Build it at order 4 where the tree is small
        enough to print, then raise it and watch the height collapse.
        """
        self.pool = pool or BufferPool(DiskManager(), capacity=64)
        self.order = order
        self.nodes: dict = {}
        self.root_id = self._new_node(leaf=True).page_id
        self.height = 1
        self.stats = {"pages_read": 0, "splits": 0, "merges": 0,
                      "borrows": 0, "height_increases": 0, "comparisons": 0}

    # -- node access --------------------------------------------------------

    def _new_node(self, leaf: bool) -> Node:
        page = self.pool.new_page(PAGE_LEAF if leaf else PAGE_INTERNAL)
        node = Node(page.page_id, leaf)
        self.nodes[page.page_id] = node
        return node

    def _node(self, page_id: int) -> Node:
        """Every read goes through here, so the counter cannot be dodged."""
        self.stats["pages_read"] += 1
        self.pool.fetch(page_id)
        return self.nodes[page_id]

    # -- search -------------------------------------------------------------

    def _find_leaf(self, key: Any) -> Tuple[Node, List[Node]]:
        """Descend to the leaf that would hold `key`, recording the path.

        The path is what makes splits possible without parent pointers. A parent
        pointer would have to be updated on every split of every node, and it
        would be a second copy of a fact the descent already knows.
        """
        raise NotImplementedError

    def get(self, key: Any) -> Optional[Any]:
        raise NotImplementedError

    def range(self, low: Any, high: Any) -> Iterator[Tuple[Any, Any]]:
        """Everything in [low, high]. One descent, then a walk along the leaves.

        This is the method the entire B+tree layout exists for. A plain B-tree
        would traverse in-order, revisiting internal nodes and turning a
        sequential read into a random one.
        """
        raise NotImplementedError

    # -- insert -------------------------------------------------------------

    def put(self, key: Any, value: Any) -> None:
        raise NotImplementedError

    def _split(self, node: Node, path: List[Node]) -> None:
        """Split an overfull node and push a separator up, recursively.

        The leaf case and the internal case differ in ONE respect and it is the
        thing to get right: a LEAF COPIES its middle key upward (the key must
        still be findable in a leaf, because leaves hold all the data), while an
        INTERNAL node MOVES its middle key upward (it is a separator, and
        keeping a copy would mean two nodes claim the same boundary).
        """
        raise NotImplementedError

    # -- delete -------------------------------------------------------------

    def delete(self, key: Any) -> bool:
        """Remove a key. Returns False if it was not there.

        DESIGN DECISION — rebalance on delete, or let nodes run empty?
          Textbook B+trees restore the half-full invariant: borrow from a
          sibling, else merge, and let the merge cascade upward.
          CHOSEN: implement it properly, because the borrow-versus-merge choice
          is the interesting part. But know that SQLite, InnoDB and PostgreSQL
          all largely DO NOT: they leave under-full pages alone and reclaim them
          in a background vacuum. The reason is concurrency — a merge locks
          three nodes and can cascade to the root, which is a latch convoy on a
          hot table, while an under-full page costs only space. "Correct" and
          "what production does" genuinely differ here, and the reason is
          contention rather than laziness.
        """
        raise NotImplementedError

    def _rebalance(self, node: Node, path: List[Node]) -> None:
        raise NotImplementedError

    def _merge(self, left: Node, right: Node, parent: Node, key_index: int) -> None:
        raise NotImplementedError

    # -- inspection ---------------------------------------------------------

    def items(self) -> Iterator[Tuple[Any, Any]]:
        raise NotImplementedError

    def check_invariants(self) -> List[str]:
        """Every property the tree claims. Run it after every experiment.

        A B+tree that is subtly wrong still answers most queries correctly,
        which is exactly what makes it dangerous. These four checks catch the
        failures that a spot-check of `get()` will not.
        """
        raise NotImplementedError

    def pretty(self, page_id: Optional[int] = None, depth: int = 0) -> str:
        raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. Growth. Insert 40 keys at order 4 and record which insertions made the
       tree taller. Print the tree. Every leaf is at the same depth, always,
       with no rebalancing pass.

    2. Fanout is the base of the logarithm. Build the same 20,000 keys at
       orders 4, 8, 32, 128 and 250, and measure PAGES READ per lookup against
       the number of leaves a scan would read. At order 250 the answer is two
       pages. Extrapolating to 100M rows is the whole argument for B-trees.

    3. Range scans. `range(4000, 4200)` against 201 individual `get` calls, in
       page reads. The gap is what the leaf chain buys.

    4. Delete. Insert 50 keys and delete all of them; count borrows against
       merges and watch the height come back down.

    5. Randomised torture. Thousands of random puts and deletes, comparing
       against a plain dict after every round and running check_invariants.
       The dict is the cheapest possible oracle and it catches everything a
       spot-check of get() will not: a wrong separator, a dropped leaf link, a
       merge that lost a key.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
