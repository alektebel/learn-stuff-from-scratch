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
        node = self._node(self.root_id)
        path: List[Node] = []
        while not node.leaf:
            path.append(node)
            index = bisect.bisect_right(node.keys, key)
            self.stats["comparisons"] += max(1, len(node.keys).bit_length())
            node = self._node(node.children[index])
        return node, path

    def get(self, key: Any) -> Optional[Any]:
        leaf, _ = self._find_leaf(key)
        index = bisect.bisect_left(leaf.keys, key)
        self.stats["comparisons"] += max(1, len(leaf.keys).bit_length())
        if index < len(leaf.keys) and leaf.keys[index] == key:
            return leaf.values[index]
        return None

    def range(self, low: Any, high: Any) -> Iterator[Tuple[Any, Any]]:
        """Everything in [low, high]. One descent, then a walk along the leaves.

        This is the method the entire B+tree layout exists for. A plain B-tree
        would traverse in-order, revisiting internal nodes and turning a
        sequential read into a random one.
        """
        leaf, _ = self._find_leaf(low)
        while leaf is not None:
            for key, value in zip(leaf.keys, leaf.values):
                if key > high:
                    return
                if key >= low:
                    yield key, value
            leaf = self._node(leaf.next_leaf) if leaf.next_leaf is not None else None

    # -- insert -------------------------------------------------------------

    def put(self, key: Any, value: Any) -> None:
        leaf, path = self._find_leaf(key)
        index = bisect.bisect_left(leaf.keys, key)
        if index < len(leaf.keys) and leaf.keys[index] == key:
            leaf.values[index] = value          # update in place
            return

        leaf.keys.insert(index, key)
        leaf.values.insert(index, value)
        if len(leaf.keys) <= self.order:
            return
        self._split(leaf, path)

    def _split(self, node: Node, path: List[Node]) -> None:
        """Split an overfull node and push a separator up, recursively.

        The leaf case and the internal case differ in ONE respect and it is the
        thing to get right: a LEAF COPIES its middle key upward (the key must
        still be findable in a leaf, because leaves hold all the data), while an
        INTERNAL node MOVES its middle key upward (it is a separator, and
        keeping a copy would mean two nodes claim the same boundary).
        """
        self.stats["splits"] += 1
        middle = len(node.keys) // 2
        sibling = self._new_node(node.leaf)

        if node.leaf:
            separator = node.keys[middle]                     # COPY up
            sibling.keys = node.keys[middle:]
            sibling.values = node.values[middle:]
            node.keys = node.keys[:middle]
            node.values = node.values[:middle]
            sibling.next_leaf = node.next_leaf                # keep the chain
            node.next_leaf = sibling.page_id
        else:
            separator = node.keys[middle]                     # MOVE up
            sibling.keys = node.keys[middle + 1:]
            sibling.children = node.children[middle + 1:]
            node.keys = node.keys[:middle]
            node.children = node.children[:middle + 1]

        if not path:
            # The root split. Everything above grows from here, and this is the
            # only place the tree gets taller — which is why every leaf is
            # always at the same depth without any rebalancing pass.
            root = self._new_node(leaf=False)
            root.keys = [separator]
            root.children = [node.page_id, sibling.page_id]
            self.root_id = root.page_id
            self.height += 1
            self.stats["height_increases"] += 1
            return

        parent = path[-1]
        index = bisect.bisect_right(parent.keys, separator)
        parent.keys.insert(index, separator)
        parent.children.insert(index + 1, sibling.page_id)
        if len(parent.keys) > self.order:
            self._split(parent, path[:-1])

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
        leaf, path = self._find_leaf(key)
        index = bisect.bisect_left(leaf.keys, key)
        if index >= len(leaf.keys) or leaf.keys[index] != key:
            return False

        leaf.keys.pop(index)
        leaf.values.pop(index)
        if path and len(leaf.keys) < (self.order + 1) // 2:
            self._rebalance(leaf, path)
        return True

    def _rebalance(self, node: Node, path: List[Node]) -> None:
        minimum = (self.order + 1) // 2
        parent = path[-1]
        position = parent.children.index(node.page_id)

        left = self._node(parent.children[position - 1]) if position > 0 else None
        right = (self._node(parent.children[position + 1])
                 if position + 1 < len(parent.children) else None)

        # Borrowing is always preferable: it touches two nodes and cannot
        # cascade. Merging touches three and can propagate to the root.
        if left is not None and len(left.keys) > minimum:
            self.stats["borrows"] += 1
            if node.leaf:
                node.keys.insert(0, left.keys.pop())
                node.values.insert(0, left.values.pop())
                parent.keys[position - 1] = node.keys[0]
            else:
                node.keys.insert(0, parent.keys[position - 1])
                parent.keys[position - 1] = left.keys.pop()
                node.children.insert(0, left.children.pop())
            return

        if right is not None and len(right.keys) > minimum:
            self.stats["borrows"] += 1
            if node.leaf:
                node.keys.append(right.keys.pop(0))
                node.values.append(right.values.pop(0))
                parent.keys[position] = right.keys[0]
            else:
                node.keys.append(parent.keys[position])
                parent.keys[position] = right.keys.pop(0)
                node.children.append(right.children.pop(0))
            return

        self.stats["merges"] += 1
        if left is not None:
            self._merge(left, node, parent, position - 1)
        elif right is not None:
            self._merge(node, right, parent, position)
        else:
            return

        if len(parent.keys) < minimum:
            if len(path) > 1:
                self._rebalance(parent, path[:-1])
            elif not parent.keys:
                # The root emptied. Its only child becomes the new root and the
                # tree gets shorter — the exact mirror of the root split.
                self.root_id = parent.children[0]
                self.height -= 1

    def _merge(self, left: Node, right: Node, parent: Node, key_index: int) -> None:
        if left.leaf:
            left.keys += right.keys
            left.values += right.values
            left.next_leaf = right.next_leaf
        else:
            left.keys += [parent.keys[key_index]] + right.keys
            left.children += right.children
        parent.keys.pop(key_index)
        parent.children.pop(key_index + 1)

    # -- inspection ---------------------------------------------------------

    def items(self) -> Iterator[Tuple[Any, Any]]:
        node = self._node(self.root_id)
        while not node.leaf:
            node = self._node(node.children[0])
        while node is not None:
            yield from zip(node.keys, node.values)
            node = self._node(node.next_leaf) if node.next_leaf is not None else None

    def check_invariants(self) -> List[str]:
        """Every property the tree claims. Run it after every experiment.

        A B+tree that is subtly wrong still answers most queries correctly,
        which is exactly what makes it dangerous. These four checks catch the
        failures that a spot-check of `get()` will not.
        """
        problems: List[str] = []
        depths: List[int] = []

        def walk(page_id: int, depth: int, low: Any, high: Any) -> None:
            node = self.nodes[page_id]
            if node.leaf:
                depths.append(depth)
            if node.keys != sorted(node.keys):
                problems.append(f"p{page_id}: keys out of order {node.keys}")
            for key in node.keys:
                if low is not None and key < low:
                    problems.append(f"p{page_id}: key {key} below separator {low}")
                if high is not None and key >= high:
                    problems.append(f"p{page_id}: key {key} at or above {high}")
            if not node.leaf:
                if len(node.children) != len(node.keys) + 1:
                    problems.append(f"p{page_id}: {len(node.keys)} keys but "
                                    f"{len(node.children)} children")
                bounds = [low] + list(node.keys) + [high]
                for i, child in enumerate(node.children):
                    walk(child, depth + 1, bounds[i], bounds[i + 1])

        walk(self.root_id, 1, None, None)
        if len(set(depths)) > 1:
            problems.append(f"leaves at different depths: {sorted(set(depths))} — "
                            f"the tree is not balanced")
        keys = [key for key, _ in self.items()]
        if keys != sorted(keys):
            problems.append("the leaf chain is not in sorted order")
        return problems

    def pretty(self, page_id: Optional[int] = None, depth: int = 0) -> str:
        node = self.nodes[page_id if page_id is not None else self.root_id]
        out = "  " * depth + repr(node) + "\n"
        for child in node.children:
            out += self.pretty(child, depth + 1)
        return out


def _demo() -> None:
    import random

    print("=" * 72)
    print("B+TREE — why the base of the logarithm is the whole design")
    print("=" * 72)

    print("\n1. Growth: the tree gets taller only at the root")
    print("-" * 72)
    tree = BPlusTree(order=4)
    heights = []
    for n in range(1, 41):
        before = tree.height
        tree.put(n, f"row-{n}")
        if tree.height != before:
            heights.append((n, tree.height))
    print(f"  40 keys, order 4 -> height {tree.height}, "
          f"{tree.stats['splits']} splits")
    print(f"  the tree grew a level after inserting keys: "
          f"{[n for n, _ in heights]}")
    print("  Every leaf is at depth", tree.height, "— always, with no")
    print("  rebalancing pass, because growth happens at the root.")
    print("\n" + tree.pretty()[:420] + "  ...")

    problems = tree.check_invariants()
    print(f"  invariants: {problems or 'all hold'}")

    print("\n2. Fanout is the base of the logarithm")
    print("-" * 72)
    print(f"    {'order':>7}{'keys':>10}{'height':>9}{'pages/lookup':>15}"
          f"{'vs scan':>10}")
    for order in (4, 8, 32, 128, 250):
        t = BPlusTree(order=order)
        for n in range(20000):
            t.put(n, n)
        t.stats["pages_read"] = 0
        for n in range(0, 20000, 97):
            t.get(n)
        lookups = len(range(0, 20000, 97))
        per_lookup = t.stats["pages_read"] / lookups
        leaves = sum(1 for node in t.nodes.values() if node.leaf)
        print(f"    {order:>7}{20000:>10}{t.height:>9}{per_lookup:>15.1f}"
              f"{leaves / per_lookup:>9.0f}x")
    print("  The last column is against a full scan, which must read every")
    print("  leaf. At order 250 — roughly what a 4 KB page gives you — a lookup")
    print("  in 20,000 rows costs two page reads, 80x fewer than the scan.")
    print("  Extrapolate: 100M rows at fanout 250 is still four levels, and the")
    print("  top two are always in the buffer pool, so a lookup is two real disk")
    print("  reads. That is the entire reason databases use this and not the")
    print("  balanced binary tree you learned first, which would be 27 levels.")

    print("\n3. Range scans: one descent, then a walk")
    print("-" * 72)
    t = BPlusTree(order=32)
    for n in range(10000):
        t.put(n, n)
    t.stats["pages_read"] = 0
    found = list(t.range(4000, 4200))
    print(f"  range(4000, 4200) returned {len(found)} rows in "
          f"{t.stats['pages_read']} page reads")
    t.stats["pages_read"] = 0
    for n in range(4000, 4201):
        t.get(n)
    print(f"  the same 201 rows as individual lookups: "
          f"{t.stats['pages_read']} page reads")
    print("  The leaf chain is why. Values live only in leaves, so a range is")
    print("  one descent plus sequential steps — and this is most queries.")

    print("\n4. Delete, and the case that shrinks the tree")
    print("-" * 72)
    t = BPlusTree(order=4)
    for n in range(50):
        t.put(n, n)
    print(f"  50 keys: height {t.height}, {t.stats['splits']} splits")
    for n in range(50):
        t.delete(n)
    print(f"  all deleted: height {t.height}, {t.stats['borrows']} borrows, "
          f"{t.stats['merges']} merges")
    print(f"  invariants: {t.check_invariants() or 'all hold'}")
    print("  Borrowing is preferred because it touches two nodes and cannot")
    print("  cascade; a merge touches three and can propagate to the root.")
    print("  Note that production engines mostly SKIP this: an under-full page")
    print("  costs space, but a cascading merge is a latch convoy on a hot")
    print("  table. Correct and shipped differ here, for a concurrency reason.")

    print("\n5. Randomised torture, with the invariants checked each round")
    print("-" * 72)
    rng = random.Random(11)
    t = BPlusTree(order=5)
    reference = {}
    for round_number in range(1, 6):
        for _ in range(400):
            key = rng.randint(0, 300)
            if rng.random() < 0.65:
                t.put(key, key * 10)
                reference[key] = key * 10
            else:
                t.delete(key)
                reference.pop(key, None)
        problems = t.check_invariants()
        matches = dict(t.items()) == reference
        print(f"  round {round_number}: {len(reference):>3} keys, height "
              f"{t.height}, invariants "
              f"{'hold' if not problems else problems[:1]}, "
              f"contents match dict: {matches}")
    print("  Comparing against a plain dict is the cheapest possible oracle and")
    print("  it catches everything: a wrong separator, a dropped leaf link, a")
    print("  merge that lost a key. A B+tree that is subtly wrong still answers")
    print("  most queries correctly, which is what makes it dangerous.")

    print("\n" + "=" * 72)
    print("Next: wal.py makes these writes survive a crash.")
    print("=" * 72)


if __name__ == "__main__":
    _demo()
